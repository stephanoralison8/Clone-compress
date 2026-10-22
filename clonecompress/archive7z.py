"""Clone de 7-zip : archiveur "solide" (tous les fichiers dans un seul flux LZMA).

Commandes : a (ajouter/créer), x (extraire), l (lister), t (tester).
Le conteneur est simplifié (format propre .7zc, non compatible avec 7-Zip officiel).

Format :
    "7ZC1" | décalage_entête u64 | flux_solide (LZMA-clone) | entête (LZMA-clone, JSON)
L'entête décrit chaque entrée : nom, type, taille, date de modification, CRC32.
"""

import json
import os
import struct
import zlib

from . import lzma_clone

MAGIE = b"7ZC1"
PREFIXE = struct.Struct("<4sQ")


def _collecter(chemins):
    """Parcourt fichiers et dossiers ; renvoie [(chemin_disque, nom_archive, est_dossier)]."""
    entrees = []
    vus = set()
    for chemin in chemins:
        chemin = os.path.normpath(chemin)
        if not os.path.exists(chemin):
            raise FileNotFoundError(chemin)
        base = os.path.basename(chemin)
        if os.path.isdir(chemin):
            if base not in vus:
                entrees.append((chemin, base, True))
                vus.add(base)
            for racine, dossiers, fichiers in os.walk(chemin):
                dossiers.sort()
                for nom in dossiers:
                    complet = os.path.join(racine, nom)
                    rel = os.path.join(base, os.path.relpath(complet, chemin))
                    entrees.append((complet, rel.replace(os.sep, "/"), True))
                for nom in sorted(fichiers):
                    complet = os.path.join(racine, nom)
                    rel = os.path.join(base, os.path.relpath(complet, chemin))
                    entrees.append((complet, rel.replace(os.sep, "/"), False))
        else:
            entrees.append((chemin, base, False))
    return entrees


def creer(archive, chemins, taille_dictionnaire=1 << 20, profondeur=48, rappel=None):
    entrees = _collecter(chemins)
    meta = []
    flux = bytearray()
    for chemin, nom, est_dossier in entrees:
        st = os.stat(chemin)
        if est_dossier:
            meta.append({"nom": nom, "dossier": True, "taille": 0, "date": int(st.st_mtime), "crc32": 0})
        else:
            with open(chemin, "rb") as f:
                contenu = f.read()
            flux += contenu
            meta.append({"nom": nom, "dossier": False, "taille": len(contenu),
                         "date": int(st.st_mtime), "crc32": zlib.crc32(contenu)})
    solide = lzma_clone.compresser(bytes(flux), taille_dictionnaire, profondeur, rappel)
    entete = lzma_clone.compresser(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
    with open(archive, "wb") as f:
        f.write(PREFIXE.pack(MAGIE, PREFIXE.size + len(solide)))
        f.write(solide)
        f.write(entete)
    return meta, len(flux), PREFIXE.size + len(solide) + len(entete)


def _lire(archive):
    with open(archive, "rb") as f:
        brut = f.read()
    if len(brut) < PREFIXE.size:
        raise ValueError("archive trop courte")
    magie, decalage = PREFIXE.unpack_from(brut, 0)
    if magie != MAGIE:
        raise ValueError("ce n'est pas une archive 7z-clone (.7zc)")
    meta = json.loads(lzma_clone.decompresser(brut[decalage:]).decode("utf-8"))
    return meta, brut[PREFIXE.size:decalage]


def lister(archive):
    meta, _ = _lire(archive)
    return meta


def _nom_sur(nom):
    """Refuse les chemins absolus / les '..' (attaque par traversée de répertoire)."""
    parties = nom.split("/")
    if nom.startswith("/") or ":" in parties[0] or any(p in ("..", "") for p in parties):
        raise ValueError(f"nom d'entrée dangereux refusé : {nom!r}")
    return os.path.join(*parties)


def extraire(archive, destination=".", tester_seulement=False):
    meta, solide = _lire(archive)
    flux = lzma_clone.decompresser(solide)
    pos = 0
    resultats = []
    for e in meta:
        chemin = os.path.join(destination, _nom_sur(e["nom"]))
        if e["dossier"]:
            if not tester_seulement:
                os.makedirs(chemin, exist_ok=True)
            resultats.append((e["nom"], True))
            continue
        contenu = flux[pos:pos + e["taille"]]
        pos += e["taille"]
        ok = len(contenu) == e["taille"] and zlib.crc32(contenu) == e["crc32"]
        resultats.append((e["nom"], ok))
        if not ok:
            raise ValueError(f"CRC32 incorrect pour {e['nom']}")
        if not tester_seulement:
            os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
            with open(chemin, "wb") as f:
                f.write(contenu)
            os.utime(chemin, (e["date"], e["date"]))
    return resultats
