import numpy as np

def zeta_modulation(frequencies, power_spectrum, coherence_filter):
    zeta_energy = 0.0
    for f, power in zip(frequencies, power_spectrum):
        if f >= 100:
            zeta_energy += power * coherence_filter(f)
    return zeta_energy

def coherence_filter(f):
    # Example filter: normalize and taper beyond 500 Hz
    if f > 500:
        return 0.1
    return 1.0