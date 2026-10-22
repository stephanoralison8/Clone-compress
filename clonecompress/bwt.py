"""Transformée de Burrows-Wheeler, Move-To-Front et codage de plages de zéros."""


def transformee_bwt(donnees):
    """BWT par tri des rotations (doublement de préfixes).

    Renvoie (dernière colonne, indice de la rotation d'origine)."""
    n = len(donnees)
    if n == 0:
        return b"", 0
    rang = list(donnees)
    sa = list(range(n))
    k = 1
    mult = max(n, 256) + 1
    while k < n:
        decale = rang[k:] + rang[:k]
        cles = [a * mult + b for a, b in zip(rang, decale)]
        sa.sort(key=cles.__getitem__)
        nouveau = [0] * n
        r = 0
        prec = cles[sa[0]]
        for i in sa:
            c = cles[i]
            if c != prec:
                r += 1
                prec = c
            nouveau[i] = r
        rang = nouveau
        if r == n - 1:
            break
        k <<= 1
    derniere = bytes(donnees[i - 1] for i in sa)  # donnees[-1] si i == 0
    return derniere, sa.index(0)


def inverse_bwt(derniere, indice):
    n = len(derniere)
    if n == 0:
        return b""
    debut = [0] * 256
    for c in derniere:
        debut[c] += 1
    somme = 0
    for c in range(256):
        debut[c], somme = somme, somme + debut[c]
    suivant = [0] * n
    for i, c in enumerate(derniere):
        suivant[debut[c]] = i
        debut[c] += 1
    sortie = bytearray(n)
    p = indice
    for k in range(n):
        p = suivant[p]
        sortie[k] = derniere[p]
    return bytes(sortie)


def mtf_encoder(donnees):
    alphabet = list(range(256))
    sortie = []
    for c in donnees:
        i = alphabet.index(c)
        sortie.append(i)
        if i:
            del alphabet[i]
            alphabet.insert(0, c)
    return sortie


def mtf_decoder(indices):
    alphabet = list(range(256))
    sortie = bytearray()
    for i in indices:
        c = alphabet[i]
        sortie.append(c)
        if i:
            del alphabet[i]
            alphabet.insert(0, c)
    return bytes(sortie)


RUNA, RUNB = 0, 1


def rle_zeros_encoder(indices):
    """Remplace les séquences de 0 par des symboles RUNA/RUNB (base 2 bijective).
    Les valeurs v >= 1 deviennent le symbole v + 1."""
    sortie = []
    z = 0
    for v in indices:
        if v == 0:
            z += 1
            continue
        while z > 0:
            if z & 1:
                sortie.append(RUNA)
                z = (z - 1) >> 1
            else:
                sortie.append(RUNB)
                z = (z - 2) >> 1
        sortie.append(v + 1)
    while z > 0:
        if z & 1:
            sortie.append(RUNA)
            z = (z - 1) >> 1
        else:
            sortie.append(RUNB)
            z = (z - 2) >> 1
    return sortie


def rle_zeros_decoder(symboles):
    sortie = []
    run = 0
    poids = 1
    for s in symboles:
        if s == RUNA:
            run += poids
            poids <<= 1
        elif s == RUNB:
            run += 2 * poids
            poids <<= 1
        else:
            if run:
                sortie.extend([0] * run)
                run = 0
                poids = 1
            sortie.append(s - 1)
    if run:
        sortie.extend([0] * run)
    return sortie


def rle1_encoder(donnees):
    """Pré-codage de bzip2 : 4 octets identiques suivis d'un compteur (0..255)."""
    sortie = bytearray()
    n = len(donnees)
    i = 0
    while i < n:
        c = donnees[i]
        j = i
        while j < n and donnees[j] == c and j - i < 259:
            j += 1
        longueur = j - i
        if longueur >= 4:
            sortie.extend([c, c, c, c, longueur - 4])
        else:
            sortie.extend([c] * longueur)
        i = j
    return bytes(sortie)


def rle1_decoder(donnees):
    sortie = bytearray()
    n = len(donnees)
    i = 0
    identiques = 0
    prec = -1
    while i < n:
        c = donnees[i]
        i += 1
        sortie.append(c)
        if c == prec:
            identiques += 1
        else:
            identiques = 1
            prec = c
        if identiques == 4:
            if i < n:
                sortie.extend([c] * donnees[i])
                i += 1
            identiques = 0
            prec = -1
    return bytes(sortie)
