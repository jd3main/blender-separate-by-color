import bpy
import numpy as np
from enum import IntEnum


class Inter(IntEnum):
    NEAREST = 0
    LINEAR = 1


class Border(IntEnum):
    # CONSTANT = 0
    REPLICATE = 1


def sample_uv(image: np.ndarray, uv, inter=Inter.NEAREST, border=Border.REPLICATE):
    h, w = image.shape[0:2]
    u, v = uv
    x = u*(w+1) - 0.5
    y = v*(h+1) - 0.5
    if inter == Inter.NEAREST:
        return sample_nearest(image, x, y, border)
    elif inter == Inter.LINEAR:
        return sample_linear(image, x, y, border)
    return image[x, y]


def sample_nearest(image: np.ndarray, x, y, border=Border.REPLICATE):
    h, w = image.shape[0:2]

    if border == Border.REPLICATE:
        x, y = clip_xy(x, y, w, h)
        x, y = round_int_xy(x, y)
        return image[y, x]
    else:
        raise ValueError('Only border type REPLICATE has been implemented')


def sample_linear(image, x, y, inter=Inter.NEAREST, border=Border.REPLICATE):
    # TODO
    raise ValueError('Linear interpolation is not implemented')


def clip_xy(x, y, w, h):
    return np.clip(x, 0, w-1), np.clip(y, 0, h-1)


def round_xy(x, y):
    return np.round(x), np.round(y)


def round_int_xy(x, y):
    return np.round(x).astype(int), np.round(y).astype(int)
