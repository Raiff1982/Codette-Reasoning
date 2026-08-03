"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""

import numpy as np

def bio_em_field(mu, phi, gamma, A):
    return mu * phi * gamma * A

def roson_resonance(f, Q, C, E_bio, delta):
    return np.sum(f * Q * C * (1 + delta * E_bio)) / len(f)