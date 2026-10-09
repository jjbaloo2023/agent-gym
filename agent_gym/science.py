"""Bounded scientific operations shared by MCP and local verification."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import uuid
from .core import atomic_json

ROOT = Path(os.environ.get("AGENT_GYM_SCIENCE_RUNS", "/home/gym/agent-gym-runs")).resolve()
HERE = Path(__file__).parent
CAD_PYTHON = "/opt/agent-gym-cad/bin/python"
FOAM_BASHRC = "/opt/openfoam14/etc/bashrc"

@dataclass(frozen=True)
class Venturi:
    inlet_diameter_mm: float
    throat_diameter_mm: float
    inlet_length_mm: float
    convergent_length_mm: float
    throat_length_mm: float
    diffuser_length_mm: float
    outlet_length_mm: float
    wall_thickness_mm: float = 2.0

    def __post_init__(self):
        for name, v in asdict(self).items():
            lower = 0 if name in {"inlet_length_mm", "outlet_length_mm"} else 0.5
            if (isinstance(v, bool) or not isinstance(v, (int, float))
                    or not math.isfinite(v) or not lower <= v <= 1000):
                raise ValueError(f"{name} must be finite and between {lower} and 1000 mm")
        if self.throat_diameter_mm >= self.inlet_diameter_mm:
            raise ValueError("Throat must be smaller than inlet")
        if self.length_mm > 2000:
            raise ValueError("Total length must not exceed 2000 mm")

    @property
    def length_mm(self):
        return sum([self.inlet_length_mm, self.convergent_length_mm,
                    self.throat_length_mm, self.diffuser_length_mm, self.outlet_length_mm])

def run_path(run_id):
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ValueError("Expected an opaque run ID")
    path = ROOT / run_id
    if not path.is_dir() or path.is_symlink():
        raise FileNotFoundError("Unknown run")
    return path

def invoke(command, folder, log_name, timeout=180):
    with (folder / log_name).open("w") as log:
        result = subprocess.run(command, cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False,
                                env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "OMP_NUM_THREADS": "2"})
    if result.returncode:
        tail = (folder / log_name).read_text(errors="replace")[-3000:]
        raise RuntimeError(f"Tool failed ({result.returncode}): {tail}")

def artifacts(folder):
    return {p.name: {"bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in folder.iterdir() if p.is_file() and p.suffix in {".step", ".FCStd", ".stl", ".svg", ".msh"}}

def build(spec):
    venturi = Venturi(**spec)
    ROOT.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    folder = ROOT / run_id
    folder.mkdir()
    atomic_json(folder / "spec.json", asdict(venturi))
    atomic_json(folder / "status.json", {"run_id": run_id, "stage": "cad_running",
                                       "source": "agent_parameters", "training_eligibility": "unreviewed"})
    try:
        invoke([CAD_PYTHON, str(HERE / "cad_worker.py"), str(folder)], folder, "cad.log")
        report = json.loads((folder / "cad-report.json").read_text())
        result = {"run_id": run_id, "stage": "cad_complete", "report": report,
                  "artifacts": artifacts(folder), "path": str(folder),
                  "source": "agent_parameters", "training_eligibility": "unreviewed"}
        atomic_json(folder / "status.json", result)
        return result
    except Exception as error:
        atomic_json(folder / "status.json", {"run_id": run_id, "stage": "cad_failed", "error": str(error)})
        raise

def mesh(run_id, size_mm=3.0):
    folder = run_path(run_id)
    spec = Venturi(**json.loads((folder / "spec.json").read_text()))
    if not math.isfinite(size_mm) or not max(0.5, spec.throat_diameter_mm / 12) <= size_mm <= 20:
        raise ValueError("Mesh size must be between max(0.5, throat diameter / 12) and 20 mm")
    # Reject obviously excessive requests before launching the mesher.
    upper_volume = math.pi * (spec.inlet_diameter_mm / 2)**2 * spec.length_mm
    if 6 * upper_volume / size_mm**3 > 250000:
        raise ValueError("Requested mesh is too fine for the local budget; increase size_mm")
    lock = folder / ".mesh-lock"
    with lock.open("x"):
        pass
    atomic_json(folder / "mesh-status.json", {"run_id": run_id, "stage": "mesh_running", "size_mm": size_mm})
    try:
        invoke(["/usr/bin/python3", str(HERE / "mesh_worker.py"), str(folder), str(size_mm)],
               folder, "gmsh.log")
        case = folder / "foam"
        case.mkdir(exist_ok=True)
        (case / "system").mkdir(exist_ok=True)
        (case / "system" / "controlDict").write_text("""FoamFile
{
    format ascii;
    class dictionary;
    object controlDict;
}
application foamRun;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 1;
deltaT 1;
writeControl timeStep;
writeInterval 1;
""")
        # All shell text is fixed. The working directory and mesh file are internal.
        script = f"source {FOAM_BASHRC}; gmshToFoam ../fluid.msh"
        invoke(["bash", "-lc", script], case, "mesh-convert.log")
        boundary = case / "constant" / "polyMesh" / "boundary"
        boundary.write_text(re.sub(r"(\bwalls\s*\{[^}]*?\btype\s+)patch;", r"\1wall;", boundary.read_text()))
        invoke(["bash", "-lc", f"source {FOAM_BASHRC}; checkMesh"], case, "mesh-check.log")
        check = (case / "mesh-check.log").read_text()
        if "Mesh OK." not in check:
            raise RuntimeError("OpenFOAM checkMesh did not report Mesh OK")
        result = {"run_id": run_id, "stage": "mesh_complete",
                  "mesh": json.loads((folder / "mesh-report.json").read_text()),
                  "openfoam_check": "Mesh OK.", "artifacts": artifacts(folder)}
        atomic_json(folder / "mesh-status.json", result)
        return result
    except Exception as error:
        atomic_json(folder / "mesh-status.json", {"run_id": run_id, "stage": "mesh_failed", "error": str(error)})
        raise
    finally:
        lock.unlink(missing_ok=True)

def inspect_run(run_id):
    folder = run_path(run_id)
    result = {"spec": json.loads((folder / "spec.json").read_text()),
              "cad": json.loads((folder / "status.json").read_text())}
    if (folder / "mesh-status.json").exists():
        result["mesh"] = json.loads((folder / "mesh-status.json").read_text())
    return result
