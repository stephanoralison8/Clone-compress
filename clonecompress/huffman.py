"""Codage de Huffman canonique (longueurs de codes + codes canoniques)."""

import heapq


def longueurs_huffman(frequences):
    """Calcule la longueur du code de chaque symbole (0 si fréquence nulle)."""
    n = len(frequences)
    longueurs = [0] * n
    presents = [s for s in range(n) if frequences[s] > 0]
    if not presents:
        return longueurs
    if len(presents) == 1:
        longueurs[presents[0]] = 1
        return longueurs
    # tas de (poids, identifiant, [symboles])
    tas = [(frequences[s], s, [s]) for s in presents]
    heapq.heapify(tas)
    compteur = n
    while len(tas) > 1:
        p1, _, s1 = heapq.heappop(tas)
        p2, _, s2 = heapq.heappop(tas)
        for s in s1:
            longueurs[s] += 1
        for s in s2:
            longueurs[s] += 1
        heapq.heappush(tas, (p1 + p2, compteur, s1 + s2))
        compteur += 1
    return longueurs


def codes_canoniques(longueurs):
    """Renvoie {symbole: (code, longueur)} pour des longueurs données."""
    triés = sorted((l, s) for s, l in enumerate(longueurs) if l > 0)
    codes = {}
    code = 0
    longueur_prec = 0
    for l, s in triés:
        code <<= (l - longueur_prec)
        codes[s] = (code, l)
        code += 1
        longueur_prec = l
    return codes


class DecodeurHuffman:
    """Décodage canonique bit par bit (méthode de zlib/puff)."""

    def __init__(self, longueurs):
        self.max_l = max(longueurs) if any(longueurs) else 0
        self.comptes = [0] * (self.max_l + 2)
        for l in longueurs:
            if l:
                self.comptes[l] += 1
        self.symboles = [s for _, s in sorted((l, s) for s, l in enumerate(longueurs) if l)]

    def decoder(self, lecteur):
        code = premier = index = 0
        for l in range(1, self.max_l + 1):
            code |= lecteur.lire_bit()
            nb = self.comptes[l]
            if code - nb < premier:
                return self.symboles[index + (code - premier)]
            index += nb
            premier = (premier + nb) << 1
            code <<= 1
        raise ValueError("code de Huffman invalide")
