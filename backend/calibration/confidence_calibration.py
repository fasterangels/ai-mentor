from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List


@dataclass
class ConfidenceCalibrator:
    version: str
    n_bins: int
    bin_edges: List[float]
    bin_values: List[float]
    default_value: float = 0.5


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def fit_binning_calibrator(
    confidences: List[float],
    outcomes: List[int],
    n_bins: int = 10,
    version: str = "v0",
) -> ConfidenceCalibrator:
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must have the same length")
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    n = len(confidences)
    if n == 0:
        # Degenerate case: no data; fall back to a symmetric identity-like calibrator.
        bin_edges = [i / float(n_bins) for i in range(n_bins + 1)]
        bin_values = [
            (bin_edges[i] + bin_edges[i + 1]) / 2.0 for i in range(n_bins)
        ]
        return ConfidenceCalibrator(
            version=version,
            n_bins=n_bins,
            bin_edges=bin_edges,
            bin_values=bin_values,
            default_value=0.5,
        )

    clamped = [clamp01(c) for c in confidences]
    total_outcome = sum(1 if o else 0 for o in outcomes)
    default_value = total_outcome / float(n) if n > 0 else 0.5

    bin_edges = [i / float(n_bins) for i in range(n_bins + 1)]
    sums = [0.0 for _ in range(n_bins)]
    counts = [0 for _ in range(n_bins)]

    for c, y in zip(clamped, outcomes):
        # Map clamped confidence into bin index in [0, n_bins-1].
        idx = int(c * n_bins)
        if idx >= n_bins:
            idx = n_bins - 1
        sums[idx] += 1.0 if y else 0.0
        counts[idx] += 1

    bin_values: List[float] = []
    for i in range(n_bins):
        if counts[i] > 0:
            bin_values.append(sums[i] / float(counts[i]))
        else:
            bin_values.append(default_value)

    return ConfidenceCalibrator(
        version=version,
        n_bins=n_bins,
        bin_edges=bin_edges,
        bin_values=bin_values,
        default_value=default_value,
    )


def apply(calibrator: ConfidenceCalibrator, conf_raw: float) -> float:
    """
    Apply a fitted binning calibrator to a raw confidence value.
    """
    c = clamp01(conf_raw)
    n_bins = calibrator.n_bins
    if n_bins <= 0:
        return calibrator.default_value
    idx = int(c * n_bins)
    if idx >= n_bins:
        idx = n_bins - 1
    try:
        return float(calibrator.bin_values[idx])
    except (IndexError, TypeError):
        return calibrator.default_value


def save_calibrator(calibrator: ConfidenceCalibrator, path: str) -> None:
    p = Path(path)
    data = {
        "version": calibrator.version,
        "n_bins": calibrator.n_bins,
        "bin_edges": list(calibrator.bin_edges),
        "bin_values": list(calibrator.bin_values),
        "default_value": calibrator.default_value,
    }
    p.write_text(json.dumps(data, indent=2, sort_keys=True))


def load_calibrator(path: str) -> ConfidenceCalibrator:
    p = Path(path)
    if not p.exists():
        # Identity-like fallback: uniform bins, midpoints as calibrated values.
        n_bins = 10
        bin_edges = [i / float(n_bins) for i in range(n_bins + 1)]
        bin_values = [
            (bin_edges[i] + bin_edges[i + 1]) / 2.0 for i in range(n_bins)
        ]
        return ConfidenceCalibrator(
            version="default",
            n_bins=n_bins,
            bin_edges=bin_edges,
            bin_values=bin_values,
            default_value=0.5,
        )

    data = json.loads(p.read_text())
    n_bins = int(data["n_bins"])
    bin_edges = [float(x) for x in data["bin_edges"]]
    bin_values = [float(x) for x in data["bin_values"]]
    default_value = float(data.get("default_value", 0.5))
    return ConfidenceCalibrator(
        version=str(data.get("version", "v0")),
        n_bins=n_bins,
        bin_edges=bin_edges,
        bin_values=bin_values,
        default_value=default_value,
    )

