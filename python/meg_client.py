"""
meg_client.py — Client Python pour la communication avec un Arduino dans le cadre d’expériences MEG (gestion de triggers et boutons réponse).

====================================================================================
Objectif
------------------------------------------------------------------------------------
Ce module fournit une interface haut-niveau pour dialoguer avec un microcontrôleur Arduino
connecté à un système MEG. Il permet :
    - d’envoyer des triggers TTL (pulses numériques) sur des lignes précises
    - de fixer des lignes à HIGH ou LOW de manière persistante
    - de lire l’état des boutons réponse (boîtier FORP, par ex.)

====================================================================================
Protocole de communication série
------------------------------------------------------------------------------------
- Communication via port série (USB)
- Encodage binaire : chaque commande commence par un opcode (entier 0–255)
- Les arguments éventuels suivent sous forme d’octets supplémentaires (bytes([...]))
- Toutes les valeurs sont des entiers non signés entre 0 et 255 (ou 0–65535 pour les durées)

Commandes disponibles (opcodes décimaux) :
  10 : set_trigger_duration   [2 octets : durée en ms, entier 0–65535]
  11 : send_trigger_mask      [1 octet : mask 0–255]
  12 : send_trigger_on_line   [1 octet : numéro de ligne 0–7]
  13 : set_high_mask          [1 octet : mask 0–255]
  14 : set_low_mask           [1 octet : mask 0–255]
  15 : set_high_on_line       [1 octet : numéro de ligne 0–7]
  16 : set_low_on_line        [1 octet : numéro de ligne 0–7]
  20 : get_response_button_mask -> Arduino renvoie 1 octet (mask 0–255)
====================================================================================

Exemple minimal :
------------------------------------------------------------------------------------
from meg_client import MegClient

with MegClient('/dev/ttyACM0') as dev:
    dev.set_trigger_duration(5)          # définit la largeur du trigger à 5 ms
    dev.send_trigger_on_line(3)          # génère un trigger sur la ligne 3
    mask = dev.get_response_button_mask() # lit les boutons appuyés
    print(mask, dev.decode_forp(mask))
====================================================================================
"""

import serial
import struct
from typing import List, Dict

# --- Constantes par défaut ---
DEFAULT_BAUD = 115200      # vitesse de communication série (doit correspondre à celle de l’Arduino)
DEFAULT_TIMEOUT = 0.2      # délai max en s pour lire une réponse avant timeout

# --- OpCodes correspondant aux commandes Arduino ---
OP_SET_TRIGGER_DURATION   = 10
OP_SEND_TRIGGER_MASK      = 11
OP_SEND_TRIGGER_ON_LINE   = 12
OP_SET_HIGH_MASK          = 13
OP_SET_LOW_MASK           = 14
OP_SET_HIGH_ON_LINE       = 15
OP_SET_LOW_ON_LINE        = 16
OP_GET_RESPONSE_BUTTON    = 20


class MegClient:
    """
    Classe principale pour la communication série avec le microcontrôleur Arduino.

    Chaque méthode correspond à une commande envoyée à l’Arduino, selon le protocole défini plus haut.

    Exemple d’utilisation :
    -----------------------
    >>> from meg_client import MegClient
    >>> with MegClient('/dev/ttyACM0') as dev:
    ...     dev.set_trigger_duration(5)
    ...     dev.send_trigger_mask(0b00001111)
    ...     mask = dev.get_response_button_mask()
    ...     print(mask, dev.decode_forp(mask))
    """

    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialise la connexion série (sans encore l’ouvrir).

        Arguments :
        - port : chemin du port série (ex. '/dev/ttyACM0' sous Linux, 'COM3' sous Windows)
        - baud : vitesse de communication (baudrate)
        - timeout : durée maximale d’attente d’une réponse (en secondes)
        """
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser: serial.Serial | None = None

        # Dictionnaire de correspondance entre bits du mask et boutons physiques FORP
        self.forp_map: Dict[int, str] = {
        0: "bouton bleu gauche activé",   # STI007 (out) pin 22
        1: "bouton jaune gauche activé",  # STI008 (out) pin 23
        2: "bouton vert gauche activé",   # STI009 (out) pin 24
        3: "bouton rouge gauche activé",  # STI010 (out) pin 25
        4: "bouton bleu droit activé",    # STI012 (out) pin 26
        5: "bouton jaune droit activé",   # STI013 (out) pin 27
        6: "bouton vert droit activé",    # STI014 (out) pin 28
        7: "bouton rouge droit activé",   # STI015 (out) pin 29
        }

    # --------------------------------------------------------------------------
    # 🔌 Gestion du port série
    # --------------------------------------------------------------------------

    def open(self):
        """Ouvre la connexion série si elle n’est pas déjà ouverte."""
        if self.ser and self.ser.is_open:
            return
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)

    def close(self):
        """Ferme proprement la connexion série."""
        if self.ser:
            try:
                self.ser.close()
            finally:
                self.ser = None

    def __enter__(self):
        """Permet l’utilisation avec un contexte 'with MegClient(...) as dev:'"""
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        """Ferme automatiquement la connexion à la fin du bloc with."""
        self.close()

    def _ensure(self):
        """Vérifie qu’une connexion série est bien ouverte avant envoi."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Port série non ouvert — appelez dev.open() avant d’envoyer des commandes.")

    def _tx(self, data: bytes):
        """Envoie un paquet d’octets sur le port série."""
        self._ensure()
        self.ser.write(data)
        self.ser.flush()  # vide le buffer pour assurer un envoi immédiat

    def _rx_exact(self, n: int) -> bytes:
        """Lit exactement n octets depuis le port série, sinon lève TimeoutError."""
        self._ensure()
        buf = self.ser.read(n)
        if len(buf) != n:
            raise TimeoutError(f"Lecture incomplète : attendu {n} octets, reçu {len(buf)}")
        return buf

    # --------------------------------------------------------------------------
    # API — Commandes de haut niveau envoyées à l’Arduino
    # --------------------------------------------------------------------------

    def set_trigger_duration(self, duration_ms: int) -> None:
        """
        Définit la durée (en ms) du signal TTL généré pour chaque trigger.

        Argument :
        - duration_ms : entier entre 0 et 65535 (valeur 5 = 5 ms)

        Exemple :
        >>> dev.set_trigger_duration(5)
        """
        if duration_ms < 0 or duration_ms > 65535:
            raise ValueError("duration_ms doit être entre 0 et 65535")
        payload = struct.pack("<BH", OP_SET_TRIGGER_DURATION, duration_ms)
        self._tx(payload)

    def send_trigger_mask(self, mask: int) -> None:
        """
        Génère un trigger sur toutes les lignes dont le bit du mask vaut 1.

        Argument :
        - mask : entier binaire entre 0 et 255 (ex. 0b00001111 active les 4 premières lignes)
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask doit être entre 0 et 255")
        self._tx(bytes([OP_SEND_TRIGGER_MASK, mask]))

    def send_trigger_on_line(self, line: int) -> None:
        """
        Génère un trigger sur une seule ligne (numéro entre 0 et 7).

        Exemple :
        >>> dev.send_trigger_on_line(3)  # active la ligne 3 pendant la durée définie
        """
        if not (0 <= line <= 7):
            raise ValueError("line doit être entre 0 et 7")
        self._tx(bytes([OP_SEND_TRIGGER_ON_LINE, line]))

    def set_high_mask(self, mask: int) -> None:
        """
        Passe en HIGH toutes les lignes correspondant aux bits à 1 dans le mask.
        (État maintenu indéfiniment, pas un trigger.)

        Exemple :
        >>> dev.set_high_mask(0b00000011)  # lignes 0 et 1 passent en HIGH
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask doit être entre 0 et 255")
        self._tx(bytes([OP_SET_HIGH_MASK, mask]))

    def set_low_mask(self, mask: int) -> None:
        """
        Passe en LOW toutes les lignes correspondant aux bits à 1 dans le mask.

        Exemple :
        >>> dev.set_low_mask(0b00001111)  # force les 4 premières lignes à LOW
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask doit être entre 0 et 255")
        self._tx(bytes([OP_SET_LOW_MASK, mask]))

    def set_high_on_line(self, line: int) -> None:
        """Passe une seule ligne (0–7) en HIGH, de manière persistante."""
        if not (0 <= line <= 7):
            raise ValueError("line doit être entre 0 et 7")
        self._tx(bytes([OP_SET_HIGH_ON_LINE, line]))

    def set_low_on_line(self, line: int) -> None:
        """Passe une seule ligne (0–7) en LOW, de manière persistante."""
        if not (0 <= line <= 7):
            raise ValueError("la ligne doit être entre 0 et 7")
        self._tx(bytes([OP_SET_LOW_ON_LINE, line]))

    def get_response_button_mask(self) -> int:
        """
        Lit l’état des boutons du boîtier de réponse.

        Retour :
        - entier (mask 0–255) dont les bits à 1 indiquent les boutons pressés.
        - exemple : 0b00000100 signifie que le bouton 2 est appuyé.

        Exemple :
        >>> mask = dev.get_response_button_mask()
        >>> print(bin(mask))
        """
        self._tx(bytes([OP_GET_RESPONSE_BUTTON]))
        resp = self._rx_exact(1)
        return resp[0]

    def decode_forp(self, mask: int) -> List[str]:
        """
        Traduit le mask renvoyé par `get_response_button_mask()` en texte lisible.

        Argument :
        - mask : entier entre 0 et 255

        Retour :
        - liste de chaînes correspondant aux boutons activés

        Exemple :
        >>> mask = dev.get_response_button_mask()
        >>> dev.decode_forp(mask)
        ['bouton rouge droit activé', 'bouton bleu gauche activé']
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask doit être entre 0 et 255")
        msgs: List[str] = []
        for bit in range(8):
            if (mask >> bit) & 1:
                label = self.forp_map.get(bit, f"ligne {bit} activée")
                msgs.append(label)
        return msgs
