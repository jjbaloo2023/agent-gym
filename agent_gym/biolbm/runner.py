# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
"""Lettuce adapter. Numerical operations remain in the dependency."""
import importlib.metadata
import json
from pathlib import Path
import time
import numpy as np
from .config import case_dict


def write_json(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def run(case, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "case.json", case_dict(case))
    write_json(output / "status.json", {"state": "starting", "step": 0})
    try:
        return _run(case, output)
    except Exception as exc:
        write_json(output / "status.json", {"state": "failed", "error": str(exc)})
        raise


def _run(case, output):
    try:
        import torch
        import lettuce as lt
    except ImportError as exc:
        raise RuntimeError("Install Agent Gym with the biolbm extra in Python 3.12+ to run simulations") from exc
    if case.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable; refusing CPU fallback")
    context = lt.Context(device=case.device, dtype=getattr(torch, case.precision), use_native=False)
    stencil = lt.D2Q9() if case.dimension == 2 else lt.D3Q19()
    flow = lt.TaylorGreenVortex(context, [case.resolution]*case.dimension,
                              case.reynolds_number, case.mach_number, stencil=stencil)
    simulation = lt.Simulation(flow, lt.BGKCollision(tau=flow.units.relaxation_parameter_lu), [])
    mass0 = float(flow.rho().sum())
    history = []
    start = time.perf_counter()
    with torch.no_grad():
        while True:
            context.synchronize()
            rho, velocity = flow.rho(), flow.u()
            if not bool(torch.isfinite(flow.f).all()) or not bool(torch.isfinite(velocity).all()) or bool((rho <= 0).any()):
                raise RuntimeError(f"Nonfinite fields or nonpositive density at step {flow.i}")
            drift = abs(float(rho.sum()) - mass0) / abs(mass0)
            mach = float(torch.linalg.vector_norm(velocity, dim=0).max()) / float(stencil.cs)
            row = {"step": flow.i, "relative_mass_drift": drift, "max_lattice_mach": mach}
            if case.dimension == 2:
                physical_time = flow.units.convert_time_to_pu(flow.i)
                _, expected = flow.analytic_solution(physical_time)
                row["relative_velocity_l2_error"] = float(torch.linalg.vector_norm(flow.u_pu-expected) / torch.linalg.vector_norm(expected))
            history.append(row)
            write_json(output / "history.json", history)
            write_json(output / "status.json", {"state": "running", **row})
            if drift > case.max_mass_drift or mach > 0.15:
                raise RuntimeError(f"Conservation or Mach limit exceeded at step {flow.i}")
            if flow.i >= case.steps:
                break
            simulation(min(case.report_interval, case.steps-flow.i))
        context.synchronize()
        elapsed = time.perf_counter()-start
        lt.VTKReporter(interval=1, filename_base=str(output / "fields"))(simulation)
        np.savez_compressed(output / "checkpoint.npz", f=flow.f.detach().cpu().numpy(), step=flow.i)
    numerical_pass = case.dimension == 2 and history[-1]["relative_velocity_l2_error"] <= case.max_velocity_error
    summary = {"state": "completed", "steps": flow.i, "elapsed_seconds": elapsed,
               "mlups_including_diagnostics": case.steps*case.resolution**case.dimension/1e6/elapsed,
               "lettuce_version": importlib.metadata.version("lettucecfd"), "torch_version": torch.__version__,
               "device": str(context.device), "precision": case.precision, "tau": float(flow.units.relaxation_parameter_lu),
               "benchmark_passed": numerical_pass if case.dimension == 2 else None,
               "validation_scope": "2D final velocity error and sampled conservation; no refinement gate" if case.dimension == 2 else "3D smoke run only; no analytical transient validation",
               "final": history[-1]}
    write_json(output / "summary.json", summary)
    write_json(output / "status.json", {"state": "completed", "step": flow.i})
    return summary
