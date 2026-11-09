"""Short UI hysteresis requires current minimap evidence, never just elapsed time."""
import math


class GameplayGate:
    def __init__(self):self.reset()
    def reset(self):self.confirmed=-math.inf
    def accept(self,stamp,*,map_open,hud,pointer):
        if map_open or not pointer:
            self.reset();return False
        if hud:self.confirmed=stamp;return True
        return 0<=stamp-self.confirmed<=.35
