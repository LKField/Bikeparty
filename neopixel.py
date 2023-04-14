"""neopixel.py

neopixel.py is based on code by blaz-r but with modifications by Lucretia Field
MIT License
Copyright (c) 2021 blaz-r
A library for using ws2812b and sk6812 leds (aka neopixels) with Raspberry Pi Pico
"""
import array, time
from machine import Pin
import rp2

try:        # AttributeError under sphinx when machine package not available
    # PIO state machine for RGB. Pulls 24 bits (rgb -> 3 * 8bit) automatically
    @rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
    def ws2812():
        T1 = 2
        T2 = 5
        T3 = 3
        wrap_target()
        label("bitloop")
        out(x, 1)               .side(0)    [T3 - 1]
        jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
        jmp("bitloop")          .side(1)    [T2 - 1]
        label("do_zero")
        nop().side(0)                       [T2 - 1]
        wrap()
except AttributeError:
    def ws2812():
        pass

try:        # AttributeError under sphinx when machine package not available
    # PIO state machine for RGBW. Pulls 32 bits (rgbw -> 4 * 8bit) automatically
    @rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=32)
    def sk6812():
        T1 = 2
        T2 = 5
        T3 = 3
        wrap_target()
        label("bitloop")
        out(x, 1)               .side(0)    [T3 - 1]
        jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
        jmp("bitloop")          .side(1)    [T2 - 1]
        label("do_zero")
        nop()                   .side(0)    [T2 - 1]
        wrap()
except AttributeError:
    def sk6812():
        pass


# Delay here is the reset time. You need a pause to reset the LED strip back to the initial LED
# however, if you have quite a bit of processing to do before the next time you update the strip
# you could put in delay=0 (or a lower delay)
#
# Class supports different order of individual colors (GRB, RGB, WRGB, GWRB ...). In order to achieve
# this, we need to flip the indexes: in 'RGBW', 'R' is on index 0, but we need to shift it left by 3 * 8bits,
# so in it's inverse, 'WBGR', it has exactly right index. Since micropython doesn't have [::-1] and recursive rev()
# isn't too efficient we simply do that by XORing (operator ^) each index with 3 (0b11) to make this flip.
# When dealing with just 'RGB' (3 letter string), this means same but reduced by 1 after XOR!.
# Example: in 'GRBW' we want final form of 0bGGRRBBWW, meaning G with index 0 needs to be shifted 3 * 8bit ->
# 'G' on index 0: 0b00 ^ 0b11 -> 0b11 (3), just as we wanted.
# Same hold for every other index (and - 1 at the end for 3 letter strings).

class Neopixel:
    """Neopixel

    :param num_leds: Total number of LEDs in ring
    :param state_machine: PIO state machine instance neopixel
    :param pin: Neopixel pin number
    :param mode: Color mode as LED RGB order. Default RGB
    :param delay: Delay time. Default 0.0001
    """
    def __init__(self, num_leds, state_machine, pin, mode="RGB", delay=0.0001):
        self.pixels = array.array("I", [0 for _ in range(num_leds)])
        self.mode = set(mode)   # set for better performance
        if 'W' in self.mode:
            # RGBW uses different PIO state machine configuration
            self.sm = rp2.StateMachine(state_machine, sk6812, freq=8000000, sideset_base=Pin(pin))
            # dictionary of values required to shift bit into position (check class desc.)
            self.shift = {'R': (mode.index('R') ^ 3) * 8, 'G': (mode.index('G') ^ 3) * 8,
                          'B': (mode.index('B') ^ 3) * 8, 'W': (mode.index('W') ^ 3) * 8}
        else:
            self.sm = rp2.StateMachine(state_machine, ws2812, freq=8000000, sideset_base=Pin(pin))
            self.shift = {'R': ((mode.index('R') ^ 3) - 1) * 8, 'G': ((mode.index('G') ^ 3) - 1) * 8,
                          'B': ((mode.index('B') ^ 3) - 1) * 8, 'W': 0}
        self.sm.active(1)
        self.num_leds = num_leds
        self.delay = delay
        self.brightnessvalue = 255

    # Set the overall value to adjust brightness when updating leds
    def brightness(self, brightness=None):
        """brightness sets the brightness of Neopixels

        :param brightness: Strip brightness 1-255
        :return: None
        """
        if brightness == None:
            return self.brightnessvalue
        else:
            if brightness < 1:
                brightness = 1
        if brightness > 255:
            brightness = 255
        self.brightnessvalue = brightness

    # Create a gradient with two RGB colors between "pixel1" and "pixel2" (inclusive)
    # Function accepts two (r, g, b) / (r, g, b, w) tuples
    def set_pixel_line_gradient(self, pixel1, pixel2, left_rgb_w, right_rgb_w):
        """

        :param pixel1:
        :param pixel2:
        :param left_rgb_w:
        :param right_rgb_w:
        :return: None
        """
        if pixel2 - pixel1 == 0:
            return
        right_pixel = max(pixel1, pixel2)
        left_pixel = min(pixel1, pixel2)

        for i in range(right_pixel - left_pixel + 1):
            fraction = i / (right_pixel - left_pixel)
            red = round((right_rgb_w[0] - left_rgb_w[0]) * fraction + left_rgb_w[0])
            green = round((right_rgb_w[1] - left_rgb_w[1]) * fraction + left_rgb_w[1])
            blue = round((right_rgb_w[2] - left_rgb_w[2]) * fraction + left_rgb_w[2])
            # if it's (r, g, b, w)
            if len(left_rgb_w) == 4 and 'W' in self.mode:
                white = round((right_rgb_w[3] - left_rgb_w[3]) * fraction + left_rgb_w[3])
                self.set_pixel(left_pixel + i, (red, green, blue, white))
            else:
                self.set_pixel(left_pixel + i, (red, green, blue))
    
    # TODO Make more universal (Not just 2 or 4 divisions but universal to all cases
    def segment_gradient(self, color_list, pixel1=0, pixel2=15, reverse=True, rainbow=False):
        """Show gradients between colors

        :param pixel1: Index of first pixel in gradient. Default = 0
        :param pixel2: Index of second pixel in gradient. Default = 15
        :param color_list: List of colors (in rgb or rgbw tuples). Length must be 2 or 4
        :param reverse: Determines if gradient reverses direction. Default = True for 2 color gradients
        :param rainbow: Determines if this is a rainbow gradient. Defualt = False for 2 color gradients
        :return: None 
        """
        if pixel2 - pixel1 == 0:
            return
        divs = len(color_list)
        step = ((pixel2+1)//divs)
        start_pixel = pixel1
        end_pixel = step
        if divs == 4:
            rainbow=True
            reverse=False
        for i, color in enumerate(color_list):
            for j in range(end_pixel - start_pixel + 1):
                start_pixel = i * step
                first_rgb_w = color
                end_pixel = start_pixel + step
                if end_pixel >= pixel2:
                    end_pixel = pixel2
                    second_rgb_w = color_list[0]
                else:
                    second_rgb_w = color_list[i+1]
#                 print("Start Pixel", start_pixel, "End Pixel", end_pixel)
#                 print("Start Color", first_rgb_w, "End Color", second_rgb_w)
                fraction = j / (end_pixel - start_pixel)
                red = round((second_rgb_w[0] - first_rgb_w[0]) * fraction + first_rgb_w[0])
                green = round((second_rgb_w[1] - first_rgb_w[1]) * fraction + first_rgb_w[1])
                blue = round((second_rgb_w[2] - first_rgb_w[2]) * fraction + first_rgb_w[2])
                # if it's (r, g, b, w)
                if len(first_rgb_w) == 4 and 'W' in self.mode:
                    white = round((second_rgb_w[3] - first_rgb_w[3]) * fraction + first_rgb_w[3])
                    if not reverse: 
                        self.set_pixel(start_pixel + j, (red, green, blue, white))
                    else:
                        self.set_pixel(end_pixel - j, (red, green, blue, white))
                else:
                    if not reverse:
                        self.set_pixel(start_pixel + j, (red, green, blue))
                    else:
                        self.set_pixel(end_pixel - j, (red, green, blue))
                if rainbow:
#                     print("Rainbow")
                    if (end_pixel+j) > (pixel2+2):
                        break
                else:
#                     print("Gradient")
                    start_pixel = end_pixel
                    end_pixel = pixel2
                    reverse = True
#                     print("Start", start_pixel, "End", end_pixel)


    # Set an array of pixels starting from "pixel1" to "pixel2" (inclusive) to the desired color.
    # Function accepts (r, g, b) / (r, g, b, w) tuple
    def set_pixel_line(self, pixel1, pixel2, rgb_w):
        """

        :param pixel1:
        :param pixel2:
        :param rgb_w:
        :return: None
        """
        for i in range(pixel1, pixel2 + 1):
            self.set_pixel(i, rgb_w)

    # Set red, green and blue value of pixel on position <pixel_num>
    # Function accepts (r, g, b) / (r, g, b, w) tuple
    def set_pixel(self, pixel_num, rgb_w):
        """

        :param pixel_num:
        :param rgb_w:
        :return: None
        """
        pos = self.shift

        red = round(rgb_w[0] * (self.brightness() / 255))
        green = round(rgb_w[1] * (self.brightness() / 255))
        blue = round(rgb_w[2] * (self.brightness() / 255))
        white = 0
        # if it's (r, g, b, w)
        if len(rgb_w) == 4 and 'W' in self.mode:
            white = round(rgb_w[3] * (self.brightness() / 255))

        self.pixels[pixel_num] = white << pos['W'] | blue << pos['B'] | red << pos['R'] | green << pos['G']

    # Rotate <num_of_pixels> pixels to the left
    def rotate_left(self, num_of_pixels=1):
        """

        :param num_of_pixels:
        :return: None
        """
        if num_of_pixels == None:
            num_of_pixels = 1
        self.pixels = self.pixels[num_of_pixels:] + self.pixels[:num_of_pixels]

    # Rotate <num_of_pixels> pixels to the right
    def rotate_right(self, num_of_pixels):
        """

        :param num_of_pixels:
        :return: None
        """
        if num_of_pixels == None:
            num_of_pixels = 1
        num_of_pixels = -1 * num_of_pixels
        self.pixels = self.pixels[num_of_pixels:] + self.pixels[:num_of_pixels]

    # Update pixels
    def show(self):
        """

        :return: None
        """
        # If mode is RGB, we cut 8 bits of, otherwise we keep all 32
        cut = 8
        if 'W' in self.mode:
            cut = 0
        for i in range(self.num_leds):
            self.sm.put(self.pixels[i], cut)
        time.sleep(self.delay)

    # Set all pixels to given rgb values
    # Function accepts (r, g, b) / (r, g, b, w)
    def fill(self, rgb_w):
        """

        :param rgb_w:
        :return: None
        """
        for i in range(self.num_leds):
            self.set_pixel(i, rgb_w)
        time.sleep(self.delay)
        
if __name__ == "__main__":
    # Define neopixel parameters 
    numpix = 16
    neo_pin = 22
    strip = Neopixel(numpix, 0, neo_pin, "GRB")
    strip.brightness(50)
    
    # Define neopixel colors
    r1 = (255,0,0)
    o1 = (128,5,0)
    y1 = (255,173,0)
    y2 = (255,255,0)
    y3 = (255,239,0)
    g1 = (0,255,0)
    g2 = (0,204,0)
    g3 = (0,153,0)
    b1 = (0,255,64)
    b2 = (0,255,255)
    b3 = (0,128,255)
    b4 = (0,64,255)
    b5 = (0,0,255)
    pk1 = (153,0,255)
    pk2 = (255,0,127)
    pl1 = (255,102,204)
    pl2 = (128,0,128)
    
    left_rgb = g1
    right_rgb = pl2
    start_rgb_w = g1
    end_rgb_w = pl2
    
    Rlist_rgb_w = [r1, y2, g1, b5]
    Glist_rgb_w = [y1, r1]
#     Rlist_rgb_w = [r1, o1, y1, g1, b2, pl1, pk1, pk2]
    
    strip.fill((0,0,0))
    strip.show()
    time.sleep(0.5)
    
#     strip.segment_gradient(Glist_rgb_w, reverse=True, rainbow=False)
#     strip.show()
#     time.sleep(5)
    
    strip.segment_gradient(Rlist_rgb_w, reverse=False)
    strip.show()
#     time.sleep(1)
    
    for i in range(100):
        strip.rotate_right(1)
        strip.show()
        time.sleep(0.05)
    strip.fill((0,0,0))
    strip.show()


# -------------------------------------OLD CODE-------------------------
#                 
#         # Create a gradient with two RGB colors between "pixel1" and "pixel2" (inclusive)
#     # Function accepts two (r, g, b) / (r, g, b, w) tuples
#     def set_pixel_ring_gradient(self, pixel1, pixel2, first_rgb_w, second_rgb_w, segs=2, list_rgb_w=None):
#         if pixel2 - pixel1 == 0:
#             return
#         reverse = False
#         rainbow = False
#         right_pixel = max(pixel1, pixel2)
#         left_pixel = min(pixel1, pixel2)
#         if (pixel2 + 1) % segs != 0:
#             print("# pixels must be divisible by # segments")
#         elif segs != 2:
#             rainbow = True
#             idx = 0
#             first_rgb_w = list_rgb_w[idx]
#             second_rgb_w = list_rgb_w[idx + 1]
#         start_pixel = pixel1
#         end_pixel = ((pixel2 + 1) // segs) - 1
#         
#         for i in range(right_pixel - left_pixel + 1):
# #         while start_pixel <= pixel2:
#             print("Start Color", first_rgb_w, "End Color", second_rgb_w)
#             print("Start", start_pixel, "End", end_pixel)
#             for j in range(end_pixel - start_pixel + 1):
#                 fraction = j / (end_pixel - start_pixel)
#                 red = round((second_rgb_w[0] - first_rgb_w[0]) * fraction + first_rgb_w[0])
#                 green = round((second_rgb_w[1] - first_rgb_w[1]) * fraction + first_rgb_w[1])
#                 blue = round((second_rgb_w[2] - first_rgb_w[2]) * fraction + first_rgb_w[2])
#                 # if it's (r, g, b, w)
#                 if len(first_rgb_w) == 4 and 'W' in self.mode:
#                     white = round((second_rgb_w[3] - first_rgb_w[3]) * fraction + first_rgb_w[3])
#                     if not reverse: 
#                         self.set_pixel(start_pixel + j, (red, green, blue, white))
#                     else:
#                         self.set_pixel(end_pixel - j, (red, green, blue, white))
#                 else:
#                     if not reverse:
#                         self.set_pixel(start_pixel + j, (red, green, blue))
#                     else: self.set_pixel(end_pixel - j, (red, green, blue))
#                     
#             if not rainbow:
#                 start_pixel = end_pixel
#                 end_pixel = pixel2
#                 reverse = True
#                 print("Start", start_pixel, "End", end_pixel)
#                 if start_pixel == end_pixel:
#                     break
#             else:
#                 idx += 1
#                 start_pixel = (idx + 1) * segs
#                 end_pixel = start_pixel + (segs - 1)
#                 first_rgb_w = list_rgb_w[idx]
#                 if idx == (len(list_rgb_w)-1):
#                     second_rgb_w = list_rgb_w[0]
#                     end_pixel = pixel2
#                 else:
#                     second_rgb_w = list_rgb_w[idx + 1]
#                     
