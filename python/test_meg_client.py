from time import sleep, time
from meg_client import MegClient

# --- Paramètres ---
PORT = "/dev/ttyACM0"   # à adapter selon machine
N_ATTEMPTS = 8
WINDOW_MS = 5000        # durée de chaque fenêtre en millisecondes

# --- Fonction de mesure (max_duration en ms ; rt renvoyé en secondes) ---
def get_resp_rt(max_duration):
    # Vider les appuis en cours (attend que tout soit relâché)
    while resp_box.get_response_button_mask() != 0:
        pass
    start = time()
    m = resp_box.get_response_button_mask()
    # Attend un appui (mask != 0) ou l'expiration du délai
    while (m == 0) and (time() - start < (max_duration / 1000)):
        m = resp_box.get_response_button_mask()
    if m != 0:
        rt = time() - start
    else:
        rt = None
    return m, rt

resp_box = MegClient(PORT)
try:
    resp_box.open()

    # --- Séquence de test des triggers ---
    print("Réglage durée pulse = 5 ms")
    resp_box.set_trigger_duration(5)
    sleep(10)

    print("Pulse sur lignes 0..3 (mask 0b00001111)")
    resp_box.send_trigger_mask(0b00001111)
    sleep(5)

    print("Pulse sur la ligne 6")
    resp_box.send_trigger_on_line(6)
    sleep(5)

    print("Forcer HIGH lignes 0 et 7")
    resp_box.set_high_mask(0b10000001)
    sleep(5)

    print("Tout remettre à LOW")
    resp_box.set_low_mask(0xFF)
    sleep(5)

    print("Mettre ligne 2 en HIGH, puis en LOW")
    resp_box.set_high_on_line(2)
    sleep(5)
    resp_box.set_low_on_line(2)
    sleep(5)

    # --- Boucle d'appuis : n tentatives, 5 s chacune ---
    print(f"\n>>> Série d'appuis : {N_ATTEMPTS} tentatives, {WINDOW_MS} ms par tentative <<<\n")
    for i in range(1, N_ATTEMPTS + 1):
        print(f"[Tentative {i}/{N_ATTEMPTS}] Appuie sur un bouton (fenêtre {WINDOW_MS} ms)")
        m, rt = get_resp_rt(WINDOW_MS)

        # Affichage résultat
        mask_str = f"{m:08b}" if isinstance(m, int) else str(m)
        print(f"  Mask brut : {mask_str}")
        try:
            decoded = ", ".join(resp_box.decode_forp(m)) or "aucun"
        except Exception:
            decoded = "n/a"
        print(f"  Boutons détectés : {decoded}")
        print(f"  RT (s) : {rt if rt is not None else 'aucune réponse détectée'}\n")

        # Petite pause entre tentatives
        sleep(0.5)

finally:
    try:
        resp_box.close()
    except Exception:
        pass
