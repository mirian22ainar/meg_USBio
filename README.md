# MEGIO_USBio — Tests de performance Arduino pour triggers et boutons FORP

Ce dépôt contient l’ensemble des tests et outils développés pour valider la **précision temporelle** et la **fiabilité** du microcontrôleur Arduino dans le cadre des expériences MEG (magnétoencéphalographie).

---

## ⚙️ Objectif

- Vérifier la latence et la stabilité temporelle des **triggers TTL générés** par l’Arduino.
- Mesurer le délai de détection des **appuis sur les boutons FORP**.
- Fournir une **API Python simple** (`meg_client.py`) pour piloter l’Arduino.
- Proposer des **exemples de scripts** utilisant cette API, jusqu’à une intégration complète dans une expérience **Expyriment**.

---

## 🧩 Composants du projet

### 🔸 1. Firmware Arduino

Le fichier [`meg_protocol.ino`](arduino/meg_protocol.ino) définit le protocole série :
- Commandes binaires pour le contrôle des triggers et la lecture des boutons.
- Gestion d’un temps de pulse configurable (en ms).
- Refractory period configurable.
- Transmission des états des 8 lignes boutons.

Les lignes utilisées sont :
| Ligne | Broche Arduino | Signal STI | Fonction / Bouton FORP |
|:------|:----------------|:------------|:------------------------|
| 0 | 22 | STI010 | Rouge gauche |
| 1 | 23 | STI009 | Vert gauche |
| 2 | 24 | STI015 | Rouge droit |
| 3 | 25 | STI014 | Vert droit |
| 4 | 26 | STI007 | Bleu gauche |
| 5 | 27 | STI008 | Jaune gauche |
| 6 | 28 | STI012 | Bleu droit |
| 7 | 29 | STI013 | Jaune droit |

*(Voir `docs/forp_mapping.png` pour le schéma complet.)*

---

### 🔸 2. API Python (`meg_client.py`)

Interface série simplifiée pour communiquer avec le firmware Arduino.  
Elle permet :
```python
from meg_client import MegClient

with MegClient('/dev/ttyACM0') as dev:
    dev.set_trigger_duration(5)
    dev.send_trigger_mask(0b00001111)
    m = dev.get_response_button_mask()
    print(dev.decode_forp(m))
