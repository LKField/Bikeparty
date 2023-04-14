# Example from neopixel.py folder with modifications
import time
from neopixel import Neopixel

numpix = 53 * 4 # Number of LEDs in strip x4 
pin = 28
strip = Neopixel(numpix, 0, pin, "GRB")
strip.brightness(100)

red = (255,0,0)
orange1 = (255,255,0)
orange2 = (128,255,0)
yellow = (64,255,0)
green1 = (0,153,0)
green2 = (0,204,0)
green3 = (0,255,0)
blue1 = (0,255,64)
blue2 = (0,255,255)
blue3 = (0,128,255)
blue4 = (0,64,255)
blue5 = (0,0,255)
pink1 = (153,0,255)
pink2 = (255,0,255)
pink3 = (255,0,128)
pink4 = (255,0,64)

colors = (red, orange1, orange2, yellow, green1, green2, blue1, blue2, blue3, pink1, pink2, pink3, pink4)

def rainbow_static():
    for multiplier in range(numpix//len(colors)):
        print(multiplier)
        for i, color in enumerate(colors):
            strip.set_pixel(i, color)
            time.sleep(0.3)
            strip.show()

def rainbow_run(count):
    n = 1
    while n <= count:
        for color in colors:
            for i in range(numpix):
                strip.set_pixel(i, color)
                time.sleep(0.3)
                strip.show()
     #   print("Loop number: ", n)
        n += 1
        
    strip.fill((0,0,0))
    strip.show()
        
def rainbow_off():
    strip.fill((0,0,0))
    strip.show()
#    time.sleep(0.5)

def segment(start, end):
    for color in colors:
        time.sleep(0.5)
        for i in range(start, end):
            strip.set_pixel(i, color)
            time.sleep(0.03)
            strip.show()

while True:
    for color in colors:
        time.sleep(0.5)
        for i in range(numpix):
            strip.set_pixel(i, color)
            time.sleep(0.03)
            strip.show()
        



