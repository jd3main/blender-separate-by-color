import bpy
import numpy as np


def get_pixel(image, x, y):
    w, h = image.size
    ch = image.channels
    x = np.clip(x, 0, w-1)
    y = np.clip(y, 0, h-1)
    index = (y*w + x)*ch
    color = image.pixels[index:index+ch]
    return color


def sample_uv(image: bpy.types.Image, uv):
    w, h = image.size
    u, v = uv
    x = round(u*w-0.5)
    y = round(v*h-0.5)
    return get_pixel(image, x, y)
