from time import sleep, time
from meg_client import MegClient

# --- Parameters ---
PORT = "/dev/ttyACM0"   # adjust according to your machine
N_ATTEMPTS = 8
WINDOW_MS = 5000        # duration of each response window in milliseconds

# --- Response measurement function (max_duration in ms; rt returned in seconds) ---
def get_resp_rt(max_duration):
    # Clear any ongoing button presses (wait until all are released)
    while resp_box.get_response_button_mask() != 0:
        pass
    start = time()
    m = resp_box.get_response_button_mask()
    # Wait for a button press (mask != 0) or until timeout
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

    # --- Trigger test sequence ---
    print("Setting pulse duration = 5 ms")
    resp_box.set_trigger_duration(5)
    sleep(10)

    print("Pulse on lines 0..3 (mask 0b00001111)")
    resp_box.send_trigger_mask(0b00001111)
    sleep(5)

    print("Pulse on line 6")
    resp_box.send_trigger_on_line(6)
    sleep(5)

    print("Force HIGH on lines 0 and 7")
    resp_box.set_high_mask(0b10000001)
    sleep(5)

    print("Reset all lines to LOW")
    resp_box.set_low_mask(0xFF)
    sleep(5)

    print("Set line 2 HIGH, then LOW")
    resp_box.set_high_on_line(2)
    sleep(5)
    resp_box.set_low_on_line(2)
    sleep(5)

    # --- Button press loop: n attempts, 5 s each ---
    print(f"\n>>> Button press series: {N_ATTEMPTS} attempts, {WINDOW_MS} ms per attempt <<<\n")
    for i in range(1, N_ATTEMPTS + 1):
        print(f"[Attempt {i}/{N_ATTEMPTS}] Press a button (window {WINDOW_MS} ms)")
        m, rt = get_resp_rt(WINDOW_MS)

        # Display result
        mask_str = f"{m:08b}" if isinstance(m, int) else str(m)
        print(f"  Raw mask: {mask_str}")
        try:
            decoded = ", ".join(resp_box.decode_forp(m)) or "none"
        except Exception:
            decoded = "n/a"
        print(f"  Detected buttons: {decoded}")
        print(f"  RT (s): {rt if rt is not None else 'no response detected'}\n")

        # Small pause between attempts
        sleep(0.5)

finally:
    try:
        resp_box.close()
    except Exception:
        pass
