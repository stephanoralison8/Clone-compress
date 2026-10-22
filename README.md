# clonecompress — clones de bzip2, lzma et 7-zip (Python)

Projet d'examen *Codage et traitement du signal*. Réimplémentation **de zéro** (bibliothèque standard
uniquement, `zlib.crc32` servant seulement de somme de contrôle) de trois utilitaires de compression.

| Outil | Algorithmes réimplémentés |
|---|---|
| `bzip2` | RLE → **Burrows-Wheeler** → **Move-To-Front** → RLE des zéros (RUNA/RUNB) → **Huffman canonique**, par blocs |
| `lzma`  | **LZ77** (chaînes de hachage) + **codeur par intervalles** binaire adaptatif, littéraux contextuels, `rep0` |
| `7z`    | archive solide (flux LZMA unique) + entête compressé ; commandes `a`, `x`, `l`, `t` |

> Les formats produits (`.bzc`, `.lzc`, `.7zc`) sont propres au projet : ils ne sont pas lisibles par les outils
> officiels, mais l'aller-retour est garanti (CRC32 + tests SHA-256).

## Utilisation (Python 3.8+, aucune installation)

```bash
# bzip2-clone : -z compresser (défaut) | -d décompresser | -t tester | -k garder | -v stats | -n 1..9
python clonecompress.py bzip2 -k -v fichier.txt          # -> fichier.txt.bzc
python clonecompress.py bzip2 -d -k fichier.txt.bzc      # -> fichier.txt

# lzma-clone
python clonecompress.py lzma -k -v fichier.wav           # -> fichier.wav.lzc
python clonecompress.py lzma -d -k fichier.wav.lzc

# 7z-clone
python clonecompress.py 7z a archive.7zc dossier fichier.txt   # créer
python clonecompress.py 7z l archive.7zc                       # lister
python clonecompress.py 7z t archive.7zc                       # tester
python clonecompress.py 7z x archive.7zc -o sortie             # extraire
```

## Tests et démonstration

```bash
python -m unittest discover -s tests -v      # 9 tests unitaires (aller-retour, corruption, sécurité)
python outils/generer_echantillons.py        # crée texte / audio / image / vidéo de test
python outils/benchmark.py                   # lance les 3 clones sur chaque fichier, vérifie SHA-256
python outils/generer_rapport.py "Prénom NOM"   # produit rapport_compression.pdf
```

Pour tester vos propres fichiers (`.txt`, `.wav`, `.bmp`, `.png`, `.mp4`, ...), déposez-les dans `echantillons/`
avant de lancer `benchmark.py`. Remarque : un fichier déjà compressé (MP3, JPEG, MP4) ne se compresse presque pas.

## Structure

```
clonecompress.py        point d'entrée
clonecompress/          bwt.py, huffman.py, flux_bits.py, bzip2_clone.py,
                        codeur_intervalles.py, lzma_clone.py, archive7z.py, cli.py
tests/                  tests unitaires
outils/                 échantillons, benchmark, rapport PDF
resultats/              sessions de terminal et chiffres
```
