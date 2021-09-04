import bpy
import numpy as np
from numpy.linalg import norm


def color_dist(c1, c2, ord=1):
    return norm(np.array(c1) - np.array(c2), ord=ord, axis=-1)


def get_ndarray(image: bpy.types.Image) -> np.ndarray:
    '''
    Return a new numpy array containing the pixels of the given image.
    '''
    w, h = image.size
    c = image.channels
    arr = np.array(image.pixels).reshape((w, h, c))
    return arr


def get_pixel(image, x, y):
    w, h = image.size
    ch = image.channels
    x = np.clip(x, 0, w-1)
    y = np.clip(y, 0, h-1)
    index = (y*w + x)*ch
    color = image.pixels[index:index+ch]
    return color
