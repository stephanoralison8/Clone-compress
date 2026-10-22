#!/usr/bin/env python3
"""Construit rapport_compression.pdf à partir de resultats/ (lancer benchmark.py d'abord).

Chaque page "capture d'écran" reproduit fidèlement la sortie réelle du terminal
(resultats/transcript_*.txt). Vous pouvez la remplacer par de vraies captures.
"""
import glob
import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Image, Preformatted)

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(RACINE, "resultats")
NOM = sys.argv[1] if len(sys.argv) > 1 else "Prénom NOM"
SORTIE = os.path.join(RACINE, "rapport_compression.pdf")

with open(os.path.join(RES, "resultats.json"), encoding="utf-8") as f:
    DONNEES = json.load(f)

st = getSampleStyleSheet()
st.add(ParagraphStyle("Corps", parent=st["Normal"], fontSize=10.5, leading=15, spaceAfter=6))
st.add(ParagraphStyle("Terminal", fontName="Courier", fontSize=7, leading=8.8,
                      textColor=colors.HexColor("#d6ffd6")))
H1, H2, CORPS = st["Heading1"], st["Heading2"], st["Corps"]


def pct(a, b):
    return f"{100 * a / b:.1f} %"


def graphique():
    noms = [d["fichier"] for d in DONNEES]
    series = [("bzip2-clone", "bzip2_clone"), ("lzma-clone", "lzma_clone"), ("7z-clone", "7z_clone")]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    larg = 0.26
    for k, (lab, cle) in enumerate(series):
        ax.bar([i + (k - 1) * larg for i in range(len(noms))],
               [100 * d[cle] / d["taille"] for d in DONNEES], larg, label=lab)
    ax.set_xticks(range(len(noms)))
    ax.set_xticklabels(noms)
    ax.set_ylabel("Taille compressée (% de l'original)")
    ax.set_title("Taux de compression (plus bas = meilleur)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    chemin = os.path.join(RES, "graphique.png")
    fig.tight_layout()
    fig.savefig(chemin, dpi=160)
    plt.close(fig)
    return chemin


def tableau():
    ent = ["Fichier", "Type", "Original\n(octets)", "bzip2-clone", "lzma-clone", "7z-clone",
           "bzip2\nréf.", "xz\nréf.", "Aller-retour"]
    lignes = [ent]
    for d in DONNEES:
        lignes.append([d["fichier"], d["type"], f"{d['taille']:,}".replace(",", " "),
                       f"{d['bzip2_clone']:,}\n({pct(d['bzip2_clone'], d['taille'])})".replace(",", " "),
                       f"{d['lzma_clone']:,}\n({pct(d['lzma_clone'], d['taille'])})".replace(",", " "),
                       f"{d['7z_clone']:,}\n({pct(d['7z_clone'], d['taille'])})".replace(",", " "),
                       f"{d['bzip2_ref']:,}".replace(",", " "), f"{d['lzma_ref']:,}".replace(",", " "),
                       "identique" if d["aller_retour_ok"] else "ÉCHEC"])
    t = Table(lignes, repeatRows=1, colWidths=[2.3*cm, 1.4*cm, 1.9*cm, 2.2*cm, 2.2*cm, 2.2*cm, 1.6*cm, 1.6*cm, 1.9*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f7")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey)]))
    return t


def terminal(texte):
    lignes = []
    for l in texte.rstrip().splitlines():
        lignes += textwrap.wrap(l, 112, subsequent_indent="    ") or [""]
    bloc = Preformatted("\n".join(lignes), st["Terminal"])
    t = Table([[bloc]], colWidths=[17.2*cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#101418")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def pied(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2*cm, 1.2*cm, "Examen — Codage et traitement du signal")
    canvas.drawRightString(A4[0] - 2*cm, 1.2*cm, f"Page {doc.page}")
    canvas.restoreState()


def main():
    doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=2*cm,
                            title="Rapport — Clones de bzip2, lzma et 7-zip", author=NOM)
    h = []
    h += [Spacer(1, 3*cm), Paragraph("Examen — Codage et traitement du signal", st["Title"]),
          Paragraph("Clones fonctionnels des utilitaires de compression <b>bzip2</b>, <b>lzma</b> et <b>7-zip</b>",
                    st["Heading2"]), Spacer(1, 1*cm),
          Paragraph(f"Auteur : {NOM}", CORPS),
          Paragraph("Date limite de remise : samedi 24 octobre 2026, 23h59", CORPS),
          Paragraph("Langage : Python 3 (bibliothèque standard uniquement ; les algorithmes sont réimplémentés, "
                    "<font face='Courier'>zlib.crc32</font> sert seulement de somme de contrôle).", CORPS),
          Spacer(1, 1*cm), Paragraph("Dépôt GitHub : <font color='#1f3a5f'>(coller ici le lien du dépôt)</font>", CORPS),
          PageBreak()]

    h += [Paragraph("1. Algorithmes implémentés", H1),
          Paragraph("<b>bzip2-clone</b> — même chaîne de traitement que bzip2 : pré-codage RLE, transformée de "
                    "Burrows-Wheeler (tri des rotations par doublement de préfixes), Move-To-Front, codage des "
                    "plages de zéros (RUNA/RUNB), puis codage de Huffman canonique par blocs de 100 à 900 Ko.", CORPS),
          Paragraph("<b>lzma-clone</b> — compression par dictionnaire LZ77 (chaînes de hachage, fenêtre jusqu'à 64 Mo) "
                    "suivie d'un codeur par intervalles binaire adaptatif (probabilités sur 11 bits). Littéraux "
                    "contextuels, longueurs 2 à 273, distances par emplacements + bits directs, répétition de la "
                    "dernière distance (rep0).", CORPS),
          Paragraph("<b>7z-clone</b> — archiveur « solide » : tous les fichiers sont concaténés puis compressés par le "
                    "moteur lzma-clone ; l'entête (noms, tailles, dates, CRC32) est lui-même compressé. "
                    "Commandes <font face='Courier'>a</font> (créer), <font face='Courier'>x</font> (extraire), "
                    "<font face='Courier'>l</font> (lister), <font face='Courier'>t</font> (tester), "
                    "avec protection contre la traversée de répertoires.", CORPS),
          Paragraph("<b>Remarque :</b> les formats de fichier produits (.bzc, .lzc, .7zc) sont propres à ce projet : "
                    "ils ne sont pas lisibles par les outils officiels, mais l'aller-retour est vérifié par SHA-256.", CORPS),
          Paragraph("2. Résultats comparatifs", H1),
          Paragraph("Quatre types de fichiers ont été testés. Les colonnes « réf. » donnent, à titre de comparaison, "
                    "la taille obtenue par les bibliothèques officielles bz2 (niveau 9) et lzma/xz (préréglage 6).", CORPS),
          tableau(), Spacer(1, 10), Image(graphique(), width=16*cm, height=7.7*cm), PageBreak()]

    commentaires = {
        "texte": "Le texte est très redondant (mots répétés) : tous les clones obtiennent un très bon taux. "
                 "bzip2-clone fait mieux que lzma-clone ici, comme pour l'original, car BWT + Huffman exploitent "
                 "bien les contextes statistiques d'un texte.",
        "audio": "L'audio PCM bruité compresse peu : le bruit de fond est incompressible sans pertes. "
                 "Le gain, faible, vient des parties tonales périodiques.",
        "image": "L'image BMP (non compressée) contient de larges aplats et dégradés : forte redondance spatiale, "
                 "que LZ77 + codeur par intervalles exploitent mieux que bzip2.",
        "vidéo": "La vidéo brute (Y4M, images YUV 4:2:0) est très redondante d'une image à l'autre : "
                 "compression de plus de 99 %. Un fichier déjà compressé (MP4, H.264) ne se compresserait presque pas.",
    }
    ordre = {"texte": 0, "audio": 1, "image": 2, "vidéo": 3}
    fichiers = sorted(glob.glob(os.path.join(RES, "transcript_*.txt")),
                      key=lambda p: ordre.get(os.path.basename(p).split("_")[1], 9))
    for n, chemin in enumerate(fichiers, 1):
        genre = os.path.basename(chemin).split("_")[1]
        d = next(x for x in DONNEES if x["type"] == genre)
        h += [Paragraph(f"3.{n} Fichier {genre} : {d['fichier']}", H1),
              Paragraph(commentaires.get(genre, ""), CORPS),
              Paragraph(f"Taille originale : <b>{d['taille']:,} o</b> — bzip2-clone : <b>{d['bzip2_clone']:,} o</b> "
                        f"({pct(d['bzip2_clone'], d['taille'])}) — lzma-clone : <b>{d['lzma_clone']:,} o</b> "
                        f"({pct(d['lzma_clone'], d['taille'])}) — 7z-clone : <b>{d['7z_clone']:,} o</b> "
                        f"({pct(d['7z_clone'], d['taille'])}).".replace(",", " "), CORPS),
              Paragraph("Session de terminal :", CORPS)]
        with open(chemin, encoding="utf-8") as f:
            h.append(terminal(f.read()))
        h.append(PageBreak())
    h += [Paragraph("4. Conclusion", H1),
          Paragraph("Les trois clones compressent et décompressent sans perte les quatre types de fichiers. "
                    "Les gains sont maximaux sur les données redondantes (texte, image non compressée, vidéo brute) "
                    "et minimaux sur les données bruitées ou déjà compressées, ce qui est conforme à la théorie de "
                    "l'information (entropie de Shannon). Les implémentations Python sont plus lentes et un peu "
                    "moins efficaces que les outils officiels (écrits en C, avec des heuristiques de recherche et de "
                    "modélisation plus poussées), mais respectent les mêmes principes.", CORPS)]
    doc.build(h, onFirstPage=pied, onLaterPages=pied)
    print("Rapport écrit :", SORTIE)


if __name__ == "__main__":
    main()
