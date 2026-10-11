#!/usr/bin/env python3
"""Independent post-run checks for the bounded ENTH reconstruction.

This reads completed GROMACS artifacts only. It does not alter the simulation
or report biological agreement. Standard library plus the GROMACS CLI only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

THREADS = 2
STAGES = {"em": ("em.log", "em.mdp"), "nvt": ("nvt.log", "nvt.mdp"),
          "npt_restraint": ("npt_restraint.log", "npt_restraint.mdp"),
          "npt_release": ("npt.log", "npt_release.mdp")}


def run(cmd: list[str], cwd: Path, stdin: str | None = None) -> dict:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(THREADS)
    started = time.monotonic()
    try:
        cp = subprocess.run(cmd, cwd=cwd, input=stdin, text=True, capture_output=True,
                            env=env, timeout=300)
        return {"command": cmd, "returncode": cp.returncode, "stdout": cp.stdout,
                "stderr": cp.stderr, "elapsed_seconds": round(time.monotonic()-started, 3)}
    except Exception as exc:
        return {"command": cmd, "returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic()-started, 3)}


def parse_mdp(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(errors="replace").splitlines():
        line = line.split(";", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip().lower()] = v.strip()
    return values


def parse_log(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "fatal_errors": [], "lincs_warning_count": 0, "constraint_error_count": 0}
    text = path.read_text(errors="replace")
    lincs = [line.strip() for line in text.splitlines() if "LINCS WARNING" in line]
    constraint = [line.strip() for line in text.splitlines() if "constraint error" in line.lower()]
    fatal = [line.strip() for line in text.splitlines() if "Fatal error" in line or "Segmentation fault" in line]
    finished = bool(re.search(r"Finished mdrun", text, re.I))
    timed = bool(re.search(r"Time limit reached|Maximum number of hours exceeded|Run time exceeded|Received the TERM signal", text, re.I))
    convergence = re.search(r"Steepest Descents converged to Fmax\s*<\s*([0-9.eE+\-]+)\s+in\s+(\d+)\s+steps", text, re.I)
    step_times = []
    for m in re.finditer(r"(?im)^\s*Step\s+(\d+)\s*,?\s*time\s+([+\-0-9.eE]+)", text):
        step_times.append({"step": int(m.group(1)), "time_ps": float(m.group(2))})
    # GROMACS logs use several aligned formats; retain the final readable step row if present.
    numeric_rows = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+)\s+([+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)\s*$", line)
        if m:
            numeric_rows.append({"step": int(m.group(1)), "time_ps": float(m.group(2))})
    return {"exists": True, "finished_mdrun_marker": finished, "time_limit_marker": timed,
            "lincs_warning_count": len(lincs), "lincs_warnings": lincs[:12],
            "constraint_error_count": len(constraint), "constraint_errors": constraint[:12],
            "fatal_errors": fatal[:12], "last_step_time_rows": (step_times or numeric_rows)[-3:],
            "has_nan_or_inf": any(re.search(r"(?i)\b(?:nan|[-+]?inf(?:inity)?)\b", line)
                                  for line in text.splitlines()
                                  if not re.fullmatch(r'\s*epsilon-rf\s*=\s*inf\s*', line, re.I)),
            "allowed_infinite_parameter_lines": [line.strip() for line in text.splitlines()
                                                   if re.fullmatch(r'\s*epsilon-rf\s*=\s*inf\s*', line, re.I)],
            "steepest_descent_converged": bool(convergence),
            "minimization_convergence": ({"fmax_threshold": float(convergence.group(1)), "steps": int(convergence.group(2))} if convergence else None)}


def parse_xvg(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "labels": [], "rows": []}
    labels = {}
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"\s*@\s+s(\d+)\s+legend\s+\"(.*?)\"", line)
        if m:
            labels[int(m.group(1)) + 1] = m.group(2)
            continue
        if not line.strip() or line.lstrip().startswith(("#", "@")):
            continue
        try:
            vals = [float(x) for x in line.split()]
            if len(vals) >= 2:
                rows.append(vals)
        except ValueError:
            continue
    return {"exists": True, "labels": ["Time (ps)"] + [labels.get(i, f"column_{i}") for i in range(1, max(labels, default=0)+1)],
            "rows": rows}


def stats(values: list[float]) -> dict:
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return {"n": 0, "finite": False}
    return {"n": len(finite), "finite": len(finite) == len(values), "mean": sum(finite)/len(finite),
            "min": min(finite), "max": max(finite), "first": finite[0], "last": finite[-1]}


def contact_audit(path: Path) -> dict:
    """Describe short intermolecular heavy-atom contacts, with periodic images.

    Protein residues form one component; each lipid is another. Water and ions
    are excluded. Counts are diagnostics, not a universal steric validity test.
    """
    if not path.exists():
        return {'available': False}
    lines = path.read_text().splitlines()
    box = [float(x) for x in lines[-1].split()]
    if len(box) != 3:
        return {'available': False, 'reason': 'requires orthorhombic box'}
    radius = 0.25
    bins = [max(1, int(x / radius)) for x in box]
    widths = [box[i] / bins[i] for i in range(3)]
    grid = defaultdict(list)
    count = 0; smallest = None; shortest = None
    for line in lines[2:2 + int(lines[1])]:
        rn = line[5:10].strip(); an = line[10:15].strip()
        if an.lstrip('0123456789').startswith(('H', 'D')) or rn in {'SOL', 'K', 'CL'}:
            continue
        component = ('lipid', line[:5], rn) if rn in {'POPC', 'SAP', 'S24', 'SAPI2'} else ('protein',)
        pos = tuple(float(line[i:i+8]) % box[k] for k, i in enumerate((20, 28, 36)))
        cell = tuple(int(pos[k] / widths[k]) % bins[k] for k in range(3))
        label = f'{rn}:{line[:5].strip()}:{an}'
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    key = tuple((cell[k] + d) % bins[k] for k, d in enumerate((dx, dy, dz)))
                    for other_component, other_pos, other_label in grid.get(key, []):
                        if component == other_component:
                            continue
                        delta = [min(abs(pos[k]-other_pos[k]), box[k]-abs(pos[k]-other_pos[k])) for k in range(3)]
                        dist = math.sqrt(sum(d*d for d in delta))
                        if dist < radius and (smallest is None or dist < smallest):
                            smallest = dist; shortest = [other_label, label]
                        if dist < 0.18:
                            count += 1
        grid[cell].append((component, pos, label))
    return {'available': True, 'search_radius_nm': radius, 'minimum_distance_nm_within_radius': smallest,
            'shortest_pair': shortest, 'intermolecular_heavy_pairs_below_0_18nm': count,
            'scope': 'protein/lipid and lipid/lipid heavy atoms; water and ions excluded; periodic minimum-image distances'}


def parse_gro(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    lines = path.read_text(errors="replace").splitlines()
    if len(lines) < 3:
        return {"exists": True, "error": "truncated GRO"}
    header = lines[0]
    mt = re.search(r"\bt\s*=\s*([+\-0-9.eE]+)", header)
    natoms = int(lines[1].strip())
    residues = []
    for line in lines[2:2+natoms]:
        try:
            resnum = int(line[:5]); rname = line[5:10].strip().upper(); aname = line[10:15].strip()
            x, y, z = (float(line[i:i+8])*10 for i in (20, 28, 36))
            residues.append((resnum, rname, aname, x, y, z))
        except (ValueError, IndexError):
            continue
    boxline = lines[2+natoms] if len(lines) > 2+natoms else ""
    try:
        box_nm = [float(x) for x in boxline.split()]
    except ValueError:
        box_nm = []
    return {"exists": True, "header": header, "time_ps": float(mt.group(1)) if mt else None,
            "declared_atom_count": natoms, "parsed_atom_count": len(residues), "box_nm": box_nm,
            "atoms": residues}


def leaflet_analysis(gro: dict) -> dict:
    if not gro.get("exists") or "atoms" not in gro:
        return {"status": "unavailable"}
    box_nm = gro.get("box_nm", [])
    if len(box_nm) < 3 or box_nm[2] <= 0:
        return {"status": "unavailable", "reason": "No valid z box dimension"}
    lz = box_nm[2] * 10.0
    # One phosphorus P per lipid is used: SAP's P4/P5 are additional headgroup phosphates.
    lipids = {}
    for resnum, rname, aname, x, y, z in gro["atoms"]:
        is_pc = rname == "POPC"
        is_pip2 = rname.startswith("SAP") or rname in {"S24", "PI2"}
        if aname == "P" and (is_pc or is_pip2):
            lipids[(resnum, rname)] = (z % lz, "POPC" if is_pc else "PIP2")
    if len(lipids) < 6:
        return {"status": "failed", "reason": "Fewer than six recognized lipid P anchors", "recognized": len(lipids)}
    zs = [v[0] for v in lipids.values()]
    angle = [2*math.pi*z/lz for z in zs]
    c = sum(math.cos(a) for a in angle); s = sum(math.sin(a) for a in angle)
    center = (math.atan2(s, c) % (2*math.pi)) * lz/(2*math.pi)
    signed = {}
    for key, (z, kind) in lipids.items():
        dz = ((z-center + lz/2) % lz) - lz/2
        signed[key] = (dz, kind)
    upper = [k for k, (dz, _) in signed.items() if dz > 0]
    lower = [k for k, (dz, _) in signed.items() if dz < 0]
    upz = [signed[k][0] for k in upper]; loz = [signed[k][0] for k in lower]
    sep = (sum(upz)/len(upz) - sum(loz)/len(loz)) if upper and lower else None
    popc_up = sum(signed[k][1] == "POPC" for k in upper)
    popc_lo = sum(signed[k][1] == "POPC" for k in lower)
    pip2_up = sum(signed[k][1] == "PIP2" for k in upper)
    pip2_lo = sum(signed[k][1] == "PIP2" for k in lower)
    return {"status": "checked", "recognized_lipid_P_count": len(lipids), "membrane_center_z_A": center,
            "leaflet_separation_A": sep, "upper": {"POPC": popc_up, "PIP2": pip2_up, "total": len(upper)},
            "lower": {"POPC": popc_lo, "PIP2": pip2_lo, "total": len(lower)},
            "pbc_method": "Circular mean for membrane center; phosphate z displacements wrapped to [-Lz/2,Lz/2).",
            "checks": {"both_leaflets_present": bool(len(upper) >= 3 and len(lower) >= 3),
                       "exactly_one_pip2": pip2_up + pip2_lo == 1,
                       "pip2_in_upper_leaflet": pip2_up == 1 and pip2_lo == 0,
                       "separation_plausible": bool(sep is not None and 10 < sep < 55)}}


def energy_from_xvg(path: Path, report: dict) -> dict:
    data = parse_xvg(path)
    rows = data["rows"]
    labels = data["labels"]
    summaries = {}
    for i, label in enumerate(labels):
        vals = [r[i] for r in rows if i < len(r)]
        summaries[label] = stats(vals)
    return {"path": str(path), "columns_and_labels": labels, "sample_count": len(rows), "summary": summaries,
            "time_first_ps": rows[0][0] if rows else None, "time_last_ps": rows[-1][0] if rows else None,
            "finite_all_columns": bool(rows) and all(math.isfinite(x) for row in rows for x in row)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, required=True, help="validation-006 root (contains run/)")
    ap.add_argument("--gmx", default="gmx")
    args = ap.parse_args()
    root = args.workdir.resolve(); run_dir = root / "run"
    report = {"analyzer": "scripts/enth_analysis.py", "status": "running", "workdir": str(root),
              "checks": {}, "commands": [], "scientific_agreement_status": "not_assessed"}
    if not run_dir.is_dir():
        report.update(status="failed", error=f"Run directory not found: {run_dir}")
        save(root, report); return 2

    stages = {}
    stage_definitions = dict(STAGES)
    if (run_dir / 'em_relax.mdp').exists():
        stage_definitions['em_relax'] = ('em_relax.log', 'em_relax.mdp')
    for name, (logname, mdpname) in stage_definitions.items():
        log = parse_log(run_dir/logname); mdp = parse_mdp(run_dir/mdpname)
        stages[name] = {"log": log, "mdp": mdp,
                        "expected_nsteps": int(mdp["nsteps"]) if mdp.get("nsteps", "").isdigit() else None,
                        "dt_ps": float(mdp["dt"]) if mdp.get("dt") else None}
    report["stages"] = stages
    report['starting_contact_audit'] = {name: contact_audit(run_dir / (name + '.gro'))
                                        for name in ('ions', 'em_relax', 'em')}
    all_logs = [v["log"] for v in stages.values() if v["log"].get("exists")]
    warnings = sum(x.get("lincs_warning_count", 0) for x in all_logs)
    constraint_errors = sum(x.get("constraint_error_count", 0) for x in all_logs)
    fatal = [f"{name}: {err}" for name, s in stages.items() for err in s["log"].get("fatal_errors", [])]
    report["checks"]["all_stage_logs_present"] = len(all_logs) == len(stage_definitions)
    report["checks"]["no_lincs_or_constraint_warnings_any_stage"] = warnings == 0 and constraint_errors == 0
    report["checks"]["no_fatal_errors_any_stage"] = not fatal
    report["checks"]["no_nonfinite_tokens_any_stage"] = not any(x.get('has_nan_or_inf', False) for x in all_logs)
    report["all_stage_lincs_warning_count"] = warnings
    report["all_stage_constraint_error_count"] = constraint_errors
    report["fatal_errors"] = fatal

    release = stages["npt_release"]
    expected_steps = release["expected_nsteps"]
    dt = release["dt_ps"]
    expected_duration = expected_steps*dt if expected_steps is not None and dt is not None else None
    final_gro = parse_gro(run_dir/"final.gro")
    production_gro = parse_gro(run_dir/"npt.gro")
    stage_files = {"nvt": "nvt.gro", "npt_restraint": "npt_restraint.gro", "npt_release": "npt.gro"}
    expected_stage_times = {}
    cumulative = 0.0
    for name in ("nvt", "npt_restraint", "npt_release"):
        st = stages[name]
        if st["expected_nsteps"] is not None and st["dt_ps"] is not None:
            cumulative += st["expected_nsteps"] * st["dt_ps"]
            expected_stage_times[name] = cumulative
    trajectory_check = run([args.gmx, "check", "-f", "npt.xtc"], run_dir)
    report["commands"].append(trajectory_check)
    check_text = trajectory_check.get("stdout", "") + "\n" + trajectory_check.get("stderr", "")
    frame_times = [float(x) for x in re.findall(r"(?i)(?:Reading frame|Last frame)\s+\d+\s+time\s+([0-9]+(?:\.[0-9]+)?)", check_text)]
    # Recover the last intact trajectory frame after a supervisor interruption.
    recovery = None
    if (run_dir/"npt.xtc").exists() and frame_times:
        last_xtc_time = max(frame_times)
        recovery = run([args.gmx, "trjconv", "-s", "npt.tpr", "-f", "npt.xtc", "-o",
                        "independent-final.gro", "-dump", f"{last_xtc_time:.4f}"], run_dir, "System\n")
        report["commands"].append(recovery)
        if recovery["returncode"] == 0 and (run_dir/"independent-final.gro").exists():
            final_gro = parse_gro(run_dir/"independent-final.gro")
    gro_time = final_gro.get("time_ps") if final_gro.get("exists") else production_gro.get("time_ps")
    # Completed stages are assigned their configured duration. For an interrupted
    # final stage, use the observed XTC span (time origin may reset on restart).
    stage_local_times = {}
    frame_span = max(frame_times)-min(frame_times) if len(frame_times) >= 2 else None
    for name in ("nvt", "npt_restraint", "npt_release"):
        st = stages[name]
        requested = st["expected_nsteps"]*st["dt_ps"] if st["expected_nsteps"] is not None and st["dt_ps"] else None
        # Finished mdrun also occurs after graceful TERM/time stops.
        stage_gro = parse_gro(run_dir / stage_files[name])
        coordinate_time = stage_gro.get('time_ps')
        if coordinate_time is not None:
            stage_local_times[name] = coordinate_time
        elif name == "npt_release" and frame_span is not None:
            stage_local_times[name] = frame_span
        elif name == "npt_release" and gro_time is not None:
            stage_local_times[name] = max(0.0, gro_time-sum(stage_local_times.values()))
        else:
            rows = stages[name]["log"].get("last_step_time_rows", [])
            stage_local_times[name] = rows[-1]["time_ps"] if rows else None
    stage_times = {}
    cumulative_observed = 0.0
    for name in ("nvt", "npt_restraint", "npt_release"):
        local = stage_local_times.get(name)
        if local is not None:
            cumulative_observed += local
            stage_times[name] = cumulative_observed
    report["trajectory"] = {"gmx_check_returncode": trajectory_check["returncode"],
                            "gmx_check_excerpt": check_text[-4000:], "final_gro_time_ps": gro_time,
                            "last_valid_frame_recovery_returncode": recovery.get("returncode") if recovery else None,
                            "trajectory_parsed_times_ps": frame_times[-4:], "release_mdp_nsteps": expected_steps,
                            "release_mdp_dt_ps": dt, "release_duration_ps": expected_duration,
                            "observed_stage_local_times_ps": stage_local_times,
                            "observed_cumulative_stage_times_ps": stage_times,
                            "expected_cumulative_stage_times_ps": expected_stage_times,
                            "full_requested_run_duration_ps": (sum((s["expected_nsteps"] or 0)*(s["dt_ps"] or 0)
                                                                  for n, s in stages.items() if n in stage_files)),
                            "release_finished_marker": release["log"].get("finished_mdrun_marker"),
                            "time_limit_marker": release["log"].get("time_limit_marker")}
    observed_last = cumulative_observed if cumulative_observed else (gro_time if gro_time is not None else (max(frame_times) if frame_times else None))
    total_expected = report["trajectory"]["full_requested_run_duration_ps"]
    report["trajectory"]["observed_last_time_ps"] = observed_last
    report["trajectory"]["completion_check"] = bool(
        expected_duration is not None and expected_duration >= 79.9 and
        stages["nvt"]["log"].get("finished_mdrun_marker") and
        stages["npt_restraint"]["log"].get("finished_mdrun_marker") and
        release["log"].get("finished_mdrun_marker") and not release["log"].get("time_limit_marker") and
        observed_last is not None and observed_last >= total_expected - 0.25)
    report["trajectory"]["stage_time_checks"] = {
        name: bool(stage_times.get(name) is not None and expected_stage_times.get(name) is not None and
                   abs(stage_times[name]-expected_stage_times[name]) <= 0.05)
        for name in stage_files}
    observed_stage_durations = {}
    for name in ("nvt", "npt_restraint", "npt_release"):
        t = stage_local_times.get(name)
        if t is not None:
            actual_duration = max(0.0, t)
            st = stages[name]
            observed_stage_durations[name] = {"observed_duration_ps": actual_duration,
                "observed_steps_estimate": round(actual_duration/st["dt_ps"]) if st["dt_ps"] else None,
                "requested_steps": st["expected_nsteps"], "requested_duration_ps": (st["expected_nsteps"]*st["dt_ps"] if st["expected_nsteps"] is not None and st["dt_ps"] else None)}
    report["trajectory"]["observed_stage_durations"] = observed_stage_durations
    report["trajectory"]["observed_cumulative_stage_times_ps"] = stage_times
    report["checks"]["requested_100ps_dynamics_completed"] = report["trajectory"]["completion_check"]
    report["checks"]["each_stage_reached_expected_time"] = all(report["trajectory"]["stage_time_checks"].values())
    report["checks"]["minimization_converged_below_requested_fmax"] = bool(
        stages["em"]["log"].get("steepest_descent_converged") and
        stages["em"]["log"].get("minimization_convergence", {}).get("fmax_threshold", 1e9) <= 1000)
    if 'em_relax' in stages:
        report["checks"]["minimization_converged_below_requested_fmax"] &= bool(
            stages['em_relax']['log'].get('steepest_descent_converged') and
            stages['em_relax']['log'].get('minimization_convergence', {}).get('fmax_threshold', 1e9) <= 1000)

    # Independently extract release-stage observables so column names are inspected, not assumed.
    energy_cmd = run([args.gmx, "energy", "-f", "npt.edr", "-o", "independent-energy.xvg"],
                     run_dir, "Potential\nTemperature\nPressure\nVolume\n0\n")
    report["commands"].append(energy_cmd)
    energy = energy_from_xvg(run_dir/"independent-energy.xvg", report)
    energy["returncode"] = energy_cmd["returncode"]
    report["energy"] = energy
    labels = {x.lower(): x for x in energy.get("columns_and_labels", [])}
    temp_label = next((orig for low, orig in labels.items() if "temperature" in low), None)
    vol_label = next((orig for low, orig in labels.items() if "volume" in low), None)
    pressure_label = next((orig for low, orig in labels.items() if "pressure" in low), None)
    p_label = next((orig for low, orig in labels.items() if "potential" in low), None)
    es = energy.get("summary", {})
    temp_stats, vol_stats = es.get(temp_label, {}), es.get(vol_label, {})
    # Use only the final 20 ps for temperature, avoiding warm-up and early box relaxation.
    xvg_rows = parse_xvg(run_dir/"independent-energy.xvg")["rows"]
    recent = [row for row in xvg_rows if row[0] >= (xvg_rows[-1][0]-20.0)] if xvg_rows else []
    temp_col = energy.get("columns_and_labels", []).index(temp_label) if temp_label in energy.get("columns_and_labels", []) else None
    recent_temp = stats([row[temp_col] for row in recent if temp_col is not None and temp_col < len(row)]) if recent else {}
    vol_change = None
    if vol_stats.get("first") and vol_stats.get("last"):
        vol_change = (vol_stats["last"]-vol_stats["first"])/vol_stats["first"]
    report["energy"]["recent_20ps_temperature_K"] = recent_temp
    report["energy"]["volume_fractional_first_to_last_change"] = vol_change
    report["energy"]["observed_labels"] = {"potential": p_label, "temperature": temp_label,
                                          "pressure": pressure_label, "volume": vol_label}
    report["checks"]["finite_energy_observables"] = energy_cmd["returncode"] == 0 and energy["finite_all_columns"] and all(
        x is not None for x in (p_label, temp_label, pressure_label, vol_label))
    report["checks"]["temperature_in_broad_target_band"] = bool(recent_temp.get("finite") and 280 <= recent_temp.get("mean", -1) <= 326)
    report["checks"]["positive_limited_volume"] = bool(vol_stats.get("finite") and vol_stats.get("min", 0) > 0 and vol_change is not None and abs(vol_change) <= 0.10)

    report["final_structure"] = {k: v for k, v in final_gro.items() if k != "atoms"}
    mem = leaflet_analysis(final_gro)
    report["membrane"] = mem
    report["checks"]["membrane_leaflets_and_pip2"] = all(mem.get("checks", {}).values()) if mem.get("status") == "checked" else False

    # DSSP uses plain per-residue one-letter rows in this GROMACS version.
    # Test both hydrogen modes on the minimized starting structure as a positive
    # control before interpreting any trajectory assignments.
    dssp_runs = {}
    def dssp_rows(path: Path) -> dict:
        raw = path.read_text(errors="replace").splitlines() if path.exists() else []
        seqs = [line.strip() for line in raw if len(line.strip()) == 158 and
                all(c in "HBEGITS~P" for c in line.strip())]
        return {"output_bytes": path.stat().st_size if path.exists() else 0,
                "frame_or_structure_rows": len(seqs), "sequence_rows": seqs,
                "alpha_counts": [s.count("H") for s in seqs],
                "first18_alpha_fraction": [sum(c == "H" for c in s[:18])/18 for s in seqs],
                "state_counts_per_first18": [dict(Counter(s[:18])) for s in seqs]}
    for mode in ("gromacs", "dssp"):
        control_out = f"dssp-control-{mode}.dat"
        control_cmd = run([args.gmx, "dssp", "-s", "npt.tpr", "-f", "em.gro", "-o", control_out,
                           "-sel", "protein", "-xvg", "none", "-tu", "ps", "-hmode", mode], run_dir)
        report["commands"].append(control_cmd)
        control_data = dssp_rows(run_dir/control_out)
        control_data["returncode"] = control_cmd["returncode"]
        dssp_runs["starting_structure_"+mode] = control_data
        traj_out = f"protein-dssp-{mode}.dat"
        traj_cmd = run([args.gmx, "dssp", "-s", "npt.tpr", "-f", "npt.xtc", "-o", traj_out,
                        "-sel", "protein", "-xvg", "none", "-tu", "ps", "-hmode", mode], run_dir)
        report["commands"].append(traj_cmd)
        traj_data = dssp_rows(run_dir/traj_out)
        traj_data["returncode"] = traj_cmd["returncode"]
        dssp_runs["trajectory_"+mode] = traj_data
    positive_control = any(v["returncode"] == 0 and v["alpha_counts"] and max(v["alpha_counts"]) > 0
                           for k, v in dssp_runs.items() if k.startswith("starting_structure_"))
    report["h0_dssp"] = {"runs": dssp_runs, "positive_control_has_alpha": positive_control,
                         "observed_residue_count": 158,
                         "status": "validated_for_descriptive_assignments" if positive_control else "unvalidated_positive_control_failed",
                         "assumed_h0_first18_alpha_fraction_by_frame": dssp_runs.get("trajectory_dssp", {}).get("first18_alpha_fraction", []) if positive_control else [],
                         "assumed_h0_first18_states_by_frame": dssp_runs.get("trajectory_dssp", {}).get("state_counts_per_first18", []) if positive_control else [],
                         "residue_mapping_status": "unverified proxy: first 18 residues in selected protein order; paper-specific H0 mapping unavailable",
                         "interpretation_limit": "If neither starting-structure hydrogen mode yields alpha assignments, DSSP is unvalidated and no H0-disorder inference is made."}
    report["checks"]["h0_dssp_positive_control"] = positive_control

    physical_required = ["all_stage_logs_present", "no_lincs_or_constraint_warnings_any_stage", "no_fatal_errors_any_stage", "no_nonfinite_tokens_any_stage",
                        "minimization_converged_below_requested_fmax", "finite_energy_observables",
                        "temperature_in_broad_target_band", "positive_limited_volume", "membrane_leaflets_and_pip2"]
    report["physical_checks_passed"] = all(report["checks"].get(k, False) for k in physical_required)
    report["required_checks_passed"] = report["physical_checks_passed"] and report["checks"].get("requested_100ps_dynamics_completed", False)
    report["status"] = ("bounded_physical_validation_passed" if report["required_checks_passed"] else
                        "partial_run_physical_checks_passed" if report["physical_checks_passed"] else
                        "bounded_validation_failed_or_incomplete")
    report["summary"] = ("All independent checks passed and the requested 100-ps dynamics completed." if report["required_checks_passed"] else
                         "The run was interrupted before 100 ps; available partial-run physical checks passed." if report["physical_checks_passed"] else
                         "One or more physical checks failed or were unavailable; see check details and raw logs.")
    report["interpretation"] = "No 100-ps completion is claimed unless the trajectory and all stage durations confirm it. This is only a reconstructed inserted-state CPU validation; it does not reproduce Figure 4, assess the authors' pull protocol, validate the uncertain salt unit or exact H0 residue mapping, or establish biological agreement."
    save(root, report)
    return 0 if report["physical_checks_passed"] else 1


def save(root: Path, report: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root/"independent-analysis.json").write_text(json.dumps(report, indent=2)+"\n")
    lines = ["# Independent ENTH bounded-run analysis", "", f"Status: **{report.get('status')}**.", "",
             report.get("summary", ""), "", "## Checks", ""]
    for key, value in report.get("checks", {}).items():
        lines.append(f"- `{key}`: **{value}**")
    lines += ["", "## Run completion", "", json.dumps(report.get("trajectory", {}), indent=2),
              "", "## Energy labels and summaries", "", json.dumps(report.get("energy", {}), indent=2),
              "", "## Membrane", "", json.dumps(report.get("membrane", {}), indent=2),
              "", "## H0 DSSP", "", json.dumps(report.get("h0_dssp", {}), indent=2),
              "", report.get("interpretation", "")]
    (root/"independent-analysis.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    raise SystemExit(main())
