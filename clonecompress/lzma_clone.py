"""Clone de LZMA : LZ77 (chaînes de hachage) + codage par intervalles adaptatif.

Principes repris de LZMA : bits "est_une_correspondance", littéraux contextuels
(octet précédent), correspondances répétées (rep0), longueurs et distances codées
par arbres binaires / emplacements ("slots") + bits directs.
Le conteneur est simplifié (format propre).

Format (.lzc) :
    "LZC1" | taille_originale u64 | crc32 u32 | taille_dictionnaire u32 | flux
"""

import struct
import zlib

from .codeur_intervalles import (CodeurIntervalles, DecodeurIntervalles, PROB_INIT)

MAGIE = b"LZC1"
ENTETE = struct.Struct("<4sQII")
LONGUEUR_MIN = 2
LONGUEUR_MAX = 273
BITS_POS = 2                  # pb = 2
MASQUE_POS = (1 << BITS_POS) - 1
BITS_CTX_LITTERAL = 3         # lc = 3
NB_ETATS = 3                  # 0 = littéral, 1 = correspondance, 2 = répétition


def _probs(n):
    return [PROB_INIT] * n


class _Modeles:
    """Ensemble des probabilités adaptatives (identique côté codeur et décodeur)."""

    def __init__(self):
        self.est_corresp = [_probs(1 << BITS_POS) for _ in range(NB_ETATS)]
        self.est_rep = _probs(NB_ETATS)
        self.litteral = [_probs(0x100) for _ in range(1 << BITS_CTX_LITTERAL)]
        # longueurs : choix, choix2, bas (3 bits), milieu (3 bits), haut (8 bits)
        self.long_choix = _probs(2)
        self.long_bas = [_probs(8) for _ in range(1 << BITS_POS)]
        self.long_milieu = [_probs(8) for _ in range(1 << BITS_POS)]
        self.long_haut = _probs(256)
        self.rep_choix = _probs(2)
        self.rep_bas = [_probs(8) for _ in range(1 << BITS_POS)]
        self.rep_milieu = [_probs(8) for _ in range(1 << BITS_POS)]
        self.rep_haut = _probs(256)
        # distances
        self.slot = [_probs(64) for _ in range(4)]
        self.spec = {s: _probs(1 << ((s >> 1) - 1)) for s in range(4, 14)}
        self.align = _probs(16)


def _slot_distance(d):
    if d < 4:
        return d
    n = d.bit_length()
    return ((n - 1) << 1) | ((d >> (n - 2)) & 1)


# ------------------------------------------------------------------ codage

def _coder_longueur(rc, choix, bas, milieu, haut, l, pos_etat):
    l -= LONGUEUR_MIN
    if l < 8:
        rc.bit(choix, 0, 0)
        rc.arbre(bas[pos_etat], 3, l)
    elif l < 16:
        rc.bit(choix, 0, 1)
        rc.bit(choix, 1, 0)
        rc.arbre(milieu[pos_etat], 3, l - 8)
    else:
        rc.bit(choix, 0, 1)
        rc.bit(choix, 1, 1)
        rc.arbre(haut, 8, l - 16)


def _coder_distance(rc, m, d, l):
    etat_long = min(l - LONGUEUR_MIN, 3)
    slot = _slot_distance(d)
    rc.arbre(m.slot[etat_long], 6, slot)
    if slot >= 4:
        nb_directs = (slot >> 1) - 1
        base = (2 | (slot & 1)) << nb_directs
        reste = d - base
        if slot < 14:
            rc.arbre_inverse(m.spec[slot], nb_directs, reste)
        else:
            rc.bits_directs(reste >> 4, nb_directs - 4)
            rc.arbre_inverse(m.align, 4, reste & 15)


class _ChercheurCorrespondances:
    """Chaînes de hachage sur 3 octets."""

    def __init__(self, donnees, fenetre, profondeur):
        self.d = donnees
        self.fenetre = fenetre
        self.profondeur = profondeur
        self.tete = {}
        self.prec = [-1] * len(donnees)
        self.n = len(donnees)

    def inserer(self, i):
        if i + 2 < self.n:
            d = self.d
            h = (d[i] << 16) | (d[i + 1] << 8) | d[i + 2]
            self.prec[i] = self.tete.get(h, -1)
            self.tete[h] = i

    def meilleure(self, i):
        n = self.n
        if i + 2 >= n:
            return 0, 0
        d = self.d
        h = (d[i] << 16) | (d[i + 1] << 8) | d[i + 2]
        j = self.tete.get(h, -1)
        maxl = min(LONGUEUR_MAX, n - i)
        meilleure_l = 0
        meilleure_d = 0
        essais = self.profondeur
        limite = i - self.fenetre
        while j >= 0 and j >= limite and essais > 0:
            if d[j + meilleure_l] == d[i + meilleure_l]:
                l = 0
                while l < maxl and d[j + l] == d[i + l]:
                    l += 1
                if l > meilleure_l:
                    meilleure_l = l
                    meilleure_d = i - j
                    if l >= maxl:
                        break
            j = self.prec[j]
            essais -= 1
        return meilleure_l, meilleure_d


def compresser(donnees, taille_dictionnaire=1 << 20, profondeur=48, rappel=None):
    n = len(donnees)
    rc = CodeurIntervalles()
    m = _Modeles()
    cherch = _ChercheurCorrespondances(donnees, taille_dictionnaire, profondeur)
    pos = 0
    etat = 0
    rep0 = 1
    prec_octet = 0
    prochain_rappel = 0
    while pos < n:
        pos_etat = pos & MASQUE_POS
        # --- recherche
        l, d = cherch.meilleure(pos)
        # répétition de la dernière distance
        lrep = 0
        if rep0 <= pos:
            maxl = min(LONGUEUR_MAX, n - pos)
            while lrep < maxl and donnees[pos + lrep] == donnees[pos + lrep - rep0]:
                lrep += 1
        if lrep >= LONGUEUR_MIN and lrep + 1 >= l:
            # --- répétition
            rc.bit(m.est_corresp[etat], pos_etat, 1)
            rc.bit(m.est_rep, etat, 1)
            _coder_longueur(rc, m.rep_choix, m.rep_bas, m.rep_milieu, m.rep_haut, lrep, pos_etat)
            avance = lrep
            etat = 2
        elif l >= 3 and not (l == 3 and d > 4096):
            # --- correspondance
            rc.bit(m.est_corresp[etat], pos_etat, 1)
            rc.bit(m.est_rep, etat, 0)
            _coder_longueur(rc, m.long_choix, m.long_bas, m.long_milieu, m.long_haut, l, pos_etat)
            _coder_distance(rc, m, d - 1, l)
            rep0 = d
            avance = l
            etat = 1
        else:
            # --- littéral
            rc.bit(m.est_corresp[etat], pos_etat, 0)
            rc.arbre(m.litteral[prec_octet >> (8 - BITS_CTX_LITTERAL)], 8, donnees[pos])
            avance = 1
            etat = 0
        for k in range(avance):
            cherch.inserer(pos + k)
        pos += avance
        prec_octet = donnees[pos - 1]
        if rappel and pos >= prochain_rappel:
            rappel(pos, n)
            prochain_rappel = pos + max(1, n // 50)
    flux = rc.terminer()
    return ENTETE.pack(MAGIE, n, zlib.crc32(donnees), taille_dictionnaire) + flux


# --------------------------------------------------------------- décodage

def _decoder_longueur(rd, choix, bas, milieu, haut, pos_etat):
    if rd.bit(choix, 0) == 0:
        return rd.arbre(bas[pos_etat], 3) + LONGUEUR_MIN
    if rd.bit(choix, 1) == 0:
        return rd.arbre(milieu[pos_etat], 3) + 8 + LONGUEUR_MIN
    return rd.arbre(haut, 8) + 16 + LONGUEUR_MIN


def _decoder_distance(rd, m, l):
    etat_long = min(l - LONGUEUR_MIN, 3)
    slot = rd.arbre(m.slot[etat_long], 6)
    if slot < 4:
        return slot
    nb_directs = (slot >> 1) - 1
    base = (2 | (slot & 1)) << nb_directs
    if slot < 14:
        reste = rd.arbre_inverse(m.spec[slot], nb_directs)
    else:
        reste = rd.bits_directs(nb_directs - 4) << 4
        reste |= rd.arbre_inverse(m.align, 4)
    return base + reste


def decompresser(compresse):
    if len(compresse) < ENTETE.size:
        raise ValueError("fichier trop court")
    magie, n, crc, _ = ENTETE.unpack_from(compresse, 0)
    if magie != MAGIE:
        raise ValueError("ce n'est pas un fichier lzma-clone (.lzc)")
    rd = DecodeurIntervalles(compresse, ENTETE.size) if n else None
    m = _Modeles()
    sortie = bytearray()
    etat = 0
    rep0 = 1
    while len(sortie) < n:
        pos = len(sortie)
        pos_etat = pos & MASQUE_POS
        if rd.bit(m.est_corresp[etat], pos_etat) == 0:
            prec = sortie[-1] if sortie else 0
            sortie.append(rd.arbre(m.litteral[prec >> (8 - BITS_CTX_LITTERAL)], 8))
            etat = 0
            continue
        if rd.bit(m.est_rep, etat) == 1:
            l = _decoder_longueur(rd, m.rep_choix, m.rep_bas, m.rep_milieu, m.rep_haut, pos_etat)
            etat = 2
        else:
            l = _decoder_longueur(rd, m.long_choix, m.long_bas, m.long_milieu, m.long_haut, pos_etat)
            rep0 = _decoder_distance(rd, m, l) + 1
            etat = 1
        if rep0 > pos or pos + l > n:
            raise ValueError("flux corrompu (distance ou longueur invalide)")
        debut = pos - rep0
        if rep0 >= l:
            sortie += sortie[debut:debut + l]
        else:                                  # chevauchement : copie octet par octet
            for k in range(l):
                sortie.append(sortie[debut + k])
    if zlib.crc32(sortie) != crc:
        raise ValueError("données corrompues (CRC32 incorrect)")
    return bytes(sortie)
