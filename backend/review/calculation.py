"""Piecewise-linear integration of a prepared, nonnegative trace."""
from dataclasses import asdict, dataclass
import math
import numpy as np
from .exceptions import DomainError

ALGORITHM_VERSION = "linear-trapezoid-v1"


@dataclass(frozen=True)
class AnalysisResult:
    start_time: float
    end_time: float
    total_start_time: float
    total_end_time: float
    total_area: float
    selected_area: float
    area_fraction_percent: float
    point_count: int
    algorithm_version: str = ALGORITHM_VERSION
    time_unit: str = "min"
    signal_unit: str = "AU"
    area_unit: str = "AU·min"
    fraction_unit: str = "%"

    def to_dict(self):
        return asdict(self)


def analyze_trace(points, start_time, end_time):
    try:
        data = np.asarray(points, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DomainError("Points must contain finite time and signal pairs.") from exc
    if data.ndim != 2 or data.shape[1] != 2 or not 2 <= len(data) <= 2000:
        raise DomainError("A trace needs 2–2,000 time and signal pairs.")
    if not np.isfinite(data).all() or (data[:, 1] < 0).any():
        raise DomainError("Signals must be finite and nonnegative; times must be finite.")
    if (data[1:, 0] <= data[:-1, 0]).any():
        raise DomainError("Time values must be strictly increasing.")
    for name, value in (("start_time", start_time), ("end_time", end_time)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)) or not math.isfinite(value):
            raise DomainError("Enter finite boundaries.", fields={name: ["Enter a finite number."]})
    a, b = float(start_time), float(end_time)
    lo, hi = float(data[0, 0]), float(data[-1, 0])
    if a < lo or a > hi:
        raise DomainError("Start is outside the trace.", fields={"start_time": [f"Use a value from {lo:g} to {hi:g}."]})
    if b < lo or b > hi:
        raise DomainError("End is outside the trace.", fields={"end_time": [f"Use a value from {lo:g} to {hi:g}."]})
    if a >= b:
        raise DomainError("End must be greater than start.", fields={"end_time": ["Must be greater than start time."]})
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            x, y = data[:, 0], data[:, 1]
            if not np.isfinite(np.diff(x)).all():
                raise FloatingPointError()
            total = float(np.trapezoid(y, x=x))
            if not math.isfinite(total):
                raise FloatingPointError()
            if total <= 0:
                raise DomainError("The entire trace must have a positive area.", "zero_total_area")
            if a == lo and b == hi:
                selected = total
            else:
                interior = (x > a) & (x < b)
                sx = np.concatenate(([a], x[interior], [b]))
                sy = np.concatenate(([np.interp(a, x, y)], y[interior], [np.interp(b, x, y)]))
                selected = float(np.trapezoid(sy, x=sx))
            if not math.isfinite(selected) or selected < 0:
                raise FloatingPointError()
            if selected > total:
                if selected - total <= total * 1e-12:
                    selected = total
                else:
                    raise FloatingPointError()
            fraction = selected / total * 100.0
    except (FloatingPointError, OverflowError) as exc:
        raise DomainError("These values exceed the supported numerical range.", "numeric_range") from exc
    return AnalysisResult(a, b, lo, hi, total, selected, fraction, len(data))
