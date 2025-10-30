import serial

PORT = '/dev/ttyACM0'   # adapter selon ton OS (COM3 sur Windows)
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    print("Listening to Arduino...")
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            print(line)
