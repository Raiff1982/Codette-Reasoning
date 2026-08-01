"""
render_meta_results — 3D meta-result rendering.

A different implementation from experiments/codette_meta_3d.py: that one is a
script, this exposes a callable. Neither supersedes the other.
"""


# Codette Meta-Analysis 3D Visualizer

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

def render_meta_results(data_matrix):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    X, Y = np.meshgrid(range(data_matrix.shape[0]), range(data_matrix.shape[1]))
    ax.plot_surface(X, Y, data_matrix, cmap='viridis')
    plt.title("Codette Meta Perspective Surface")
    plt.savefig("Codette_Meta_3D.png")
