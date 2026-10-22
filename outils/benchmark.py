#!/usr/bin/env python3
"""Lance les trois clones sur chaque fichier de ./echantillons, vérifie l'aller-retour,
compare avec les bibliothèques de référence (bz2, lzma) et écrit :
    resultats/resultats.json          (chiffres)
    resultats/transcript_<type>.txt   (sessions de terminal, utilisées par le rapport PDF)
"""
import bz2
import hashlib
import json
import lzma
import os
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RACINE, "echantillons")
RES = os.path.join(RACINE, "resultats")
OUTIL = os.path.join(RACINE, "clonecompress.py")
os.makedirs(RES, exist_ok=True)

TYPES = {".txt": "texte", ".md": "texte", ".csv": "texte", ".wav": "audio", ".mp3": "audio",
         ".flac": "audio", ".bmp": "image", ".png": "image", ".jpg": "image", ".jpeg": "image",
         ".ppm": "image", ".y4m": "vidéo", ".mp4": "vidéo", ".avi": "vidéo", ".mkv": "vidéo"}


def sha(chemin):
    with open(chemin, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def lancer(transcript, args):
    """Exécute le CLI, ajoute '$ commande' + sortie au transcript, renvoie la durée."""
    affiche = "python clonecompress.py " + " ".join(os.path.relpath(a, RACINE) if os.path.isabs(a) else a
                                                    for a in args)
    t0 = time.time()
    p = subprocess.run([sys.executable, OUTIL] + args, capture_output=True, text=True, cwd=RACINE)
    duree = time.time() - t0
    transcript.append("$ " + affiche)
    sortie = (p.stdout + p.stderr).rstrip()
    if sortie:
        transcript.append(sortie)
    if p.returncode != 0:
        raise SystemExit(f"échec : {affiche}\n{sortie}")
    return duree


def main():
    fichiers = sorted(f for f in os.listdir(ECH) if os.path.splitext(f)[1].lower() in TYPES)
    if not fichiers:
        raise SystemExit("Aucun fichier reconnu dans " + ECH)
    resultats = []
    for nom in fichiers:
        src = os.path.join(ECH, nom)
        base, ext = os.path.splitext(nom)
        genre = TYPES[ext.lower()]
        taille = os.path.getsize(src)
        print(f"== {nom} ({genre}, {taille} octets)", flush=True)
        tr = []
        rel_src = os.path.relpath(src, RACINE)
        sorties = {k: os.path.join("resultats", f"{base}{ext}.{k}") for k in ("bzc", "lzc", "7zc")}
        d_bz = lancer(tr, ["bzip2", "-k", "-f", "-v", "-n", "3", "-o", sorties["bzc"], rel_src])
        d_lz = lancer(tr, ["lzma", "-k", "-f", "-v", "-n", "6", "-o", sorties["lzc"], rel_src])
        if os.path.exists(os.path.join(RACINE, sorties["7zc"])):
            os.remove(os.path.join(RACINE, sorties["7zc"]))
        d_7z = lancer(tr, ["7z", "a", sorties["7zc"], rel_src, "-n", "5"])
        lancer(tr, ["7z", "l", sorties["7zc"]])
        # décompression + vérification
        ok = {}
        d_bz_d = lancer(tr, ["bzip2", "-d", "-k", "-f", "-v", "-o", "resultats/_bz.out", sorties["bzc"]])
        ok["bzip2"] = sha("resultats/_bz.out" if False else os.path.join(RACINE, "resultats/_bz.out")) == sha(src)
        d_lz_d = lancer(tr, ["lzma", "-d", "-k", "-f", "-v", "-o", "resultats/_lz.out", sorties["lzc"]])
        ok["lzma"] = sha(os.path.join(RACINE, "resultats/_lz.out")) == sha(src)
        os.makedirs(os.path.join(RACINE, "resultats", "_7z"), exist_ok=True)
        lancer(tr, ["7z", "x", sorties["7zc"], "-o", "resultats/_7z"])
        ok["7z"] = sha(os.path.join(RACINE, "resultats", "_7z", nom)) == sha(src)
        tr.append(f"# Vérification SHA-256 de l'aller-retour : "
                  f"bzip2={'OK' if ok['bzip2'] else 'ECHEC'}  lzma={'OK' if ok['lzma'] else 'ECHEC'}  "
                  f"7z={'OK' if ok['7z'] else 'ECHEC'}")
        with open(src, "rb") as f:
            brut = f.read()
        ref_bz = len(bz2.compress(brut, 9))
        ref_lz = len(lzma.compress(brut, preset=6))
        tailles = {k: os.path.getsize(os.path.join(RACINE, v)) for k, v in sorties.items()}
        resultats.append({
            "fichier": nom, "type": genre, "taille": taille,
            "bzip2_clone": tailles["bzc"], "lzma_clone": tailles["lzc"], "7z_clone": tailles["7zc"],
            "bzip2_ref": ref_bz, "lzma_ref": ref_lz,
            "duree_bzip2": d_bz, "duree_lzma": d_lz, "duree_7z": d_7z,
            "aller_retour_ok": all(ok.values()),
        })
        with open(os.path.join(RES, f"transcript_{genre}_{base}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(tr) + "\n")
        for nom_tmp in ("_bz.out", "_lz.out"):
            os.remove(os.path.join(RACINE, "resultats", nom_tmp))
    with open(os.path.join(RES, "resultats.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)
    print(f"\n{'Fichier':<14}{'Original':>10}{'bzip2-c':>10}{'lzma-c':>10}{'7z-c':>10}{'bz2 réf':>10}{'xz réf':>10}  OK")
    for r in resultats:
        print(f"{r['fichier']:<14}{r['taille']:>10}{r['bzip2_clone']:>10}{r['lzma_clone']:>10}"
              f"{r['7z_clone']:>10}{r['bzip2_ref']:>10}{r['lzma_ref']:>10}  {'oui' if r['aller_retour_ok'] else 'NON'}")


if __name__ == "__main__":
    main()
