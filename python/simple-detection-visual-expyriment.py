#! /usr/bin/env python
# Time-stamp: <2021-11-16 15:36:47 christophe@pallier.org>
""" This is a simple reaction-time experiment.

At each trial, a cross is presented at the center of the screen and
the participant must press a key as quickly as possible.
"""
from meg_client import MegClient
from time import time
import random
from expyriment import design, control, stimuli

N_TRIALS = 20
MIN_WAIT_TIME = 1000
MAX_WAIT_TIME = 2000
MAX_RESPONSE_DELAY = 2000


PORT = "/dev/ttyACM0"
resp_box = MegClient(PORT) 
resp_box.open()

def get_resp_rt(max_duration):
    while resp_box.get_response_button_mask() !=0: 
        pass
    start = time()
    m = resp_box.get_response_button_mask()
    while (m == 0) & (time() - start < (max_duration/1000)):
        m = resp_box.get_response_button_mask()
    if m != 0:
        rt = time() - start
    else:
        rt = None
    return m, rt 

exp = design.Experiment(name="Visual Detection", text_size=40)
#control.set_develop_mode(on=True)
control.initialize(exp)

target = stimuli.FixCross(size=(50, 50), line_width=4)
blankscreen = stimuli.BlankScreen()

instructions = stimuli.TextScreen("Instructions",
    f"""From time to time, a cross will appear at the center of screen.

    Your task is to press the response button as quickly as possible when you see it (We measure your reaction-time).

    There will be {N_TRIALS} trials in total.

    Press the spacebar to start.""")

exp.add_data_variable_names(['trial', 'wait', 'respkey', 'RT'])

control.start(skip_ready_screen=True)
instructions.present()
exp.keyboard.wait()

for i_trial in range(N_TRIALS):
    blankscreen.present()
    waiting_time = random.randint(MIN_WAIT_TIME, MAX_WAIT_TIME)
    exp.clock.wait(waiting_time)
    target.present()
    key_mask, rt = get_resp_rt(MAX_RESPONSE_DELAY)
    exp.data.add([i_trial, waiting_time, key_mask, rt])


resp_box.close()
control.end()
