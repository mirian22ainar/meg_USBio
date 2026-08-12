#!/usr/bin/env python3
"""
Measuring reaction times with firmware-timestamped button events.

Why not just poll get_response_button_mask()? Because polling can only tell you
"the press had already happened by the time I asked" — its resolution is your
polling interval, typically several milliseconds, and that error lands directly
in your reaction times.

Firmware from protocol version 1 with CAP_TIMESTAMPS samples the buttons every
loop iteration (a few microseconds) and records micros() at the transition. Your
polling then only determines how soon you *learn* of the press, not the instant
that gets recorded.

Run:
    python3 example_timestamped_rt.py /dev/ttyACM0
"""
import sys
import time

from meg_client_eng import MegClient, CAP_TIMESTAMPS

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
N_TRIALS = 5


def main() -> int:
    with MegClient(PORT) as dev:
        # Always feature-detect. Firmware predating protocol version 1 ignores
        # the event opcodes *silently*, so without this check the failure mode
        # is a program that waits forever rather than one that reports an error.
        info = dev.get_info()
        print(f"firmware: {info}")
        if info.legacy or not info.has(CAP_TIMESTAMPS):
            print("This firmware has no timestamped events.")
            print("Reflash arduino/meg_protocol.ino to enable them.")
            return 1

        # Fibre-optic pads do not bounce, so leave debounce off; enable it only
        # for mechanical buttons, whose chatter can overflow the 32-event queue.
        dev.set_debounce(0)
        dev.set_trigger_duration(5)

        rts = []
        for trial in range(N_TRIALS):
            # Discard anything left over from the previous trial, including a
            # button still being held down.
            dev.clear_events()

            # Stimulus onset. Read the device clock as close to it as possible:
            # both timestamps must come from the same clock to be subtractable.
            onset_us = dev.get_micros()
            dev.send_trigger_on_line(0)
            print(f"\ntrial {trial + 1}: stimulus on, press a button…")

            event = dev.wait_for_press(timeout=5.0)
            if event is None:
                print("  no response within 5 s")
                continue

            # elapsed_us handles the ~71.6 minute micros() wrap.
            rt_us = MegClient.elapsed_us(onset_us, event.t_us)
            rts.append(rt_us)
            print(f"  {dev.decode_forp(event.mask)}")
            print(f"  RT = {rt_us / 1000:.1f} ms")

            # Report lost events rather than trusting the trial silently.
            _, dropped = dev.get_event()
            if dropped:
                print("  WARNING: firmware queue overflowed — presses were lost")

        dev.set_low_mask(0xFF)

    if rts:
        print(f"\n{len(rts)} responses, mean RT = {sum(rts) / len(rts) / 1000:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
