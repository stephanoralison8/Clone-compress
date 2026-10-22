"""Tests unitaires : python -m unittest discover -s tests -v"""
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clonecompress import bzip2_clone, lzma_clone, archive7z
from clonecompress.bwt import (transformee_bwt, inverse_bwt, mtf_encoder, mtf_decoder,
                               rle_zeros_encoder, rle_zeros_decoder, rle1_encoder, rle1_decoder)

random.seed(42)
CAS = [
    b"", b"a", b"ab", b"aaaa", b"a" * 1000, b"abracadabra" * 50, bytes(range(256)) * 3,
    os.urandom(4000), b"x" * 300 + b"y" + b"x" * 5,
    bytes(random.choice(b"abc") for _ in range(20000)),
    "Élève à l'école : garçon, être, œuvre, ça va ? ".encode("utf-8") * 200,
    (b"0123456789" * 7 + b"Z") * 300,
]


class TestBWT(unittest.TestCase):
    def test_banane(self):
        derniere, i = transformee_bwt(b"banana")
        self.assertEqual(inverse_bwt(derniere, i), b"banana")

    def test_aller_retour(self):
        for d in CAS:
            d = d[:5000]
            self.assertEqual(inverse_bwt(*transformee_bwt(d)), d)

    def test_mtf_rle(self):
        for d in CAS:
            self.assertEqual(mtf_decoder(mtf_encoder(d)), d)
            idx = mtf_encoder(d)
            self.assertEqual(rle_zeros_decoder(rle_zeros_encoder(idx)), idx)
            self.assertEqual(rle1_decoder(rle1_encoder(d)), d)


class TestBzip2(unittest.TestCase):
    def test_aller_retour(self):
        for d in CAS:
            for bloc in (100, 7000, 300_000):
                self.assertEqual(bzip2_clone.decompresser(bzip2_clone.compresser(d, bloc)), d)

    def test_corruption(self):
        c = bytearray(bzip2_clone.compresser(b"bonjour " * 500))
        c[-3] ^= 0xFF
        with self.assertRaises(Exception):
            bzip2_clone.decompresser(bytes(c))


class TestLzma(unittest.TestCase):
    def test_aller_retour(self):
        for d in CAS:
            for dico in (1 << 10, 1 << 16, 1 << 20):
                self.assertEqual(lzma_clone.decompresser(lzma_clone.compresser(d, dico)), d)

    def test_corruption(self):
        c = bytearray(lzma_clone.compresser(os.urandom(2000)))
        c[len(c) // 2] ^= 0xFF
        with self.assertRaises(Exception):
            lzma_clone.decompresser(bytes(c))


class Test7z(unittest.TestCase):
    def test_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "dossier")
            os.makedirs(os.path.join(src, "sous"))
            with open(os.path.join(src, "a.txt"), "wb") as f:
                f.write(b"bonjour " * 300)
            with open(os.path.join(src, "sous", "b.bin"), "wb") as f:
                f.write(os.urandom(3000))
            arc = os.path.join(tmp, "t.7zc")
            archive7z.creer(arc, [src])
            self.assertEqual(len(archive7z.lister(arc)), 4)
            dest = os.path.join(tmp, "sortie")
            archive7z.extraire(arc, dest)
            for rel in ("a.txt", os.path.join("sous", "b.bin")):
                with open(os.path.join(src, rel), "rb") as f1, \
                        open(os.path.join(dest, "dossier", rel), "rb") as f2:
                    self.assertEqual(f1.read(), f2.read())

    def test_traversee_repertoire(self):
        for mauvais in ("../evil", "/etc/passwd", "a/../../b"):
            with self.assertRaises(ValueError):
                archive7z._nom_sur(mauvais)


if __name__ == "__main__":
    unittest.main()
