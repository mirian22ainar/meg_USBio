from time import sleep, time
from meg_client import MegClient

PORT = "/dev/ttyACM0"   # adapte selon ta machine

with MegClient(PORT) as arduino:
    sleep(1)

    print("Appuie sur un des boutons maintenant (appuie sur un/des boutons ou relie D22..D29 à GND)")
   
    for trial in range(10):
        sleep(0.500)  
        while arduino.get_response_button_mask() != 0:
            pass
        sleep(.5)
        print("X...")
        m = arduino.get_response_button_mask() 
        start = time()
        while m == 0:
            m = arduino.get_response_button_mask()
        rt = time() - start
        print(f'RT = {rt}s, mask={m}')


    
       