"""Interface en ligne de commande : python -m clonecompress {bzip2|lzma|7z} ..."""

import argparse
import os
import sys
import time

from . import bzip2_clone, lzma_clone, archive7z

EXT = {"bzip2": ".bzc", "lzma": ".lzc"}


def _barre(prefixe):
    if not sys.stderr.isatty():
        return None

    def rappel(i, total):
        pct = 100 * i // total
        sys.stderr.write(f"\r{prefixe} {pct:3d} %")
        sys.stderr.flush()
        if i >= total:
            sys.stderr.write("\r" + " " * (len(prefixe) + 8) + "\r")
    return rappel


def _taille(n):
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or u == "Go":
            return f"{n:.0f} {u}" if u == "o" else f"{n:.2f} {u}"
        n /= 1024


def _outil_simple(nom, args):
    module = bzip2_clone if nom == "bzip2" else lzma_clone
    ext = EXT[nom]
    for entree in args.fichiers:
        t0 = time.time()
        with open(entree, "rb") as f:
            donnees = f.read()
        if args.decompresser or args.tester:
            if not args.tester and not entree.endswith(ext) and not args.sortie:
                print(f"{nom}: {entree}: extension inconnue (attendu {ext})", file=sys.stderr)
                return 1
            res = module.decompresser(donnees)
            if args.tester:
                print(f"{entree}: OK ({_taille(len(res))} une fois décompressé)")
                continue
            sortie = args.sortie or entree[: -len(ext)]
        else:
            if nom == "bzip2":
                res = module.compresser(donnees, taille_bloc=args.niveau * 100_000,
                                        rappel=_barre(f"{entree}"))
            else:
                profondeur = {1: 4, 2: 8, 3: 16, 4: 24, 5: 32, 6: 48, 7: 64, 8: 96, 9: 128}[args.niveau]
                res = module.compresser(donnees, 1 << min(26, 16 + args.niveau), profondeur,
                                        rappel=_barre(f"{entree}"))
            sortie = args.sortie or entree + ext
        if os.path.exists(sortie) and not args.forcer:
            print(f"{nom}: {sortie} existe déjà (utiliser -f pour écraser)", file=sys.stderr)
            return 1
        with open(sortie, "wb") as f:
            f.write(res)
        if args.verbeux:
            if args.decompresser:
                print(f"{entree} -> {sortie} : {_taille(len(donnees))} -> {_taille(len(res))} "
                      f"en {time.time()-t0:.2f} s")
            else:
                taux = 100 * len(res) / len(donnees) if donnees else 0
                print(f"{entree} -> {sortie} : {_taille(len(donnees))} -> {_taille(len(res))} "
                      f"({taux:.2f} % de l'original, gain {100-taux:.2f} %) en {time.time()-t0:.2f} s")
        if not args.garder:
            os.remove(entree)
    return 0


def _outil_7z(args):
    cmd = args.commande
    if cmd == "a":
        if not args.fichiers:
            print("7z a : précisez au moins un fichier ou dossier à archiver", file=sys.stderr)
            return 1
        profondeur = {1: 4, 3: 16, 5: 32, 7: 64, 9: 128}.get(args.niveau, 48)
        t0 = time.time()
        meta, brut, total = archive7z.creer(args.archive, args.fichiers, 1 << min(26, 16 + args.niveau),
                                            profondeur, _barre("Compression"))
        nb = sum(1 for e in meta if not e["dossier"])
        print(f"Archive {args.archive} créée : {nb} fichier(s), {_taille(brut)} -> {_taille(total)} "
              f"({100*total/brut:.2f} % de l'original)" if brut else f"Archive {args.archive} créée (vide)")
        print(f"Durée : {time.time()-t0:.2f} s")
    elif cmd == "l":
        meta = archive7z.lister(args.archive)
        print(f"{'Date':<17} {'Taille':>12}  {'CRC32':>8}  Nom")
        print("-" * 60)
        tot = 0
        for e in meta:
            d = time.strftime("%Y-%m-%d %H:%M", time.localtime(e["date"]))
            if e["dossier"]:
                print(f"{d:<17} {'<dossier>':>12}  {'':>8}  {e['nom']}/")
            else:
                print(f"{d:<17} {e['taille']:>12}  {e['crc32']:08x}  {e['nom']}")
                tot += e["taille"]
        print("-" * 60)
        print(f"{'':<17} {tot:>12}  {len(meta)} entrée(s)")
    elif cmd in ("x", "t"):
        res = archive7z.extraire(args.archive, args.destination, tester_seulement=(cmd == "t"))
        for nom, ok in res:
            print(("Test OK   " if cmd == "t" else "Extrait   ") + nom)
        print("Aucune erreur." if cmd == "t" else f"Extraction terminée dans {args.destination!r}.")
    return 0


def construire_parseur():
    p = argparse.ArgumentParser(prog="clonecompress",
                                description="Clones pédagogiques de bzip2, lzma et 7-zip.")
    sp = p.add_subparsers(dest="outil", required=True)
    for nom in ("bzip2", "lzma"):
        s = sp.add_parser(nom, help=f"clone de {nom}")
        g = s.add_mutually_exclusive_group()
        g.add_argument("-z", "--compresser", action="store_true", help="compresser (par défaut)")
        g.add_argument("-d", "--decompresser", action="store_true", help="décompresser")
        g.add_argument("-t", "--tester", action="store_true", help="tester l'intégrité")
        s.add_argument("-k", "--garder", action="store_true", help="conserver le fichier d'entrée")
        s.add_argument("-f", "--forcer", action="store_true", help="écraser la sortie existante")
        s.add_argument("-v", "--verbeux", action="store_true", help="afficher les statistiques")
        s.add_argument("-o", "--sortie", help="nom du fichier de sortie")
        s.add_argument("-n", "--niveau", type=int, choices=range(1, 10), default=3,
                       help="niveau 1 (rapide) à 9 (maximal) ; défaut 3")
        s.add_argument("fichiers", nargs="+")
    s = sp.add_parser("7z", help="clone de 7-zip (a, x, l, t)")
    s.add_argument("commande", choices=["a", "x", "l", "t"])
    s.add_argument("archive")
    s.add_argument("fichiers", nargs="*")
    s.add_argument("-o", "--destination", default=".", help="dossier de destination (x, t)")
    s.add_argument("-n", "--niveau", type=int, default=5, choices=range(1, 10), help="niveau 1..9")
    return p


def principal(argv=None):
    args = construire_parseur().parse_args(argv)
    try:
        if args.outil == "7z":
            return _outil_7z(args)
        return _outil_simple(args.outil, args)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(principal())
