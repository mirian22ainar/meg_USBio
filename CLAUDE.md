# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arduino-based replacement for legacy parallel ports in MEG (magnetoencephalography) experiments. Provides an Arduino firmware and a Python client API to send TTL triggers and read response button states over USB serial.

## Setup

**Arduino firmware:** Flash `arduino/meg_protocol.ino` via the Arduino IDE to an Arduino Mega/Mega 2560.

**Python dependencies (no requirements.txt — install manually):**
```bash
pip install pyserial expyriment
```

**Run a Python script:**
```bash
python3 python/<script_name>.py
```

**Run Jupyter notebooks:**
```bash
jupyter notebook
```

## Architecture

### Serial Protocol (Arduino ↔ Python)

Communication runs at 115200 baud (8N1). The Arduino firmware (`arduino/meg_protocol.ino`) implements an opcode-based binary protocol:

- **Output pins 30–37**: 8 TTL trigger lines
- **Input pins 22–29**: 8 response button lines (FORP box)

The Python client (`python/meg_client_eng.py` / `python/meg_client.py`) wraps this protocol. Every method sends a binary command frame and optionally reads back a response. Key methods:

| Method | Description |
|---|---|
| `send_trigger_mask(mask)` | Pulse multiple trigger lines simultaneously |
| `send_trigger_on_line(line)` | Pulse a single trigger line (0–7) |
| `set_trigger_duration(ms)` | Set TTL pulse width in ms |
| `set_high_mask(mask)` / `set_low_mask(mask)` | Persistent HIGH/LOW states |
| `get_response_button_mask()` | Read all button states as bitmask |
| `decode_forp(mask)` | Decode bitmask to human-readable button names |

### File Layout

- `arduino/` — Firmware (`meg_protocol.ino` is production; `recep_exec*.ino` are test variants)
- `python/meg_client_eng.py` — Main API (English); `meg_client.py` is the French mirror
- `python/test_meg_client_eng.py` — API integration test (requires connected Arduino)
- `python/simple-detection-visual-expyriment.py` — Example full experiment using Expyriment
- `notebooks/` — Latency and timing analysis (post-experiment)
- `docs/` — Schematics and FORP button-to-pin mapping notebooks

### Bilingual codebase

Source files exist in both French (`meg_client.py`) and English (`meg_client_eng.py`) versions. Keep both in sync when modifying the API.
