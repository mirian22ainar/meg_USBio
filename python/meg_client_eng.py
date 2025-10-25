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

import serial
import struct
from typing import List, Dict

# --- Default constants ---
DEFAULT_BAUD = 115200      # serial communication speed (must match Arduino)
DEFAULT_TIMEOUT = 0.2      # max waiting time (s) before read timeout

# --- OpCodes corresponding to Arduino commands ---
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
