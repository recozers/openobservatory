"""Derived meteorological quantities.

All temperatures in °C unless the name says K; pressure in hPa.
"""
from __future__ import annotations

import numpy as np


def wind_speed(u, v):
    return np.hypot(u, v)


def rh_from_t_td(t_c, td_c):
    """Relative humidity (%) from air and dew-point temperature (Magnus)."""
    a, b = 17.625, 243.04
    rh = 100.0 * np.exp(a * td_c / (b + td_c)) / np.exp(a * t_c / (b + t_c))
    return np.clip(rh, 0.5, 100.0)


def vapour_pressure_hpa(td_c):
    return 6.112 * np.exp(17.67 * td_c / (td_c + 243.5))


def specific_humidity(td_c, p_hpa):
    e = vapour_pressure_hpa(td_c)
    return 0.622 * e / (p_hpa - 0.378 * e)


def wet_bulb_stull(t_c, rh_pct):
    """Wet-bulb temperature (°C), Stull (2011) empirical fit.  Valid roughly
    for -20..50 °C and RH 5..99 %; error ~±1 K, adequate for a covariate."""
    rh = np.asarray(rh_pct, dtype=float)
    t = np.asarray(t_c, dtype=float)
    tw = (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh)
        - 4.686035
    )
    return tw


def pressure_from_elevation(elev_m):
    """ISA standard atmosphere pressure (hPa) at elevation; adequate for the
    weak pressure dependence of specific humidity."""
    return 1013.25 * (1.0 - 2.25577e-5 * np.asarray(elev_m, dtype=float)) ** 5.25588


def derive(t2m_k, d2m_k, u10, v10, elev_m=0.0, sp_pa=None):
    """Return a dict of derived covariates from ERA5-style inputs."""
    t = np.asarray(t2m_k, dtype=float) - 273.15
    td = np.asarray(d2m_k, dtype=float) - 273.15
    p = (np.asarray(sp_pa, dtype=float) / 100.0) if sp_pa is not None else pressure_from_elevation(elev_m)
    rh = rh_from_t_td(t, td)
    return {
        "ta_c": t,
        "td_c": td,
        "rh_pct": rh,
        "wind_ms": wind_speed(np.asarray(u10, float), np.asarray(v10, float)),
        "q_kgkg": specific_humidity(td, p),
        "tw_c": wet_bulb_stull(t, rh),
    }
