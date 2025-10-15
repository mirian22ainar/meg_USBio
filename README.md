# MEGIO_USBio — Tests de performance Arduino pour triggers et boutons FORP

Ce dépôt contient l’ensemble des tests et outils développés pour valider la **précision temporelle** et la **fiabilité** du microcontrôleur Arduino dans le cadre des expériences MEG (magnétoencéphalographie).

---

## ⚙️ Objectif

- Vérifier la latence et la stabilité temporelle des **triggers TTL générés** par l’Arduino.
- Mesurer le délai de détection des **appuis sur les boutons FORP**.
- Fournir une **API Python simple** (`meg_client.py`) pour piloter l’Arduino.
- Proposer des **exemples de scripts** utilisant cette API, jusqu’à une intégration complète dans une expérience **Expyriment**.

---


### Description des dossiers et fichiers

#### 1. **`arduino/`** 
Ce dossier contient le code Arduino utilisé pour gérer la communication série avec le microcontrôleur et l'envoi des triggers.

- **[`meg_protocol.ino`](arduino/meg_protocol.ino)** : Le firmware principal pour la gestion du protocole série entre l'Arduino et le système MEG, ainsi que la génération de triggers sur des lignes spécifiques.
- **[`recep_exec.ino`](arduino/recep_exec.ino)** : Une version de test/réception permettant de simuler et vérifier les réponses des boutons.

#### 2. **`python/`**
Ce dossier contient les scripts Python pour interagir avec le microcontrôleur Arduino et effectuer des tests.

- **[`meg_client.py`](python/meg_client.py)** : Une API Python pour la communication série avec l'Arduino. Elle permet d'envoyer des triggers et de lire les réponses des boutons de manière simple et efficace.
- **[`test_meg_client.py`](python/test_meg_client.py)** : Le script principal de test qui vérifie le bon fonctionnement des triggers et des boutons.
- **[`test_meg2.py`](python/test_meg2.py)** : Un test basique mesurant la latence de la détection des boutons.
- **[`simple-detection-visual-expyriment.py`](python/simple-detection-visual-expyriment.py)** : Un script complet pour réaliser une expérience Expyriment de détection visuelle, mesurant le temps de réaction des participants.

#### 3. **`notebooks/`**
Ce dossier contient des notebooks Jupyter utilisés pour analyser les résultats des tests.

- **[`verif_test_meg_client.ipynb`](notebooks/verif_test_meg_client.ipynb)** : Vérifie la latence et la précision des timings des triggers en analysant les résultats des tests effectués avec `test_meg_client.py`.
- **[`check_triggers.ipynb`](notebooks/check_triggers.ipynb)** : Analyse temporelle des triggers enregistrés, utile pour évaluer leur performance et leur exactitude.

#### 4. **`docs/`**
Ce dossier contient des schémas et des fichiers de documentation supplémentaires.

- **[`forp_mapping.png`](docs/forp_mapping.png)** : Schéma représentant la correspondance entre les lignes du boîtier STI et les boutons FORP.
- **[`pinout.txt`](docs/pinout.txt)** : Détail des connexions physiques entre l'Arduino, le boîtier STI et le boîtier FORP, utile pour les branchements matériels.

---

### Prérequis

Avant d'exécuter les scripts Python, assure-toi que tu as installé les dépendances nécessaires :

- **Python 3.x**
- **pyserial** : Pour la communication série avec l'Arduino.
- **expyriment** : Pour l'exécution des expériences Expyriment.

Installe les dépendances avec la commande suivante :

```bash
pip install -r requirements.txt
```
