#!/usr/bin/env python3
"""Génère 4 fichiers de test synthétiques dans ./echantillons : texte, audio, image, vidéo.

Aucune dépendance externe. Vous pouvez aussi déposer vos propres fichiers
(.txt, .wav, .bmp, .y4m, .mp4, .png, ...) dans le dossier echantillons/.
"""
import math
import os
import random
import struct
import sys

DOSSIER = sys.argv[1] if len(sys.argv) > 1 else "echantillons"
random.seed(2026)
os.makedirs(DOSSIER, exist_ok=True)


def texte():
    mots = ("le la les un une des de du et ou mais donc car ni que qui quoi dont où "
            "compression données algorithme fichier octet bit signal codage entropie "
            "dictionnaire huffman transformée burrows wheeler intervalle probabilité "
            "redondance fréquence séquence motif répétition mémoire taux gain qualité "
            "système information théorie shannon canal bruit message symbole code "
            "analyse temps espace performance vitesse efficacité résultat étude "
            "exemple méthode principe structure bloc flux lecture écriture").split()
    lignes = []
    taille = 0
    while taille < 300_000:
        phrase = " ".join(random.choice(mots) for _ in range(random.randint(6, 16)))
        phrase = phrase.capitalize() + random.choice([".", ".", ".", " ;", " !", " ?"])
        lignes.append(phrase)
        taille += len(phrase) + 1
        if random.random() < 0.12:
            lignes.append("")
    chemin = os.path.join(DOSSIER, "texte.txt")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))
    return chemin


def audio():
    fe, duree = 22050, 6
    n = fe * duree
    notes = [261.63, 329.63, 392.00, 523.25]
    ech = bytearray()
    for i in range(n):
        t = i / fe
        f = notes[int(t * 2) % len(notes)]
        env = 0.5 * (1 - ((t * 2) % 1) ** 2)
        v = env * (math.sin(2 * math.pi * f * t) + 0.4 * math.sin(2 * math.pi * 2 * f * t))
        v += random.uniform(-0.01, 0.01)        # léger bruit de fond
        ech += struct.pack("<h", int(max(-1, min(1, v / 1.4)) * 32000))
    chemin = os.path.join(DOSSIER, "audio.wav")
    with open(chemin, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(ech)) + b"WAVEfmt " +
                struct.pack("<IHHIIHH", 16, 1, 1, fe, fe * 2, 2, 16) +
                b"data" + struct.pack("<I", len(ech)) + bytes(ech))
    return chemin


def image():
    L, H = 320, 240
    lignes = []
    for y in range(H):
        ligne = bytearray()
        for x in range(L):
            r = int(255 * x / L)
            g = int(255 * y / H)
            b = 128 + int(60 * math.sin(x / 15.0) * math.cos(y / 15.0))
            for cx, cy, ray, col in ((90, 90, 50, (240, 200, 30)), (220, 150, 60, (30, 120, 220))):
                if (x - cx) ** 2 + (y - cy) ** 2 < ray ** 2:
                    r, g, b = col
            ligne += bytes((b & 255, g, r))
        lignes.append(bytes(ligne))
    pixels = b"".join(reversed(lignes))          # BMP : de bas en haut
    taille = 54 + len(pixels)
    chemin = os.path.join(DOSSIER, "image.bmp")
    with open(chemin, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", taille, 0, 0, 54) +
                struct.pack("<IiiHHIIiiII", 40, L, H, 1, 24, 0, len(pixels), 2835, 2835, 0, 0) + pixels)
    return chemin


def video():
    L, H, nb = 160, 120, 20
    chemin = os.path.join(DOSSIER, "video.y4m")
    with open(chemin, "wb") as f:
        f.write(f"YUV4MPEG2 W{L} H{H} F10:1 Ip A1:1 C420jpeg\n".encode())
        for k in range(nb):
            Y = bytearray(L * H)
            for y in range(H):
                for x in range(L):
                    v = 40 + (x + y) // 3
                    if 10 + 6 * k <= x < 40 + 6 * k and 40 <= y < 70:
                        v = 230
                    Y[y * L + x] = v & 255
            U = bytes([110 + k]) * (L * H // 4)
            V = bytes([150 - k]) * (L * H // 4)
            f.write(b"FRAME\n" + bytes(Y) + U + V)
    return chemin


if __name__ == "__main__":
    for fabrique in (texte, audio, image, video):
        c = fabrique()
        print(f"{c} : {os.path.getsize(c):,} octets".replace(",", " "))
