# MEGIO_USBio — Conception d'un dispositif Arduino pour triggers et boutons forP

Ce dépôt contient une API *meg_client.py* et un code arduino *meg_protocol.ino* permettant l'implémentation et l'utilisation de la solution proposée en salle MEG. Il contient également l’ensemble des tests et outils développés pour valider la **précision temporelle** et la **fiabilité** du microcontrôleur Arduino dans le cadre des expériences MEG (magnétoencéphalographie). 

---

## Objectif

- Fournir une **API Python simple** (`meg_client.py`) pour piloter l’Arduino.
- Vérifier la latence et la stabilité temporelle des **triggers TTL générés** par l’Arduino.
- Mesurer le délai de détection des **appuis sur les boutons FORP**.
- Proposer des **exemples de scripts** utilisant cette API, jusqu’à une intégration complète dans une expérience **Expyriment**.

---


### Description des dossiers et fichiers

#### 1. **`arduino/`** 
Ce dossier contient les codes Arduino utilisés pour gérer la communication série avec le microcontrôleur et l'envoi des triggers. Ils sont donc à flasher sur le microcontôleur au besoin pour pouvoir poursuivre.

- **[`meg_protocol.ino`](arduino/meg_protocol.ino)** : Le firmware principal pour la gestion du protocole série entre l'Arduino et le système MEG, ainsi que la génération de triggers sur des lignes spécifiques.
- **[`recep_exec.ino`](arduino/recep_exec.ino)** : Une version de test/réception permettant de simuler et vérifier le timing de détection des appuis sur les boutons réponses.

#### 2. **`python/`**
Ce dossier contient les scripts Python pour interagir avec le microcontrôleur Arduino et effectuer des tests.

- **[`meg_client.py`](python/meg_client.py)** : l'API Python pour la communication série avec l'Arduino. Elle définit les méthodes permettant d'envoyer des triggers et de lire les réponses des boutons de manière simple et efficace. Ces méthodes seront donc à intégrer à vos scripts d'expériences au besoin.
- **[`test_meg_client.py`](python/test_meg_client.py)** : Le script principal de test qui vérifie le bon fonctionnement des triggers et des boutons en utilisant **toutes** les méthodes définies dans l'API.
- **[`test_meg2.py`](python/test_meg2.py)** : Un exemple d'application basique mesurant la durée séparant l'affichage d'une image sur l'écran de l'ordinateur et la détection d'un appui sur un des boutons branchés au niveau des pins 22-29 de l'Arduino. C'est un test qui peut être réalisé sur son ordinateur portable avec un bouton réponse Putikeeg.
- **[`simple-detection-visual-expyriment.py`](python/simple-detection-visual-expyriment.py)** : Un exemple d'application concret de certaines méthodes pour réaliser une expérience Expyriment de détection visuelle, mesurant le temps de réaction des participants.

#### 3. **`notebooks/`**
Ce dossier contient des notebooks Jupyter utilisés pour analyser les résultats des tests.

- **[`verif_test_meg_client.ipynb`](notebooks/verif_test_meg_client.ipynb)** : Vérifie la latence et la précision des timings des triggers en analysant les résultats des tests effectués avec `test_meg_client.py`.
- **[`check_triggers.ipynb`](notebooks/check_triggers.ipynb)** : Analyse temporelle des triggers enregistrés, utile pour évaluer leur performance et leur exactitude.

#### 4. **`docs/`**
Ce dossier contient des schémas et des fichiers de documentation supplémentaires.

- **[`forp_mapping.ipynb`](docs/forp_mapping.ipynb)** : notebook reprenant les câblages réalisés pour l'intégration de l'arduino dans le système actuel.
- **[`schematic_forp_mapping.png`](docs/schematic_forp_mapping.png)** : Schéma représentant la correspondance entre les lignes du boîtier STI et les boutons FORP.
- **[`schematic_Stim-MEG.png`](docs/schematic_Stim-MEG.png)** : schéma du système global Détail des connexions physiques entre l'Arduino, le boîtier STI et le boîtier FORP, utile pour les branchements matériels.

---

### Prérequis

- Avoir téléchargé l'**IDE Arduino**


Avant d'exécuter les scripts Python, assure-toi que tu as installé les dépendances nécessaires :

- **Python 3.x**
- **pyserial** : Pour la communication série avec l'Arduino.
- **expyriment** : Pour l'exécution des expériences Expyriment.



### Comment utiliser le dispositif pour une expérience en MEG
 Il vous faut : 
 - l'API *meg_client.py*
 - votre script python utilisant les méthodes de l'API (par exemple : *simple-detection-visual-expyriment.py*)
 - le code "*meg_protocol.ino*
 - le dispositif avec Arduino

 Etapes à suivre :
 - Se munir de l'API python et le placer dans un dossier contenant les futurs scripts python d'expériences.
 - Se munir du code *meg_protocol.ino* et l'ouvrir sur l'IDE Arduino
 - Brancher le dispositif à l'ordinateur par USB
 - S'assurer que la carte/le port est bien détecté dans *Tools*
 - Assurer vous que le port affiché est bien celui défini dans votre script python
 - S'assurer que les paramètres de la carte sont bien configurés dans *Tools* : *Tools/Board : " Arduino Mega or Mega 2560* et *Processor : ATMega 2560 (2560)*
 - Téléverser le code sur la carte arduino en cliquant sur *Upload*
 - Brancher les câbles en suivant le schéma de câblage fourni.
 Il ne vous reste plus qu'à lancer votre script python !


