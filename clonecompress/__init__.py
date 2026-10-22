"""clonecompress : clones pédagogiques de bzip2, lzma et 7-zip, écrits de zéro en Python.

Seuls zlib.crc32 (somme de contrôle) et la bibliothèque standard sont utilisés ;
les algorithmes de compression (BWT, MTF, Huffman, LZ77, codeur par intervalles)
sont entièrement réimplémentés dans ce paquet.
"""

__version__ = "1.0.0"
