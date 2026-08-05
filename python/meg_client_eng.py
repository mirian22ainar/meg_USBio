"""
meg_client_eng.py — Python client for communication with an Arduino board in the context of MEG experiments (trigger and response button management).

====================================================================================
Purpose
------------------------------------------------------------------------------------
This module provides a high-level interface for communication with an Arduino
microcontroller connected to a MEG system. It allows you to:
    - send TTL triggers (digital pulses) on specific output lines
    - set lines to HIGH or LOW persistently
    - read the state of response buttons (e.g. FORP response box)

====================================================================================
Serial communication protocol
------------------------------------------------------------------------------------
- Communication via serial port (USB)
- Binary encoding: each command starts with an opcode (integer 0–255)
- Optional arguments follow as additional bytes (bytes([...]))
- All values are unsigned integers between 0–255 (or 0–65535 for durations)

Available commands (decimal opcodes):
  10 : set_trigger_duration   [2 bytes: duration in ms, integer 0–65535]
  11 : send_trigger_mask      [1 byte: mask 0–255]
  12 : send_trigger_on_line   [1 byte: line number 0–7]
  13 : set_high_mask          [1 byte: mask 0–255]
  14 : set_low_mask           [1 byte: mask 0–255]
  15 : set_high_on_line       [1 byte: line number 0–7]
  16 : set_low_on_line        [1 byte: line number 0–7]
  20 : get_response_button_mask -> Arduino returns 1 byte (mask 0–255)
====================================================================================

Minimal example:
------------------------------------------------------------------------------------
from meg_client import MegClient

with MegClient('/dev/ttyACM0') as dev:
    dev.set_trigger_duration(5)           # sets trigger pulse width to 5 ms
    dev.send_trigger_on_line(3)           # sends a trigger on line 3
    mask = dev.get_response_button_mask() # reads pressed buttons
    print(mask, dev.decode_forp(mask))
====================================================================================
"""

import time
import serial
import struct
from typing import List, Dict

# --- Default constants ---
DEFAULT_BAUD = 115200      # serial communication speed (must match Arduino)
DEFAULT_TIMEOUT = 0.2      # max waiting time (s) before read timeout

# --- OpCodes corresponding to Arduino commands ---
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

# --- Capability bits reported by get_info() ---
CAP_ATOMIC_PORT = 0x01     # opcode 17: all 8 lines assigned in one port write
CAP_TIMESTAMPS  = 0x02     # opcodes 21-24: micros()-timestamped input events

# --- get_event() reply flags ---
EV_PRESENT = 0x01          # an event follows
EV_DROPPED = 0x02          # the firmware queue overflowed; events were lost


class FirmwareInfo:
    """Identification returned by MegClient.get_info().

    `legacy` is True for firmware predating opcode 1. Such firmware ignores
    unknown opcodes without replying, so it is detected by the probe timing
    out rather than by any positive signal; only opcodes 10-16 and 20 may be
    used against it.
    """

    def __init__(self, version: int = 0, capabilities: int = 0, legacy: bool = False):
        self.version = version
        self.capabilities = capabilities
        self.legacy = legacy

    def has(self, capability: int) -> bool:
        """True if the firmware advertises the given CAP_* bit."""
        return bool(self.capabilities & capability)

    def __repr__(self) -> str:
        if self.legacy:
            return "FirmwareInfo(legacy, no get_info)"
        return f"FirmwareInfo(version={self.version}, capabilities=0x{self.capabilities:02X})"


class InputEvent:
    """A button transition timestamped by the firmware itself.

    `mask` is the button state AFTER the change; `t_us` is the Arduino's
    micros() value at the moment it was detected. Because the firmware samples
    every loop iteration (a few microseconds), the timestamp does not depend on
    when the host got round to asking — unlike get_response_button_mask(),
    whose resolution is your polling interval.

    micros() wraps every ~71.6 minutes. Compare timestamps with
    MegClient.elapsed_us(), which handles the wrap.
    """

    def __init__(self, mask: int, t_us: int):
        self.mask = mask
        self.t_us = t_us

    @property
    def pressed(self) -> bool:
        """True if any button is down after this event."""
        return self.mask != 0

    def __repr__(self) -> str:
        return f"InputEvent(mask=0b{self.mask:08b}, t_us={self.t_us})"


class MegClient:
    """
    Main class for serial communication with the Arduino microcontroller.

    Each method corresponds to a command sent to the Arduino, according to the protocol defined above.

    Example usage:
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
        Initializes the serial connection (without opening it yet).

        Arguments:
        - port : serial port path (e.g. '/dev/ttyACM0' on Linux, 'COM3' on Windows)
        - baud : baudrate (communication speed)
        - timeout : maximum time to wait for a response (in seconds)
        """
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser: serial.Serial | None = None

        # Mapping between mask bits and physical FORP buttons
        self.forp_map: Dict[int, str] = {
        0: "left blue button pressed",    # STI007 (out) pin 22
        1: "left yellow button pressed",  # STI008 (out) pin 23
        2: "left green button pressed",   # STI009 (out) pin 24
        3: "left red button pressed",     # STI010 (out) pin 25
        4: "right blue button pressed",   # STI012 (out) pin 26
        5: "right yellow button pressed", # STI013 (out) pin 27
        6: "right green button pressed",  # STI014 (out) pin 28
        7: "right red button pressed",    # STI015 (out) pin 29
        }

    # --------------------------------------------------------------------------
    # 🔌 Serial port management
    # --------------------------------------------------------------------------

    def open(self):
        """Opens the serial connection if it is not already open."""
        if self.ser and self.ser.is_open:
            return
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        # Opening the port triggers a DTR reset on the Arduino; wait for it to boot.
        time.sleep(2)

    def close(self):
        """Properly closes the serial connection."""
        if self.ser:
            try:
                self.ser.close()
            finally:
                self.ser = None

    def __enter__(self):
        """Allows usage with a context manager: 'with MegClient(...) as dev:'"""
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        """Automatically closes the connection at the end of the with block."""
        self.close()

    def _ensure(self):
        """Checks that a serial connection is open before sending data."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not open — call dev.open() before sending commands.")

    def _tx(self, data: bytes):
        """Sends a byte packet over the serial port."""
        self._ensure()
        self.ser.write(data)
        self.ser.flush()  # flush buffer to ensure immediate sending

    def _rx_exact(self, n: int) -> bytes:
        """Reads exactly n bytes from the serial port, raises TimeoutError otherwise."""
        self._ensure()
        buf = self.ser.read(n)
        if len(buf) != n:
            raise TimeoutError(f"Incomplete read: expected {n} bytes, received {len(buf)}")
        return buf

    # --------------------------------------------------------------------------
    # API — High-level commands sent to the Arduino
    # --------------------------------------------------------------------------

    def set_trigger_duration(self, duration_ms: int) -> None:
        """
        Sets the TTL signal duration (in ms) for each trigger.

        Argument:
        - duration_ms : integer between 0 and 65535 (e.g. 5 = 5 ms)

        Example:
        >>> dev.set_trigger_duration(5)
        """
        if duration_ms < 0 or duration_ms > 65535:
            raise ValueError("duration_ms must be between 0 and 65535")
        payload = struct.pack("<BH", OP_SET_TRIGGER_DURATION, duration_ms)
        self._tx(payload)

    def send_trigger_mask(self, mask: int) -> None:
        """
        Generates a trigger on all lines whose corresponding mask bit is 1.

        Argument:
        - mask : integer between 0 and 255 (e.g. 0b00001111 activates the first 4 lines)
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask must be between 0 and 255")
        self._tx(bytes([OP_SEND_TRIGGER_MASK, mask]))

    def send_trigger_on_line(self, line: int) -> None:
        """
        Generates a trigger on a single line (line number 0–7).

        Example:
        >>> dev.send_trigger_on_line(3)  # activates line 3 for the set duration
        """
        if not (0 <= line <= 7):
            raise ValueError("line must be between 0 and 7")
        self._tx(bytes([OP_SEND_TRIGGER_ON_LINE, line]))

    def set_high_mask(self, mask: int) -> None:
        """
        Sets HIGH all lines whose bits are 1 in the given mask.
        (Persistent state, not a trigger.)

        Example:
        >>> dev.set_high_mask(0b00000011)  # sets lines 0 and 1 to HIGH
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask must be between 0 and 255")
        self._tx(bytes([OP_SET_HIGH_MASK, mask]))

    def set_low_mask(self, mask: int) -> None:
        """
        Sets LOW all lines whose bits are 1 in the given mask.

        Example:
        >>> dev.set_low_mask(0b00001111)  # forces the first 4 lines to LOW
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask must be between 0 and 255")
        self._tx(bytes([OP_SET_LOW_MASK, mask]))

    def set_high_on_line(self, line: int) -> None:
        """Sets a single line (0–7) to HIGH persistently."""
        if not (0 <= line <= 7):
            raise ValueError("line must be between 0 and 7")
        self._tx(bytes([OP_SET_HIGH_ON_LINE, line]))

    def set_low_on_line(self, line: int) -> None:
        """Sets a single line (0–7) to LOW persistently."""
        if not (0 <= line <= 7):
            raise ValueError("line must be between 0 and 7")
        self._tx(bytes([OP_SET_LOW_ON_LINE, line]))

    def get_response_button_mask(self) -> int:
        """
        Reads the state of the response box buttons.

        Returns:
        - integer (mask 0–255) whose bits set to 1 correspond to pressed buttons
        - example: 0b00000100 means button 2 is pressed

        Example:
        >>> mask = dev.get_response_button_mask()
        >>> print(bin(mask))
        """
        self._tx(bytes([OP_GET_RESPONSE_BUTTON]))
        resp = self._rx_exact(1)
        return resp[0]

    # --------------------------------------------------------------------------
    # Firmware identification and capability detection
    # --------------------------------------------------------------------------

    def get_info(self) -> FirmwareInfo:
        """
        Asks the firmware to identify itself (opcode 1).

        Firmware older than protocol version 1 does not implement this opcode
        and answers nothing at all, so "legacy" is inferred from a read timeout.
        Feature-detect before using any opcode above 20: old firmware ignores
        unknown opcodes *silently*, so the failure mode is a command that does
        nothing rather than an error you can catch.

        Returns:
        - FirmwareInfo

        Example:
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
                f"unexpected reply to get_info: {resp!r} (is this really a MEG TTL box?)")
        return FirmwareInfo(version=resp[3], capabilities=resp[4])

    def set_port_mask(self, mask: int) -> None:
        """
        Assigns all 8 output lines at once (opcode 17). Requires CAP_ATOMIC_PORT.

        Unlike set_high_mask()/set_low_mask(), which only set or only clear and
        so need two commands to express a full byte, this writes the whole port
        in a single instruction. No intermediate value ever reaches the pins, so
        a recording device cannot latch a half-written trigger code.

        Argument:
        - mask : integer 0-255; bit N drives line N HIGH, a zero bit drives LOW
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask must be between 0 and 255")
        self._tx(bytes([OP_SET_PORT_MASK, mask]))

    # --------------------------------------------------------------------------
    # Timestamped input events (requires CAP_TIMESTAMPS)
    # --------------------------------------------------------------------------

    def get_micros(self) -> int:
        """Reads the Arduino's micros() counter (opcode 22).

        Useful for aligning firmware timestamps with the host clock: bracket
        this call between two host readings and take the midpoint.
        """
        self._tx(bytes([OP_GET_MICROS]))
        return struct.unpack("<I", self._rx_exact(4))[0]

    def clear_events(self) -> None:
        """
        Discards queued events and re-seeds the firmware's change detector
        (opcode 23), so a button already held down is not reported as a fresh
        press. Call this between trials.
        """
        self._tx(bytes([OP_CLEAR_EVENTS]))

    def set_debounce(self, microseconds: int) -> None:
        """
        Ignores transitions occurring within `microseconds` of the previous one
        (opcode 24). Pass 0 to disable, which is the default.

        Leave it off for fibre-optic response pads, which do not bounce:
        suppressing real transitions is worse than reporting extra ones. Use it
        for mechanical buttons, whose chatter can otherwise overflow the
        32-event queue.
        """
        if not (0 <= microseconds <= 65535):
            raise ValueError("debounce must be between 0 and 65535 microseconds")
        self._tx(bytes([OP_SET_DEBOUNCE]) + struct.pack("<H", microseconds))

    def get_event(self) -> tuple:
        """
        Fetches the oldest queued input event (opcode 21).

        The reply is a fixed 6 bytes even when the queue is empty, so the host
        never has to guess how much is coming.

        Returns:
        - (event, dropped) where `event` is an InputEvent or None if the queue
          was empty, and `dropped` is True if the firmware's queue overflowed
          since the last call.

        A True `dropped` means presses were *lost*, not merely delayed, so the
        trial should be treated as suspect rather than silently trusted.
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
        Blocks until a button goes down, and returns the event carrying the
        firmware's timestamp of the press.

        This is the accurate counterpart to polling get_response_button_mask()
        in a loop: your polling only affects how soon you *learn* of the press,
        not the recorded instant. Subtract your stimulus-onset timestamp from
        the event's t_us to get a reaction time.

        Arguments:
        - timeout : seconds to wait, or None to wait indefinitely

        Returns:
        - InputEvent, or None if the timeout expired

        Release events are skipped. Call clear_events() first to discard
        presses left over from a previous trial.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            ev, _ = self.get_event()
            if ev is not None:
                if ev.pressed:
                    return ev
                continue  # a release; keep draining
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.002)

    @staticmethod
    def elapsed_us(start_us: int, end_us: int) -> int:
        """
        Microseconds from `start_us` to `end_us`, correcting for the ~71.6 minute
        micros() wrap. Valid for intervals shorter than about 35.8 minutes.
        """
        return (end_us - start_us) & 0xFFFFFFFF

    def decode_forp(self, mask: int) -> List[str]:
        """
        Translates the mask returned by `get_response_button_mask()` into human-readable text.

        Argument:
        - mask : integer between 0 and 255

        Returns:
        - list of strings describing which buttons are pressed

        Example:
        >>> mask = dev.get_response_button_mask()
        >>> dev.decode_forp(mask)
        ['right red button pressed', 'left blue button pressed']
        """
        if not (0 <= mask <= 255):
            raise ValueError("mask must be between 0 and 255")
        msgs: List[str] = []
        for bit in range(8):
            if (mask >> bit) & 1:
                label = self.forp_map.get(bit, f"line {bit} activated")
                msgs.append(label)
        return msgs
