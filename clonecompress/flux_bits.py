"""Lecture / écriture de bits (MSB en premier), utilisées par le clone bzip2."""


class EcrivainBits:
    def __init__(self):
        self.sortie = bytearray()
        self._acc = 0
        self._nb = 0

    def ecrire(self, valeur, nb_bits):
        self._acc = (self._acc << nb_bits) | valeur
        self._nb += nb_bits
        while self._nb >= 8:
            self._nb -= 8
            self.sortie.append((self._acc >> self._nb) & 0xFF)
        self._acc &= (1 << self._nb) - 1

    def terminer(self):
        """Complète le dernier octet avec des zéros et renvoie les octets."""
        if self._nb:
            self.sortie.append((self._acc << (8 - self._nb)) & 0xFF)
            self._acc = 0
            self._nb = 0
        return bytes(self.sortie)


class LecteurBits:
    def __init__(self, donnees):
        self.donnees = donnees
        self.pos = 0       # position de l'octet courant
        self.masque = 0x80

    def lire_bit(self):
        if self.pos >= len(self.donnees):
            raise ValueError("flux de bits tronqué")
        bit = 1 if self.donnees[self.pos] & self.masque else 0
        self.masque >>= 1
        if self.masque == 0:
            self.masque = 0x80
            self.pos += 1
        return bit
