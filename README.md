# MEGIO_USBio — Design of an Arduino-Based Device for Triggers and Response Buttons

This repository contains the Python API *meg_client.py* and the Arduino firmware *meg_protocol.ino*, enabling the implementation and use of an Arduino-based solution in the MEG environment to replace the legacy parallel ports.  
It also includes all the tests and tools developed to validate the **temporal precision** and **reliability** of the Arduino microcontroller within MEG (magnetoencephalography) experiments.


## Objectives

- Provide a **simple Python API** (`meg_client.py`) to control the Arduino.  
- Verify the latency and temporal stability of the **TTL triggers generated** by the Arduino.  
- Measure the detection delay of **FORP button presses**.  
- Offer **example scripts** using this API, up to full integration within an **Expyriment** experimental framework.


### Folder and File Description

#### 1. **`arduino/`**
This folder contains the Arduino source codes used to handle serial communication and trigger generation.  
These programs must be flashed to the microcontroller before usage.

- **[`meg_protocol.ino`](arduino/meg_protocol.ino)** — Main firmware managing the serial protocol between the Arduino and the MEG system, as well as trigger generation on specific output lines.  
- **[`recep_exec.ino`](arduino/recep_exec.ino)** — A test/receiver version used to simulate and verify the timing of response button detection.

#### 2. **`python/`**
This folder contains Python scripts used to interact with the Arduino microcontroller and perform tests.

- **[`meg_client.py`](python/meg_client.py)** and **[`meg_client_eng.py`](python/meg_client_eng.py)** — Python APIs (in French and English) for serial communication with the Arduino.  
  They define methods to send triggers and read response buttons in a simple and efficient way. These methods can be integrated directly into your experimental scripts.  
- **[`test_meg_client.py`](python/test_meg_client.py)** and **[`test_meg_client_eng.py`](python/test_meg_client_eng.py)** — Main testing script that verifies trigger and button functionality using **all** methods defined in the API.  
- **[`test_meg2.py`](python/test_meg2.py)** — Basic example measuring the delay between the display of an image on the computer screen and the detection of a button press connected to pins 22–29 of the Arduino.  
  This test can be run locally using a portable response button such as a Putikeeg.  
- **[`simple-detection-visual-expyriment.py`](python/simple-detection-visual-expyriment.py)** — Concrete example using several API methods to implement a visual detection task in Expyriment, measuring participant reaction times.

#### 3. **`notebooks/`**
This folder contains Jupyter notebooks used to analyze test results.

- **[`verif_test_meg_client.ipynb`](notebooks/verif_test_meg_client.ipynb)** — Verifies the latency and timing precision of triggers by analyzing test data produced with `test_meg_client.py`.  
- **[`check_triggers.ipynb`](notebooks/check_triggers.ipynb)** — Temporal analysis of recorded triggers, useful for evaluating their performance and accuracy.

#### 4. **`docs/`**
This folder contains schematics and additional documentation.

- **[`forp_mapping.ipynb`](docs/forp_mapping.ipynb)** and **[`forp_mapping_eng.ipynb`](docs/forp_mapping_eng.ipynb)** — Notebook detailing the wiring layout for integrating the Arduino into the existing MEG system.  
- **[`schematic_forp_mapping.png`](docs/schematic_forp_mapping.png)** — Diagram showing the correspondence between STI box lines and FORP buttons.  
- **[`schematic_Stim-MEG.png`](docs/schematic_Stim-MEG.png)** — Global system diagram showing physical connections between the Arduino, STI box, and FORP box, useful for hardware setup.


### Prerequisites

- Installed **Arduino IDE**

Before running the Python scripts, make sure the following dependencies are installed:

- **Python 3.x**  
- **pyserial** — For serial communication with the Arduino.  
- **expyriment** — For running Expyriment-based experiments.


### How to Use the Device for MEG Experiments

You will need:
- The API *meg_client.py*  
- Your Python experiment script using this API (e.g., *simple-detection-visual-expyriment.py*)  
- The Arduino firmware *meg_protocol.ino*  
- The physical Arduino setup  

Steps to follow:
1. Copy the Python API into the folder containing your experiment scripts.  
2. Open the *meg_protocol.ino* file in the Arduino IDE.  
3. Connect the Arduino device to your computer via USB.  
4. Ensure that the board and port are correctly detected under *Tools*.  
5. Check that the port name matches the one defined in your Python script.  
6. Verify that the board settings are properly configured under *Tools*:  
   - *Tools → Board: "Arduino Mega or Mega 2560"*  
   - *Processor: ATmega2560 (Mega 2560)*  
7. Upload the code to the Arduino by clicking *Upload*.  
8. Connect the cables following the provided wiring diagram.  

You are now ready to launch your Python script!

---

# MEGIO_USBio — Conception d'un dispositif Arduino pour triggers et boutons réponses

Ce dépôt contient une API *meg_client.py* et un code arduino *meg_protocol.ino* permettant l'implémentation et l'utilisation de la solution Arduino proposée en salle MEG pour remplacer les ports parallèles. Il contient également l’ensemble des tests et outils développés pour valider la **précision temporelle** et la **fiabilité** du microcontrôleur Arduino dans le cadre des expériences MEG (magnétoencéphalographie). 


## Objectifs

- Fournir une **API Python simple** (`meg_client.py`) pour piloter l’Arduino.
- Vérifier la latence et la stabilité temporelle des **triggers TTL générés** par l’Arduino.
- Mesurer le délai de détection des **appuis sur les boutons FORP**.
- Proposer des **exemples de scripts** utilisant cette API, jusqu’à une intégration complète dans une expérience **Expyriment**.


### Description des dossiers et fichiers

#### 1. **`arduino/`** 
Ce dossier contient les codes Arduino utilisés pour gérer la communication série avec le microcontrôleur et l'envoi des triggers. Ils sont donc à flasher sur le microcontôleur au besoin pour pouvoir poursuivre.

- **[`meg_protocol.ino`](arduino/meg_protocol.ino)** : Le firmware principal pour la gestion du protocole série entre l'Arduino et le système MEG, ainsi que la génération de triggers sur des lignes spécifiques.
- **[`recep_exec.ino`](arduino/recep_exec.ino)** : Une version de test/réception permettant de simuler et vérifier le timing de détection des appuis sur les boutons réponses.

#### 2. **`python/`**
Ce dossier contient les scripts Python pour interagir avec le microcontrôleur Arduino et effectuer des tests.

- **[`meg_client.py`](python/meg_client.py)** et **[`meg_client_eng.py`](python/meg_client_eng.py)** : API Python (en français et en anglais) pour la communication série avec l'Arduino. Elle définit les méthodes permettant d'envoyer des triggers et de lire les réponses des boutons de manière simple et efficace. Ces méthodes seront donc à intégrer à vos scripts d'expériences au besoin.
- **[`test_meg_client.py`](python/test_meg_client.py)** et **[`test_meg_client_eng.py`](python/test_meg_client_eng.py)** : Le script principal de test qui vérifie le bon fonctionnement des triggers et des boutons en utilisant **toutes** les méthodes définies dans l'API.
- **[`test_meg2.py`](python/test_meg2.py)** : Un exemple d'application basique mesurant la durée séparant l'affichage d'une image sur l'écran de l'ordinateur et la détection d'un appui sur un des boutons branchés au niveau des pins 22-29 de l'Arduino. C'est un test qui peut être réalisé sur son ordinateur portable avec un bouton réponse Putikeeg.
- **[`simple-detection-visual-expyriment.py`](python/simple-detection-visual-expyriment.py)** : Un exemple d'application concret de certaines méthodes pour réaliser une expérience Expyriment de détection visuelle, mesurant le temps de réaction des participants.

#### 3. **`notebooks/`**
Ce dossier contient des notebooks Jupyter utilisés pour analyser les résultats des tests.

- **[`verif_test_meg_client.ipynb`](notebooks/verif_test_meg_client.ipynb)** : Vérifie la latence et la précision des timings des triggers en analysant les résultats des tests effectués avec `test_meg_client.py`.
- **[`check_triggers.ipynb`](notebooks/check_triggers.ipynb)** : Analyse temporelle des triggers enregistrés, utile pour évaluer leur performance et leur exactitude.

#### 4. **`docs/`**
Ce dossier contient des schémas et des fichiers de documentation supplémentaires.

- **[`forp_mapping.ipynb`](docs/forp_mapping.ipynb)** et **[`forp_mapping_eng.ipynb`](docs/forp_mapping_eng.ipynb)**  : notebook reprenant les câblages réalisés pour l'intégration de l'arduino dans le système actuel.
- **[`schematic_forp_mapping.png`](docs/schematic_forp_mapping.png)** : Schéma représentant la correspondance entre les lignes du boîtier STI et les boutons FORP.
- **[`schematic_Stim-MEG.png`](docs/schematic_Stim-MEG.png)** : schéma du système global Détail des connexions physiques entre l'Arduino, le boîtier STI et le boîtier FORP, utile pour les branchements matériels.


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


