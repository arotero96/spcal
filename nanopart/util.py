import numpy as np
import scipy.ndimage as ndi

from typing import Tuple


def accumulate_detections_scipy(
    y: np.ndarray,
    limit_detection: float,
    limit_accumulation: float,
    # return_regions: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """Returns an array of accumulated detections.

    Contiguous regions above `limit_accumulation` that contain at least one value above
    `limit_detection` are summed.

    Args:
        y: array
        limit_detection: value for detection of region
        limit_accumulation: minimum accumulation value

    Returns:
        summed detection regions
        labels of regions
    """
    # Label regions above the Lc
    labels, n = ndi.label(y > limit_accumulation)
    # Idx of labels without background
    idx = np.arange(1, n)
    if idx.size == 0:
        return np.array([]), np.array([])
    # Remove indices without a value above the Ld
    idx = idx[ndi.maximum(y, labels=labels, index=idx) > limit_detection]
    # Compute the sum (minus the mean of background) of remaining regions
    sums = ndi.sum(y, labels=labels, index=idx)
    # Remove labels of undetected regions
    labels[~np.isin(labels, idx)] = 0

    return sums, labels


def accumulate_detections(
    y: np.ndarray,
    limit_detection: float,
    limit_accumulation: float,
    # return_regions: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """Returns an array of accumulated detections.

    Contiguous regions above `limit_accumulation` that contain at least one value above
    `limit_detection` are summed.

    Args:
        y: array
        limit_detection: value for detection of region
        limit_accumulation: minimum accumulation value

    Returns:
        summed detection regions
        labels of regions
    """
    # Label regions above the Lc
    diff = np.diff((y > limit_accumulation).astype(np.int8), prepend=0)
    n = np.count_nonzero(diff == 1)
    ix = np.arange(1, n + 1)
    diff[diff == 1] = ix
    m = np.count_nonzero(diff == -1)
    nx = np.arange(1, m + 1)
    diff[diff == -1] = -nx
    labels = np.cumsum(diff)

    regions = labels == ix[:, None]
    # labels, n = ndi.label(y > limit_accumulation)
    maximums = np.maximum()
    # Idx of labels without background
    # idx = np.arange(1, n)
    # if idx.size == 0:
    #     return np.array([]), np.array([])
    # Remove indices without a value above the Ld
    # idx = idx[ndi.maximum(y, labels=labels, index=idx) > limit_detection]
    # Compute the sum (minus the mean of background) of remaining regions
    sums = ndi.sum(y, labels=labels, index=idx)
    # Remove labels of undetected regions
    labels[~np.isin(labels, idx)] = 0

    return sums, labels

import time

x = np.random.random(10000)
start = time.time()
r, l = accumulate_detections_scipy(x, 0.5, 0.25)
print(time.time() - start)
start = time.time()
r2, l2 = accumulate_detections(x, 0.5, 0.25)
print(time.time() - start)
print(np.all(r == r2))

def poisson_limits(ub: float, epsilon: float = 0.5) -> Tuple[float, float]:
    """Calulate Yc and Yd for mean `ub`.

    If `ub` if lower than 5.0, the correction factor `epsilon` is added to `ub`.
    Lc and Ld can be calculated by adding `ub` to `Yc` and `Yd`.

    Args:
        ub: mean of background
        epsilon: low `ub` correct factor

    Returns:
        Yc, gross count critical value
        Yd, gross count detection limit

    References:
        Currie, L. A. (1968). Limits for qualitative detection and quantitative
            determination. Application to radiochemistry.
            Analytical Chemistry, 40(3), 586–593.
            doi:10.1021/ac60259a007
        Currie, L.A. On the detection of rare, and moderately rare, nuclear events.
            J Radioanal Nucl Chem 276, 285–297 (2008).
            https://doi.org/10.1007/s10967-008-0501-5
    """
    if ub < 5.0:  # 5 counts limit to maintain 0.05 alpha / beta (Currie 2008)
        ub += epsilon
    # Yc and Yd for paired distribution (Currie 1969)
    return 2.33 * np.sqrt(ub), 2.71 + 4.65 * np.sqrt(ub)


# Particle functions


def nebulisation_efficiency(
    count: int, concentration: float, mass: float, flow: float, time: float
) -> float:
    """The nebulistaion efficiency.

    Args:
        count: number of detected particles
        concentration: of reference material (kg/L)
        mass: of reference material (kg)
        flow: sample inlet flow (L/s)
        time: total aquisition time (s)
    """

    return count / (concentration / mass * flow * time)


def particle_mass(
    signal: np.ndarray,
    dwell: float,
    efficiency: float,
    flowrate: float,
    response_factor: float,
    mass_fraction: float = 1.0,
) -> np.ndarray:
    """Array of particle masses given their integrated responses (kg).

    Args:
        signal: array of particle signals
        dwell: dwell time (s)
        efficiency: nebulisation efficiency
        flowrate: sample inlet flowrate (L/s)
        response_factor: counts / concentration (kg/L)
        mass_fraction: molar mass particle / molar mass analyte
    """
    return signal * (dwell * flowrate * efficiency * mass_fraction / response_factor)


def particle_number_atoms(
    masses: np.ndarray,
    molarmass: float,
) -> float:
    """Concentration of particles per L.

    Args:
        masses: array of particle signals (kg)
        molarmass: molecular weight (kg/mol)
    """
    Na = 6.02214076e23
    return masses * Na / molarmass


def particle_number_concentration(
    count: int, efficiency: float, flowrate: float, time: float
) -> float:
    """Concentration of particles per L.

    Args:
        count: number of detected particles
        efficiency: nebulisation efficiency
        flowrate: sample inlet flowrate (L/s)
        time: total aquisition time (s)
    """
    return count / (efficiency * flowrate * time)


def particle_size(masses: np.ndarray, density: float) -> np.ndarray:
    """Array of particle sizes in m.

    Args:
        masses: array of particle signals (kg)
        density: reference density (kg/m3)
    """
    return np.cbrt(6.0 / (np.pi * density) * masses)


def particle_total_concentration(
    masses: np.ndarray, efficiency: float, flowrate: float, time: float
) -> float:
    """Concentration of material in kg/L.

    Args:
        masses: array of particle signals (kg)
        efficiency: nebulisation efficiency
        flowrate: sample inlet flowrate (L/s)
        time: total aquisition time (s)
    """

    return np.sum(masses) / (efficiency * flowrate * time)


def reference_particle_mass(density: float, diameter: float) -> float:
    """Calculates particle mass in kg.

    Args:
        density: reference density (kg/m3)
        diameter: reference diameter (m)
    """
    return 4.0 / 3.0 * np.pi * diameter ** 3 * density


def reference_particle_size(mass_std: float, density_std: float) -> float:
    """Calculates particle diameter in m.

    Args:
        mass: particle mass (kg)
        density: reference density (kg/m3)
    """
    return np.cbrt(6.0 / np.pi * mass_std / density_std)
