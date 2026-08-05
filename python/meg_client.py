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

import time
import serial
import struct
from typing import List, Dict

# --- Constantes par défaut ---
DEFAULT_BAUD = 115200      # vitesse de communication série (doit correspondre à celle de l’Arduino)
DEFAULT_TIMEOUT = 0.2      # délai max en s pour lire une réponse avant timeout

# --- OpCodes correspondant aux commandes Arduino ---
OP_GET_INFO               = 1
OP_SET_TRIGGER_DURATION   = 10
OP_SEND_TRIGGER_MASK      = 11
OP_SEND_TRIGGER_ON_LINE   = 12
OP_SET_HIGH_MASK          = 13
OP_SET_LOW_MASK           = 14
OP_SET_HIGH_ON_LINE       = 15
OP_SET_LOW_ON_LINE        = 16
OP_SET_PORT_MASK          = 17
OP_GET_RESPONSE_BUTTON    = 20
OP_GET_EVENT              = 21
OP_GET_MICROS             = 22
OP_CLEAR_EVENTS           = 23
OP_SET_DEBOUNCE           = 24

# --- Bits de capacité renvoyés par get_info() ---
CAP_ATOMIC_PORT = 0x01     # opcode 17 : les 8 lignes écrites en une seule fois
CAP_TIMESTAMPS  = 0x02     # opcodes 21-24 : événements horodatés par micros()

# --- Drapeaux de la réponse à get_event() ---
EV_PRESENT = 0x01          # un événement suit
EV_DROPPED = 0x02          # la file du firmware a débordé ; des événements sont perdus


class FirmwareInfo:
    """Identification renvoyée par MegClient.get_info().

    `legacy` vaut True pour un firmware antérieur à l'opcode 1. Ce firmware
    ignore silencieusement les opcodes inconnus, sans répondre : on le détecte
    donc par l'expiration du délai de lecture et non par un signal positif.
    Seuls les opcodes 10-16 et 20 peuvent être utilisés avec lui.
    """

    def __init__(self, version: int = 0, capabilities: int = 0, legacy: bool = False):
        self.version = version
        self.capabilities = capabilities
        self.legacy = legacy

    def has(self, capability: int) -> bool:
        """True si le firmware annonce le bit CAP_* demandé."""
        return bool(self.capabilities & capability)

    def __repr__(self) -> str:
        if self.legacy:
            return "FirmwareInfo(legacy, pas de get_info)"
        return f"FirmwareInfo(version={self.version}, capabilities=0x{self.capabilities:02X})"


class InputEvent:
    """Un changement d'état des boutons, horodaté par le firmware lui-même.

    `mask` est l'état des boutons APRÈS le changement ; `t_us` est la valeur de
    micros() sur l'Arduino au moment où il a été détecté. Le firmware
    échantillonne à chaque tour de boucle (quelques microsecondes), si bien que
    l'horodatage ne dépend pas du moment où l'hôte pense à interroger la carte —
    contrairement à get_response_button_mask(), dont la résolution est votre
    intervalle d'interrogation.

    micros() reboucle toutes les ~71,6 minutes. Comparez les horodatages avec
    MegClient.elapsed_us(), qui gère ce rebouclage.
    """

    def __init__(self, mask: int, t_us: int):
        self.mask = mask
        self.t_us = t_us

    @property
    def pressed(self) -> bool:
        """True si au moins un bouton est enfoncé après cet événement."""
        return self.mask != 0

    def __repr__(self) -> str:
        return f"InputEvent(mask=0b{self.mask:08b}, t_us={self.t_us})"


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
        # L’ouverture du port déclenche un reset DTR sur l’Arduino ; attendre le démarrage.
        time.sleep(2)

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

    # --------------------------------------------------------------------------
    # Identification du firmware et détection des capacités
    # --------------------------------------------------------------------------

    def get_info(self) -> FirmwareInfo:
        """
        Demande au firmware de s'identifier (opcode 1).

        Un firmware antérieur à la version 1 du protocole n'implémente pas cet
        opcode et ne répond rien : on en déduit « legacy » par l'expiration du
        délai de lecture. Vérifiez les capacités avant d'utiliser un opcode
        au-delà de 20 : un ancien firmware ignore *silencieusement* les opcodes
        inconnus, si bien que l'échec se traduit par une commande sans effet et
        non par une erreur que l'on pourrait rattraper.

        Retour :
        - FirmwareInfo

        Exemple :
        >>> info = dev.get_info()
        >>> if info.has(CAP_TIMESTAMPS):
        ...     ev = dev.wait_for_press()
        """
        self._tx(bytes([OP_GET_INFO]))
        try:
            resp = self._rx_exact(5)
        except TimeoutError:
            return FirmwareInfo(legacy=True)
        if resp[:3] != b"MTB":
            raise RuntimeError(
                f"réponse inattendue à get_info : {resp!r} (est-ce bien un boîtier TTL MEG ?)")
        return FirmwareInfo(version=resp[3], capabilities=resp[4])

    def set_port_mask(self, mask: int) -> None:
        """
        Affecte les 8 lignes de sortie en une seule fois (opcode 17).
        Nécessite CAP_ATOMIC_PORT.

        Contrairement à set_high_mask()/set_low_mask(), qui ne font que mettre à
        1 ou à 0 et demandent donc deux commandes pour exprimer un octet complet,
        cette commande écrit le port entier en une seule instruction. Aucune
        valeur intermédiaire n'apparaît sur les broches : un appareil
        d'enregistrement ne peut donc pas capturer un code de trigger à moitié
        écrit.

        Argument :
        - mask : entier 0-255 ; le bit N met la ligne N à HIGH, un bit à 0 la met à LOW
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask doit être entre 0 et 255")
        self._tx(bytes([OP_SET_PORT_MASK, mask]))

    # --------------------------------------------------------------------------
    # Événements d'entrée horodatés (nécessite CAP_TIMESTAMPS)
    # --------------------------------------------------------------------------

    def get_micros(self) -> int:
        """Lit le compteur micros() de l'Arduino (opcode 22).

        Utile pour aligner les horodatages du firmware sur l'horloge de l'hôte :
        encadrez cet appel entre deux lectures de l'horloge locale et prenez le
        point milieu.
        """
        self._tx(bytes([OP_GET_MICROS]))
        return struct.unpack("<I", self._rx_exact(4))[0]

    def clear_events(self) -> None:
        """
        Vide la file d'événements et réinitialise le détecteur de changement du
        firmware (opcode 23), afin qu'un bouton déjà enfoncé ne soit pas signalé
        comme un nouvel appui. À appeler entre deux essais.
        """
        self._tx(bytes([OP_CLEAR_EVENTS]))

    def set_debounce(self, microseconds: int) -> None:
        """
        Ignore les transitions survenant moins de `microseconds` après la
        précédente (opcode 24). 0 désactive, ce qui est la valeur par défaut.

        Laissez cette option désactivée pour les boîtiers de réponse à fibre
        optique, qui ne rebondissent pas : supprimer de vraies transitions est
        pire que d'en signaler quelques-unes en trop. Utilisez-la pour des
        boutons mécaniques, dont les rebonds peuvent saturer la file de 32
        événements.
        """
        if not (0 <= microseconds <= 65535):
            raise ValueError("le debounce doit être entre 0 et 65535 microsecondes")
        self._tx(bytes([OP_SET_DEBOUNCE]) + struct.pack("<H", microseconds))

    def get_event(self) -> tuple:
        """
        Récupère le plus ancien événement en attente (opcode 21).

        La réponse fait toujours 6 octets, même si la file est vide : l'hôte n'a
        donc jamais à deviner la longueur de ce qui arrive.

        Retour :
        - (event, dropped) où `event` est un InputEvent, ou None si la file était
          vide, et `dropped` vaut True si la file du firmware a débordé depuis
          l'appel précédent.

        Un `dropped` à True signifie que des appuis ont été *perdus*, et non
        simplement retardés : l'essai doit être considéré comme suspect plutôt
        que silencieusement validé.
        """
        self._tx(bytes([OP_GET_EVENT]))
        resp = self._rx_exact(6)
        flags = resp[0]
        dropped = bool(flags & EV_DROPPED)
        if not (flags & EV_PRESENT):
            return None, dropped
        t_us = struct.unpack("<I", resp[2:6])[0]
        return InputEvent(mask=resp[1], t_us=t_us), dropped

    def wait_for_press(self, timeout: float = None) -> "InputEvent":
        """
        Bloque jusqu'à l'appui sur un bouton et renvoie l'événement portant
        l'horodatage de cet appui tel que mesuré par le firmware.

        C'est l'équivalent précis d'une boucle d'interrogation sur
        get_response_button_mask() : votre interrogation ne détermine plus que le
        moment où vous *apprenez* l'appui, et non l'instant enregistré.
        Soustrayez l'horodatage d'apparition du stimulus au `t_us` de
        l'événement pour obtenir un temps de réaction.

        Arguments :
        - timeout : délai d'attente en secondes, ou None pour attendre indéfiniment

        Retour :
        - InputEvent, ou None si le délai a expiré

        Les relâchements sont ignorés. Appelez clear_events() au préalable pour
        écarter les appuis restant de l'essai précédent.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            ev, _ = self.get_event()
            if ev is not None:
                if ev.pressed:
                    return ev
                continue  # un relâchement : on continue de vider la file
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.002)

    @staticmethod
    def elapsed_us(start_us: int, end_us: int) -> int:
        """
        Durée en microsecondes de `start_us` à `end_us`, en corrigeant le
        rebouclage de micros() (~71,6 minutes). Valable pour des intervalles
        inférieurs à environ 35,8 minutes.
        """
        return (end_us - start_us) & 0xFFFFFFFF

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
