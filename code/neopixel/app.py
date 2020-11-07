import board
import neopixel

# Define the NeoPixel strip setting the pin the control wire is connected to, the brightness
# and if the colors are written as soon as the values are updated, or if they need to be 
# updated all at once as soon as the values are set
pixels = neopixel.NeoPixel(board.D18, 150, brightness=0.2, auto_write=False)

# Pixel values are made of 3 components - red, green and blue.
# These values are from 0 (off) to 255 (full on). Colors can be made using different
# combinations of values. For example, 255, 0, 0 is red, 255, 0, 255 is purple.
# Set all the pixels to blue
pixels.fill((0, 0, 255))

# Show the color on all the pixels
pixels.show()