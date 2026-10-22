"""Codeur / décodeur par intervalles binaire adaptatif, au style de LZMA.

Probabilités sur 11 bits, adaptation par décalage de 5 bits.
"""

NB_BITS_PROB = 11
PROB_INIT = 1 << (NB_BITS_PROB - 1)   # 1024 = probabilité 0,5
DECALAGE = 5
HAUT = 1 << 24


class CodeurIntervalles:
    def __init__(self):
        self.sortie = bytearray()
        self.bas = 0
        self.intervalle = 0xFFFFFFFF
        self.cache = 0
        self.taille_cache = 1

    def _decaler(self):
        if self.bas < 0xFF000000 or self.bas >= (1 << 32):
            retenue = self.bas >> 32
            temp = self.cache
            while True:
                self.sortie.append((temp + retenue) & 0xFF)
                temp = 0xFF
                self.taille_cache -= 1
                if self.taille_cache == 0:
                    break
            self.cache = (self.bas >> 24) & 0xFF
        self.taille_cache += 1
        self.bas = (self.bas & 0x00FFFFFF) << 8

    def bit(self, probs, i, bit):
        p = probs[i]
        borne = (self.intervalle >> NB_BITS_PROB) * p
        if bit == 0:
            self.intervalle = borne
            probs[i] = p + (((1 << NB_BITS_PROB) - p) >> DECALAGE)
        else:
            self.bas += borne
            self.intervalle -= borne
            probs[i] = p - (p >> DECALAGE)
        while self.intervalle < HAUT:
            self.intervalle = (self.intervalle << 8) & 0xFFFFFFFF
            self._decaler()

    def bits_directs(self, valeur, nb):
        for i in range(nb - 1, -1, -1):
            self.intervalle >>= 1
            if (valeur >> i) & 1:
                self.bas += self.intervalle
            while self.intervalle < HAUT:
                self.intervalle = (self.intervalle << 8) & 0xFFFFFFFF
                self._decaler()

    def arbre(self, probs, nb_bits, valeur):
        """Arbre binaire (bit de poids fort en premier)."""
        m = 1
        for i in range(nb_bits - 1, -1, -1):
            b = (valeur >> i) & 1
            self.bit(probs, m, b)
            m = (m << 1) | b

    def arbre_inverse(self, probs, nb_bits, valeur):
        """Arbre binaire (bit de poids faible en premier)."""
        m = 1
        for i in range(nb_bits):
            b = (valeur >> i) & 1
            self.bit(probs, m, b)
            m = (m << 1) | b

    def terminer(self):
        for _ in range(5):
            self._decaler()
        return bytes(self.sortie)


class DecodeurIntervalles:
    def __init__(self, donnees, debut=0):
        self.d = donnees
        self.pos = debut
        self.intervalle = 0xFFFFFFFF
        self.code = 0
        if len(donnees) - debut < 5:
            raise ValueError("flux trop court")
        self.pos += 1  # le premier octet est toujours 0
        for _ in range(4):
            self.code = (self.code << 8) | self.d[self.pos]
            self.pos += 1

    def _octet(self):
        if self.pos < len(self.d):
            o = self.d[self.pos]
        else:
            raise ValueError("flux de données tronqué")
        self.pos += 1
        return o

    def bit(self, probs, i):
        p = probs[i]
        borne = (self.intervalle >> NB_BITS_PROB) * p
        if self.code < borne:
            self.intervalle = borne
            probs[i] = p + (((1 << NB_BITS_PROB) - p) >> DECALAGE)
            b = 0
        else:
            self.code -= borne
            self.intervalle -= borne
            probs[i] = p - (p >> DECALAGE)
            b = 1
        if self.intervalle < HAUT:
            self.intervalle = (self.intervalle << 8) & 0xFFFFFFFF
            self.code = ((self.code << 8) | self._octet()) & 0xFFFFFFFF
        return b

    def bits_directs(self, nb):
        r = 0
        for _ in range(nb):
            self.intervalle >>= 1
            if self.code >= self.intervalle:
                self.code -= self.intervalle
                b = 1
            else:
                b = 0
            r = (r << 1) | b
            if self.intervalle < HAUT:
                self.intervalle = (self.intervalle << 8) & 0xFFFFFFFF
                self.code = ((self.code << 8) | self._octet()) & 0xFFFFFFFF
        return r

    def arbre(self, probs, nb_bits):
        m = 1
        for _ in range(nb_bits):
            m = (m << 1) | self.bit(probs, m)
        return m - (1 << nb_bits)

    def arbre_inverse(self, probs, nb_bits):
        m = 1
        r = 0
        for i in range(nb_bits):
            b = self.bit(probs, m)
            m = (m << 1) | b
            r |= b << i
        return r
