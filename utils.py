import numpy as np
from numpy.linalg import norm


def color_dist(c1, c2, ord=1):
    return norm(np.array(c1) - np.array(c2), ord=ord, axis=-1)

