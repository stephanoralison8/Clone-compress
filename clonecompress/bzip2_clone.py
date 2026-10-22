"""Clone de bzip2 : RLE1 -> BWT -> MTF -> RLE des zéros -> Huffman canonique.

Le pipeline est celui de bzip2 ; le conteneur est simplifié (format propre,
non compatible octet pour octet avec les fichiers .bz2 officiels).

Format du fichier (.bzc) :
    "BZC1" | taille_originale u64 | crc32 u32 | nb_blocs u32 | taille_bloc u32
    puis pour chaque bloc : longueur_charge u32 | charge
    charge : indice_bwt u32 | 258 longueurs de codes (octets) | flux de bits Huffman
"""

import struct
import zlib

from .bwt import (transformee_bwt, inverse_bwt, mtf_encoder, mtf_decoder,
                  rle_zeros_encoder, rle_zeros_decoder, rle1_encoder, rle1_decoder)
from .flux_bits import EcrivainBits, LecteurBits
from .huffman import longueurs_huffman, codes_canoniques, DecodeurHuffman

MAGIE = b"BZC1"
NB_SYMBOLES = 258          # RUNA, RUNB, 1..255 décalés (2..256), fin de bloc (257)
FIN_BLOC = 257
ENTETE = struct.Struct("<4sQIII")


def _compresser_bloc(bloc):
    pre = rle1_encoder(bloc)
    derniere, indice = transformee_bwt(pre)
    symboles = rle_zeros_encoder(mtf_encoder(derniere))
    symboles.append(FIN_BLOC)
    freq = [0] * NB_SYMBOLES
    for s in symboles:
        freq[s] += 1
    longueurs = longueurs_huffman(freq)
    codes = codes_canoniques(longueurs)
    ecr = EcrivainBits()
    for s in symboles:
        code, l = codes[s]
        ecr.ecrire(code, l)
    return struct.pack("<I", indice) + bytes(longueurs) + ecr.terminer()


def _decompresser_bloc(charge):
    indice = struct.unpack_from("<I", charge, 0)[0]
    longueurs = list(charge[4:4 + NB_SYMBOLES])
    lecteur = LecteurBits(charge[4 + NB_SYMBOLES:])
    dec = DecodeurHuffman(longueurs)
    symboles = []
    while True:
        s = dec.decoder(lecteur)
        if s == FIN_BLOC:
            break
        symboles.append(s)
    derniere = mtf_decoder(rle_zeros_decoder(symboles))
    return rle1_decoder(inverse_bwt(derniere, indice))


def compresser(donnees, taille_bloc=300_000, rappel=None):
    """Compresse `donnees` (bytes). `rappel(i, total)` est appelé après chaque bloc."""
    blocs = [donnees[i:i + taille_bloc] for i in range(0, len(donnees), taille_bloc)]
    sortie = bytearray(ENTETE.pack(MAGIE, len(donnees), zlib.crc32(donnees),
                                   len(blocs), taille_bloc))
    for i, bloc in enumerate(blocs, 1):
        charge = _compresser_bloc(bloc)
        sortie += struct.pack("<I", len(charge)) + charge
        if rappel:
            rappel(i, len(blocs))
    return bytes(sortie)


def decompresser(compresse):
    if len(compresse) < ENTETE.size:
        raise ValueError("fichier trop court")
    magie, taille, crc, nb_blocs, _ = ENTETE.unpack_from(compresse, 0)
    if magie != MAGIE:
        raise ValueError("ce n'est pas un fichier bzip2-clone (.bzc)")
    pos = ENTETE.size
    sortie = bytearray()
    for _ in range(nb_blocs):
        (longueur,) = struct.unpack_from("<I", compresse, pos)
        pos += 4
        sortie += _decompresser_bloc(compresse[pos:pos + longueur])
        pos += longueur
    if len(sortie) != taille or zlib.crc32(sortie) != crc:
        raise ValueError("données corrompues (CRC32 ou taille incorrects)")
    return bytes(sortie)
