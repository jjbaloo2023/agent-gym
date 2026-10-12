# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
"""Versioned, deliberately narrow benchmark configuration."""
from dataclasses import asdict, dataclass
import math
from pathlib import Path
import yaml


@dataclass(frozen=True)
class Case:
    schema_version: int = 1
    flow: str = "taylor_green_2d"
    resolution: int = 32
    reynolds_number: float = 20.0
    mach_number: float = 0.05
    steps: int = 100
    report_interval: int = 10
    device: str = "cpu"
    precision: str = "float64"
    max_mass_drift: float = 1e-8
    max_velocity_error: float = 0.05

    def __post_init__(self):
        for key in ("schema_version", "resolution", "steps", "report_interval"):
            value = getattr(self, key)
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if self.schema_version != 1:
            raise ValueError("Unsupported schema_version")
        if self.flow not in ("taylor_green_2d", "taylor_green_3d"):
            raise ValueError("Only Taylor-Green benchmark cases are implemented")
        if self.resolution < 16:
            raise ValueError("resolution must be >= 16")
        for key in ("reynolds_number", "mach_number", "max_mass_drift", "max_velocity_error"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        if self.mach_number > 0.1:
            raise ValueError("mach_number exceeds the initial 0.1 operating limit")
        if self.device not in ("cpu", "cuda") or self.precision not in ("float32", "float64"):
            raise ValueError("device must be cpu/cuda and precision float32/float64")
        if not 0.51 <= self.tau <= 2.0:
            raise ValueError(f"tau={self.tau:.6g} is outside the initial [0.51, 2] envelope")

    @property
    def dimension(self):
        return 2 if self.flow.endswith("2d") else 3

    @property
    def tau(self):
        return 0.5 + 3 * (self.resolution / (2 * math.pi)) * (self.mach_number / math.sqrt(3)) / self.reynolds_number

    def estimate(self):
        cells = self.resolution ** self.dimension
        q = 9 if self.dimension == 2 else 19
        size = 4 if self.precision == "float32" else 8
        return {"cells": cells, "tau": self.tau, "distribution_bytes_two_buffers": 2*q*cells*size,
                "working_memory_estimate_bytes": (8*q + 20)*cells*size,
                "memory_note": "Conservative planning estimate; not a measured peak or allocation guarantee."}


def load_case(path):
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("Case must be a YAML/JSON mapping")
    try:
        return Case(**data)
    except TypeError as exc:
        raise ValueError(f"Invalid case keys: {exc}") from exc


def case_dict(case):
    return asdict(case)
