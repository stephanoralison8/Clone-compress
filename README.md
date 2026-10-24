# clonecompress

Clones de **bzip2**, **lzma** et **7-zip** écrits de zéro en Python.
Projet d'examen *Codage et traitement du signal* — RALISON Andriniaina Stephano Michel

## Présentation

| Outil | Principe |
|---|---|
| **bzip2-clone** | Burrows-Wheeler, Move-To-Front, puis codage de Huffman |
| **lzma-clone** | LZ77 (renvoi vers les répétitions) puis codeur par intervalles adaptatif |
| **7z-clone** | archive de plusieurs fichiers / dossiers, compressée avec lzma-clone |

Seule la bibliothèque standard de Python est utilisée : il n'y a **rien à installer** (Python 3.8 ou plus).
Les fichiers produits (`.bzc`, `.lzc`, `.7zc`) sont propres au projet : ils ne s'ouvrent pas avec les vrais outils.

## Utilisation

Se placer dans le dossier du projet. Sous Windows, écrire `py` à la place de `python` si besoin.

```bash
# Créer des fichiers de test (texte, audio, image, vidéo) dans echantillons/
python outils/generer_echantillons.py

# bzip2-clone : compresser / décompresser
python clonecompress.py bzip2 -k -v echantillons/texte.txt
python clonecompress.py bzip2 -d -k -o texte_restaure.txt echantillons/texte.txt.bzc

# lzma-clone : compresser / décompresser
python clonecompress.py lzma -k -v echantillons/image.bmp
python clonecompress.py lzma -d -k -o image_restauree.bmp echantillons/image.bmp.lzc

# 7z-clone : a = créer, l = lister, t = tester, x = extraire
python clonecompress.py 7z a demo.7zc echantillons/texte.txt echantillons/audio.wav
python clonecompress.py 7z l demo.7zc
python clonecompress.py 7z t demo.7zc
python clonecompress.py 7z x demo.7zc -o sortie
```

Options de bzip2 et lzma : `-d` décompresser, `-t` tester, `-k` garder le fichier d'origine,
`-f` écraser la sortie, `-v` afficher les statistiques, `-o` nom de sortie, `-n 1..9` niveau.
Sans `-k`, le fichier d'origine est supprimé après compression.

## Résultats

| Type | Fichier | Original | Outil | Compressé | Gain |
|---|---|---|---|---|---|
| Texte | `texte.txt` | 307,68 Ko | bzip2-clone | 49,72 Ko | 83,84 % |
| Audio | `audio.wav` | 258,44 Ko | lzma-clone | 239,82 Ko | 7,21 % |
| Image | `image.bmp` | 225,05 Ko | lzma-clone | 101,43 Ko | 54,93 % |
| Vidéo | `video.y4m` | 562,66 Ko | bzip2-clone | 4,53 Ko | 99,19 % |

Plus les données sont redondantes, plus le gain est grand. L'audio contient du bruit, donc il compresse peu.

## Tests

```bash
python -m unittest discover -s tests -v    # 9 tests, résultat attendu : OK
python outils/benchmark.py                 # les 3 outils sur les 4 fichiers (long : plusieurs minutes)
```

## Structure

```
clonecompress.py          point d'entrée
clonecompress/            bwt.py, huffman.py, flux_bits.py, bzip2_clone.py,
                          codeur_intervalles.py, lzma_clone.py, archive7z.py, cli.py
tests/                    tests unitaires
outils/                   génération d'échantillons, benchmark
```