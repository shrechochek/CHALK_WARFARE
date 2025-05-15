#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from random import randint

def generate(img, amount):

    # Let's have repeatable, deterministic randomness
    # seed(37)/

    img_array = np.array(img)
    noise = np.random.randint(0, 2, img_array.shape, dtype=np.uint8)
    img = Image.fromarray(np.clip(img_array + noise, 0, 255))

    draw = ImageDraw.Draw(img)

    # Generate a basic random colour, random RGB values 10-245
    color = randint(0, 200)
    R, G, B = color, color ,color

    for _ in range(amount):
    # Choose RGB values for this circle, somewhat close (+/-10) to basic RGB
        n = randint(-30, 30)
        r = R + n
        g = G + n
        b = B + n
        diam = randint(20,70)
        x, y = randint(0,img.width), randint(0,img.height)
        draw.ellipse([x,y,x+diam,y+diam], fill=(r,g,b))

    # Blur the background a bit
    res = img.filter(ImageFilter.BoxBlur(3))
    # Save result

    # img.show()

    return res

# if __name__ == "__main__":
#     generate(Image.open("assets/Glock_17.png"), 100)