#!/usr/bin/env python3
"""Build and run a capped, explicitly reconstructed ENTH/POPC/SAPI24 pilot.

This creates one inserted-state smoke system, not a reproduction of Figure 4.
It uses only Python's standard library plus the GROMACS executable. The caller
must run the whole command inside the benchmark's external process/resource
boundary. All downloaded inputs and generated files stay under --workdir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

SOURCES = {
    "pdb_1h0a": "https://files.rcsb.org/download/1H0A.pdb",
    "c36_gromacs": "https://mackerell.umaryland.edu/download.php?filename=CHARMM_ff_params_files/charmm36-jul2020.ff.tgz",
    "popc_bilayer": "https://www.charmm-gui.org/archive/pure_bilayer/popc.tar.gz",
    "popc_template": "https://www.charmm-gui.org/archive/csml/popc.pdb",
    "sapi24_template": "https://www.charmm-gui.org/archive/csml/sapi24.pdb",
}
MAX_ATOMS = 100_000
MAX_STEPS = 50_000
MAX_BYTES = 1024**3
MAX_SECONDS = 1_800
DT_PS = 0.002


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tree_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def record_file(path: Path, root: Path) -> dict:
    return {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}


def fetch(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "AgentGym-ENTH-validation/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as out:
        shutil.copyfileobj(response, out)
    if path.stat().st_size == 0:
        raise RuntimeError(f"Empty download: {url}")


def xyz(line: str) -> tuple[float, float, float]:
    return float(line[30:38]), float(line[38:46]), float(line[46:54])


def set_xyz(line: str, p: tuple[float, float, float]) -> str:
    return line[:30] + "".join(f"{v:8.3f}" for v in p) + line[54:]


def atom_name(line: str) -> str:
    return line[12:16].strip()


def resname(line: str) -> str:
    # CHARMM-GUI's PDB output uses the full 4-column residue-name field for
    # lipids such as POPC; standard 3-character residues retain a trailing blank.
    return line[17:21].strip().upper()


def resid(line: str) -> tuple[str, str, str]:
    return line[21:22], line[22:26], line[26:27]


def parse_atoms(lines: list[str], accepted: set[str] | None = None) -> list[str]:
    out = []
    for line in lines:
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        if line[16:17] not in (" ", "A"):
            continue
        if accepted is None or resname(line) in accepted:
            out.append(line)
    return out


def mean(points: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    if not points:
        raise ValueError("Cannot average an empty coordinate set")
    return tuple(sum(p[i] for p in points) / len(points) for i in range(3))


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def scale(a, s):
    return tuple(x * s for x in a)


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    n = math.sqrt(dot(a, a))
    if n < 1e-8:
        raise ValueError("Degenerate vector in orientation calculation")
    return scale(a, 1.0 / n)


def rotate_to_z(v):
    """Return Rodrigues rotation matrix mapping v to +z."""
    a = unit(v)
    b = (0.0, 0.0, 1.0)
    c = max(-1.0, min(1.0, dot(a, b)))
    if c > 1 - 1e-10:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    if c < -1 + 1e-10:
        return ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
    k = unit(cross(a, b))
    x, y, z = k
    s = math.sqrt(1 - c * c)
    return (
        (c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s),
        (y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s),
        (z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)),
    )


def matvec(m, v):
    return tuple(dot(row, v) for row in m)


def pdb_box(lines: list[str]) -> tuple[float, float, float]:
    for line in lines:
        if line.startswith("CRYST1"):
            return tuple(float(line[i:i + 9]) for i in (6, 15, 24))
        # CHARMM-GUI pure-bilayer archive PDBs may omit CRYST1 while providing
        # the exact periodic dimensions in this REMARK.
        match = re.search(r"System Size:\s*([0-9.]+)\s*X\s*([0-9.]+)\s*X\s*([0-9.]+)", line, re.I)
        if match:
            return tuple(float(match.group(i)) for i in (1, 2, 3))
    raise RuntimeError("PDB has neither CRYST1 nor an explicit CHARMM-GUI System Size REMARK; refusing to guess periodic dimensions")


def format_atom(serial: int, name: str, residue: str, chain: str, resno: int,
                p: tuple[float, float, float], element: str = "C") -> str:
    # Keep standard fixed-width PDB columns and preserve all heavy coordinates.
    return (f"ATOM  {serial % 100000:5d} {name:>4.4s} {residue:>3.3s} {chain[:1]:1s}"
            f"{resno % 10000:4d}    {p[0]:8.3f}{p[1]:8.3f}{p[2]:8.3f}"
            f"  1.00  0.00          {element:>2.2s}  \n")


def find_bilayer_pdb(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        members = [m for m in tf.getmembers() if m.isfile() and Path(m.name).suffix.lower() in (".pdb", ".crd", ".psf", ".rtf", ".str")]
        if not members:
            raise RuntimeError("Official POPC bilayer archive contains no PDB/CRD coordinates")
        # Extract only candidate coordinate files; reject absolute/parent paths.
        for member in members:
            p = Path(member.name)
            if p.is_absolute() or ".." in p.parts:
                raise RuntimeError("Unsafe archive member path")
            tf.extract(member, dest, filter="data")
    candidates = list(dest.rglob("*.pdb")) + list(dest.rglob("*.crd"))
    scored = []
    for path in candidates:
        try:
            lines = path.read_text(errors="replace").splitlines()
            popcs = {resid(a) for a in parse_atoms(lines, {"POPC"})}
            if popcs:
                scored.append((len(popcs), path))
        except OSError:
            continue
    if not scored:
        raise RuntimeError("Could not find POPC coordinates in the official pure-bilayer archive")
    # The archive offers 128- and 256-lipid boxes. Choose the 128-lipid box so
    # explicit solvent remains under the benchmark's 100,000-atom cap.
    return min(scored, key=lambda item: item[0])[1]


def parse_psf_popc_graph(path: Path):
    lines = path.read_text(errors="replace").splitlines()
    natom_at = next((i for i, line in enumerate(lines) if "!NATOM" in line), None)
    nbond_at = next((i for i, line in enumerate(lines) if "!NBOND" in line), None)
    if natom_at is None or nbond_at is None:
        raise RuntimeError(f"PSF lacks NATOM or NBOND sections: {path}")
    natom = int(lines[natom_at].split()[0])
    atoms = {}
    for line in lines[natom_at + 1:natom_at + 1 + natom]:
        cols = line.split()
        if len(cols) < 8:
            continue
        idx = int(cols[0]); seg, resid0, resn, name, typ = cols[1:6]
        if resn.upper() == "POPC":
            # Legacy CHARMM PSF stores numeric type IDs. Its mass is explicit;
            # use it to color the molecular graph, and cross-check atom names.
            mass = float(cols[7])
            elements = [("H", 1.008), ("C", 12.011), ("N", 14.007),
                        ("O", 15.999), ("P", 30.974), ("S", 32.06)]
            element, reference = min(elements, key=lambda item: abs(item[1] - mass))
            if abs(reference - mass) > 0.1 or not name.upper().startswith(element):
                raise RuntimeError(f"Unrecognized PSF element/mass: {name} {mass}")
            atoms[idx] = {"seg": seg, "resid": resid0, "name": name, "type": element}
    nbond = int(lines[nbond_at].split()[0])
    nums = []
    for line in lines[nbond_at + 1:]:
        if "!" in line:
            break
        nums.extend(int(x) for x in line.split())
    if len(nums) < 2 * nbond:
        raise RuntimeError("PSF NBOND data ended before all bonds were read")
    edges = set()
    for i in range(nbond):
        a, b = nums[2 * i], nums[2 * i + 1]
        if a in atoms and b in atoms:
            edges.add(tuple(sorted((atoms[a]["name"], atoms[b]["name"]))))
    residues = defaultdict(list)
    for atom in atoms.values():
        residues[(atom["seg"], atom["resid"])].append(atom)
    first = next(iter(residues.values()), None)
    if not first:
        raise RuntimeError("No POPC residue found in PSF")
    names = [a["name"] for a in first]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate atom names in PSF POPC residue")
    graph_edges = {e for e in edges if e[0] in names and e[1] in names}
    types = {a["name"]: a["type"] for a in first}
    return {n: types[n] for n in names}, graph_edges, {"psf_popc_residue_count": len(residues), "psf_atoms_per_popc": len(names)}


def parse_rtp_residue_graph(ff_dir: Path, residue: str):
    hits = []
    for path in ff_dir.rglob("*.rtp"):
        lines = path.read_text(errors="replace").splitlines()
        active = False; section = None; atoms = {}; edges = set()
        for line in lines:
            clean = line.split(";", 1)[0].strip()
            if not clean or clean.startswith(("#", "!")):
                continue
            if clean.startswith("[") and clean.endswith("]"):
                name = clean[1:-1].strip().upper()
                if name == residue.upper() and not active:
                    active = True; section = None; continue
                if active and name in {"ATOMS", "BONDS"}:
                    section = name.lower(); continue
                if active:
                    break
                continue
            if not active or section is None:
                continue
            cols = clean.split()
            if section == "atoms" and len(cols) >= 3:
                atoms[cols[0]] = cols[1]
            elif section == "bonds" and len(cols) >= 2:
                edges.add(tuple(sorted((cols[0], cols[1]))))
        if atoms:
            hits.append((path, atoms, edges))
    if len(hits) != 1:
        raise RuntimeError(f"Expected one {residue} residue graph in CHARMM36 RTP files, found {len(hits)}")
    return hits[0]


def atom_element(atom_type: str) -> str:
    # CHARMM lipid atom types begin with the corresponding element symbol.
    first = atom_type.strip().upper()[:1]
    if first not in {"C", "H", "N", "O", "P", "S"}:
        raise RuntimeError(f"Cannot infer element from force-field atom type {atom_type!r}")
    return first


def graph_isomorphism(old_types: dict, old_edges: set, new_types: dict, new_edges: set) -> dict:
    """Deterministic colored-graph isomorphism for old CHARMM27 to C36 POPC."""
    old_nodes, new_nodes = set(old_types), set(new_types)
    if len(old_nodes) != len(new_nodes) or len(old_edges) != len(new_edges):
        raise RuntimeError(f"POPC graph sizes differ: archive={len(old_nodes)} atoms/{len(old_edges)} bonds, C36={len(new_nodes)} atoms/{len(new_edges)} bonds")
    old_adj = {n: set() for n in old_nodes}; new_adj = {n: set() for n in new_nodes}
    for a, b in old_edges: old_adj[a].add(b); old_adj[b].add(a)
    for a, b in new_edges: new_adj[a].add(b); new_adj[b].add(a)
    old_elem = {n: atom_element(t) for n, t in old_types.items()}
    new_elem = {n: atom_element(t) for n, t in new_types.items()}
    def initial(nodes, adj, elems):
        return {n: (elems[n], len(adj[n]), tuple(sorted(elems[x] for x in adj[n]))) for n in nodes}
    old_c, new_c = initial(old_nodes, old_adj, old_elem), initial(new_nodes, new_adj, new_elem)
    for _ in range(12):
        old_sig = {n: (old_c[n], tuple(sorted(old_c[x] for x in old_adj[n]))) for n in old_nodes}
        new_sig = {n: (new_c[n], tuple(sorted(new_c[x] for x in new_adj[n]))) for n in new_nodes}
        palette = {sig: i for i, sig in enumerate(sorted(set(old_sig.values()) | set(new_sig.values()), key=repr))}
        next_old = {n: palette[old_sig[n]] for n in old_nodes}
        next_new = {n: palette[new_sig[n]] for n in new_nodes}
        old_c, new_c = next_old, next_new
    if sorted(old_c.values()) != sorted(new_c.values()):
        raise RuntimeError("CHARMM27 POPC and C36 POPC atom graph colors do not match")
    candidates = {n: [m for m in sorted(new_nodes) if new_c[m] == old_c[n]] for n in old_nodes}
    order = sorted(old_nodes, key=lambda n: (len(candidates[n]), -len(old_adj[n]), n))
    mapping = {}
    used = set()
    def search():
        if len(mapping) == len(old_nodes):
            return True
        remaining = [n for n in old_nodes if n not in mapping]
        old = min(remaining, key=lambda n: (sum(m not in used for m in candidates[n]), -len(old_adj[n]), n))
        for new in candidates[old]:
            if new in used:
                continue
            if any(((prior in old_adj[old]) != (mapped in new_adj[new])) for prior, mapped in mapping.items()):
                continue
            mapping[old] = new; used.add(new)
            if search(): return True
            del mapping[old]; used.remove(new)
        return False
    if not search():
        raise RuntimeError("No atom-name mapping satisfies the CHARMM27→C36 POPC bond-graph isomorphism")
    return mapping


def rename_archive_popc(lines: list[str], old_types: dict, mapping: dict) -> tuple[list[str], int]:
    expected = set(old_types)
    groups = defaultdict(list)
    for i, line in enumerate(lines):
        if line.startswith(("ATOM  ", "HETATM")) and resname(line) == "POPC":
            groups[resid(line)].append((i, line))
    if not groups:
        raise RuntimeError("No POPC coordinates found for topology atom-name translation")
    renamed = list(lines)
    for rid, atoms in groups.items():
        names = [atom_name(line) for _, line in atoms]
        if len(names) != len(set(names)) or set(names) != expected:
            missing = sorted(expected - set(names)); extra = sorted(set(names) - expected)
            raise RuntimeError(f"PDB/PSF POPC atom inventory mismatch at {rid}: missing={missing[:8]}, extra={extra[:8]}")
        for i, line in atoms:
            newname = mapping[atom_name(line)]
            if len(newname) > 4:
                raise RuntimeError(f"C36 POPC atom name too long for PDB field: {newname}")
            renamed[i] = line[:12] + f"{newname:>4s}" + line[16:]
    return renamed, len(groups)


def alias_sapi24_rtp(ff_dir: Path, root: Path) -> dict:
    """Alias the archive PDB label SAP to the exact CHARMM residue SAPI24.

    Only the RTP section header changes; all atom types, charges, bonds, and
    parameters remain byte-identical. The before/after hash is retained.
    """
    candidates = []
    for path in ff_dir.rglob("*.rtp"):
        try:
            body = path.read_text(errors="strict")
        except UnicodeError:
            continue
        if re.search(r"(?im)^\s*\[\s*SAPI24\s*\]\s*(?:;.*)?$", body):
            candidates.append((path, body))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one SAPI24 RTP section in CHARMM36, found {len(candidates)}")
    path, body = candidates[0]
    new_body, replacements = re.subn(r"(?im)^(\s*\[\s*)SAPI24(\s*\]\s*(?:;.*)?)$", r"\1SAP\2", body, count=1)
    if replacements != 1:
        raise RuntimeError("Could not create SAPI24-to-SAP residue-name alias in the local RTP")
    before = sha256(path)
    path.write_text(new_body)
    after = sha256(path)
    return {"path": str(path.relative_to(root)), "original_sha256": before, "aliased_sha256": after,
            "change": "RTP section label [ SAPI24 ] renamed to [ SAP ]; all atom and bonded parameter records retained unchanged"}


def orient_insert(protein_atoms: list[str], ligand_atoms: list[str], bilayer_atoms: list[str], box):
    h0_ca = [xyz(a) for a in protein_atoms if atom_name(a) == "CA" and 1 <= int(a[22:26]) <= 18]
    if len(h0_ca) < 5:
        raise RuntimeError("1H0A chain A residues 1-18 do not provide enough C-alpha atoms for assumed H0 orientation")
    helix_start = [xyz(a) for a in protein_atoms if atom_name(a) == "CA" and int(a[22:26]) in range(1, 5)]
    helix_end = [xyz(a) for a in protein_atoms if atom_name(a) == "CA" and int(a[22:26]) in range(14, 19)]
    lig_center = mean([xyz(a) for a in ligand_atoms])
    prot_center = mean([xyz(a) for a in protein_atoms if atom_name(a) == "CA"])
    z_axis = unit(sub(prot_center, lig_center))  # protein body is on solvent side of bound headgroup
    h0_axis = unit(sub(mean(helix_end), mean(helix_start)))
    x_axis = unit(sub(h0_axis, scale(z_axis, dot(h0_axis, z_axis))))
    y_axis = unit(cross(z_axis, x_axis))
    x_axis = unit(cross(y_axis, z_axis))
    p_atoms = [a for a in bilayer_atoms if atom_name(a) == "P" and resname(a) == "POPC"]
    if len(p_atoms) < 20:
        raise RuntimeError("POPC bilayer lacks expected phosphate anchor atoms")
    p_z = [xyz(a)[2] for a in p_atoms]
    mid_z = (min(p_z) + max(p_z)) / 2.0
    upper_p = [xyz(a) for a in p_atoms if xyz(a)[2] > mid_z]
    upper_z = sum(p[2] for p in upper_p) / len(upper_p)
    # Model choice: crystal InsP3 binding center is placed at the upper-leaflet phosphate plane.
    target = (box[0] * 0.5, box[1] * 0.5, upper_z)
    transformed = []
    for a in protein_atoms:
        delta = sub(xyz(a), lig_center)
        new = add(target, (dot(delta, x_axis), dot(delta, y_axis), dot(delta, z_axis)))
        transformed.append(set_xyz(a, new))
    return transformed, target, mid_z, upper_z


def insert_sapi24(template_lines: list[str], bilayer_atoms: list[str], anchor: tuple[float, float, float],
                   mid_z: float, box) -> tuple[list[str], set[tuple[str, str, str]]]:
    sapi = parse_atoms(template_lines)
    if not sapi:
        raise RuntimeError("SAPI24 official coordinate template has no atoms")
    p = next((xyz(a) for a in sapi if atom_name(a) == "P"), None)
    tails = [xyz(a) for a in sapi if atom_name(a) in {"C11", "C21"}]
    heads = [xyz(a) for a in sapi if atom_name(a) in {"P", "P4", "P5"}]
    if p is None or len(tails) != 2 or not heads:
        raise RuntimeError("SAPI24 template does not contain expected P/C11/C21/P4/P5 atom-name anchors")
    tail_center = mean(tails)
    head_center = mean(heads)
    rot = rotate_to_z(sub(head_center, tail_center))
    # Select upper-leaflet POPC P closest in xy to the protein's crystallographic binding site.
    candidates = [a for a in bilayer_atoms if resname(a) == "POPC" and atom_name(a) == "P" and xyz(a)[2] > mid_z]
    chosen = min(candidates, key=lambda a: (xyz(a)[0] - anchor[0]) ** 2 + (xyz(a)[1] - anchor[1]) ** 2)
    oldid = resid(chosen)
    p_target = xyz(chosen)
    # Translate after rotating so the glycerol phosphate occupies the chosen POPC anchor.
    sapi_out = []
    for i, a in enumerate(sapi, 1):
        pnew = add(p_target, matvec(rot, sub(xyz(a), p)))
        # Preserve the CHARMM-GUI residue-name field verbatim (PDB has a
        # fixed-width name field); retain SAPI24 explicitly in the manifest.
        sapi_id = a[:21] + "B" + f"{9001:4d}" + a[26:]
        sapi_out.append(set_xyz(sapi_id, pnew))
    return sapi_out, {oldid}


def write_mdp(path: Path, stage: str) -> None:
    if stage == "min":
        data = """integrator = steep
emtol = 1000
emstep = 0.01
nsteps = 5000
nstlist = 20
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb = 1.2
rvdw = 1.2
rvdw-switch = 1.0
vdw-modifier = Force-switch
constraints = h-bonds
constraint-algorithm = lincs
define = -DUSE_OLD_C36
"""
    elif stage == "nvt":
        data = f"""integrator = md
dt = {DT_PS:.3f}
nsteps = 5000
continuation = no
constraint-algorithm = lincs
constraints = h-bonds
lincs-order = 4
lincs-iter = 1
cutoff-scheme = Verlet
nstlist = 20
coulombtype = PME
rcoulomb = 1.2
rvdw = 1.2
rvdw-switch = 1.0
vdw-modifier = Force-switch
DispCorr = no
tcoupl = V-rescale
tc-grps = System
tau-t = 1.0
ref-t = 303.15
annealing = single
annealing-npoints = 2
annealing-time = 0 10
annealing-temp = 100 303.15
pcoupl = no
gen-vel = yes
gen-temp = 100
gen-seed = 1357911
nstxout = 0
nstvout = 0
nstfout = 0
nstenergy = 100
nstlog = 1000
nstxout-compressed = 1000
define = -DPOSRES -DUSE_OLD_C36
"""
    elif stage in {"npt_restraint", "npt_release"}:
        steps = 5000 if stage == "npt_restraint" else 40000
        posres = stage == "npt_restraint"
        continuation = "yes"
        genvel = "no"
        data = f"""integrator = md
dt = {DT_PS:.3f}
nsteps = {steps}
continuation = {continuation}
constraint-algorithm = lincs
constraints = h-bonds
lincs-order = 4
lincs-iter = 1
cutoff-scheme = Verlet
nstlist = 20
coulombtype = PME
rcoulomb = 1.2
rvdw = 1.2
rvdw-switch = 1.0
vdw-modifier = Force-switch
DispCorr = no
tcoupl = V-rescale
tc-grps = System
tau-t = 1.0
ref-t = 303.15
pcoupl = C-rescale
pcoupltype = semiisotropic
tau-p = 5.0
ref-p = 1.0 1.0
compressibility = 4.5e-5 4.5e-5
refcoord-scaling = com
gen-vel = {genvel}
gen-temp = 303.15
gen-seed = 1357911
nstxout = 0
nstvout = 0
nstfout = 0
nstenergy = 100
nstlog = 1000
nstxout-compressed = 1000
define = {'-DPOSRES ' if posres else ''}-DUSE_OLD_C36
"""
    else:
        raise ValueError(f"Unknown MDP stage: {stage}")
    path.write_text(data)


def run(cmd: list[str], cwd: Path, report: dict, stdin: str | None = None,
        extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    start = time.monotonic()
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    if extra_env:
        env.update(extra_env)
    cp = subprocess.run(cmd, cwd=cwd, input=stdin, text=True, capture_output=True, env=env, timeout=MAX_SECONDS)
    elapsed = time.monotonic() - start
    entry = {"command": cmd, "elapsed_seconds": round(elapsed, 3), "returncode": cp.returncode,
             "stdin": stdin, "stdout": cp.stdout[-12000:], "stderr": cp.stderr[-12000:]}
    report["commands"].append(entry)
    report["elapsed_seconds"] = round(time.monotonic() - report["started_monotonic"], 3)
    if tree_bytes(Path(report.get("attempt_root", cwd))) > MAX_BYTES:
        raise RuntimeError("Aggregate output cap of 1 GiB reached")
    if report["elapsed_seconds"] >= MAX_SECONDS:
        raise RuntimeError("30-minute attempt wall limit reached")
    return cp


def write_report(root: Path, report: dict) -> None:
    if "started_monotonic" in report:
        report["elapsed_seconds"] = round(time.monotonic() - report["started_monotonic"], 3)
    report.pop("started_monotonic", None)
    report["output_bytes"] = tree_bytes(root)
    report["output_files"] = [record_file(p, root) for p in sorted(root.rglob("*")) if p.is_file() and p.name not in {"validation.json", "validation.md"}]
    lines = [
        "# ENTH inserted-state bounded validation",
        "",
        f"Preparation: **{report.get('preparation_status')}**. Execution: **{report.get('execution_status')}**. Analysis: **{report.get('analysis_status')}**.",
        "",
        report.get("summary", "No summary produced."),
        "",
        "## Reconstruction choices",
        "",
        "- Protein: chain A of rat epsin ENTH PDB 1H0A; the bound Ins(1,4,5)P3 ligand was used only to define the modeled membrane-contact anchor and removed from the final system.",
        "- Assumed H0: chain A residues 1–18; exact Figure 4 residue mapping was not supplied, so this is an explicit structural convention, not confirmed paper mapping.",
        "- Membrane: public CHARMM-GUI 128-lipid POPC pure-bilayer archive, the smaller archived size selected to meet the 100,000-atom cap after solvation. The protein was oriented by the vector from protein C-alpha centroid to crystallographic InsP3 centroid; the ligand centroid was aligned to the upper-leaflet POPC phosphate plane. This is a reproducible geometric reconstruction, not the authors' original placement.",
        "- PIP2: one CHARMM-GUI SAPI24 molecule replaces the upper-leaflet POPC nearest the crystallographic ligand anchor. SAPI24 is the CHARMM lipid model protonated on P4 (formal residue charge -4). The paper does not report this protonation choice.",
        "- Salt: 0.15 mM KCl is passed literally to GROMACS. At this system size it is below a single neutral KCl pair; only charge-neutralizing K+ counterions may be present. This does not emulate 0.15 M.",
        "- Only inserted-state setup/validation is attempted. Pulling and adsorbed/solvent states are outside this experiment.",
        "",
        "## Commands and outputs",
        "",
        f"Elapsed: {report.get('elapsed_seconds')} s; aggregate output: {report.get('output_bytes')} bytes; atom count: {report.get('atom_count')}; MD step cap: {MAX_STEPS} at {DT_PS} ps (100 ps).",
        "",
        "See `validation.json` for downloaded/input hashes, exact commands, stdout/stderr, and per-file output hashes.",
        "",
        "## Interpretation",
        "",
        report.get("interpretation", "No trajectory interpretation was made."),
        "",
        "This local 100-ps validation cannot reproduce 70-ns equilibration plus 150-ns production, establish independent-seed uncertainty, or support a biological agreement score.",
    ]
    (root / "validation.md").write_text("\n".join(lines) + "\n")
    report["artifact_hashes"] = {entry["path"]: entry["sha256"] for entry in report["output_files"]}
    report["artifact_hashes"]["validation.md"] = sha256(root / "validation.md")
    report["artifact_hashes_note"] = "The JSON report's own SHA256 is omitted to avoid a self-referential hash; compute it after the final write."
    (root / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true", help="Prepare and preflight, but do not run MD")
    args = parser.parse_args()
    root = args.workdir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    inputs = root / "inputs"
    run_dir = root / "run"
    inputs.mkdir(exist_ok=True)
    run_dir.mkdir(exist_ok=True)
    report = {"benchmark": "epsin-enth-md-v1", "model": "gpt-6-luna (delegated preparation; runtime label per task)",
              "attempt_root": str(root),
              "started_monotonic": time.monotonic(), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "bounds": {"wall_seconds": MAX_SECONDS, "cpu_threads": 2, "memory_mib": 4096, "max_atoms": MAX_ATOMS,
                         "max_md_steps": MAX_STEPS, "dt_ps": DT_PS, "max_output_bytes": MAX_BYTES, "gpu": False,
                         "cloud_spend_usd": 0, "concurrent_simulations": 1},
              "scientific_agreement_status": "not_assessed", "preparation_status": "running", "execution_status": "not_started",
              "analysis_status": "not_started", "sources": SOURCES, "inputs": [], "commands": []}
    try:
        for key, url in SOURCES.items():
            dest = inputs / ("c36.tgz" if key == "c36_gromacs" else "popc_bilayer.tar.gz" if key == "popc_bilayer" else key + ".pdb")
            if not dest.exists():
                fetch(url, dest)
            if tree_bytes(root) > MAX_BYTES:
                raise RuntimeError("Aggregate input download size exceeded 1 GiB")
            report["inputs"].append({"source": key, "url": url, **record_file(dest, root)})
        ff_archive = inputs / "c36.tgz"
        ff_root = inputs / "forcefield"
        ff_root.mkdir(exist_ok=True)
        with tarfile.open(ff_archive, "r:gz") as tf:
            tf.extractall(ff_root, filter="data")
        ff_dirs = [p for p in ff_root.rglob("forcefield.itp")]
        if not ff_dirs:
            raise RuntimeError("CHARMM36 tarball unpacked but no GROMACS forcefield.itp was found")
        ff_dir = ff_dirs[0].parent
        ff_name = ff_dir.name.removesuffix(".ff")
        os.environ["GMXLIB"] = str(ff_root)
        report["forcefield"] = {"name": ff_name, "directory": str(ff_dir.relative_to(root)), "release": "MacKerell CHARMM36 July 2020",
                                "protein_model_toggle": "USE_OLD_C36 enabled"}
        report["forcefield"]["sapi24_pdb_alias"] = alias_sapi24_rtp(ff_dir, root)
        version = run(["gmx", "--version"], root, report)
        report["gromacs_version_command_returncode"] = version.returncode
        report["gromacs_version_excerpt"] = version.stdout[:4000]
        if version.returncode:
            raise RuntimeError("gmx --version failed")
        bilayer_file = find_bilayer_pdb(inputs / "popc_bilayer.tar.gz", inputs / "pdb_archive")
        bilayer_lines = bilayer_file.read_text(errors="replace").splitlines()
        psf_candidates = list((inputs / "pdb_archive").rglob("*.psf"))
        psf_file = next((p for p in psf_candidates if "n128" in p.name.lower()), psf_candidates[0] if psf_candidates else None)
        if psf_file is None:
            raise RuntimeError("CHARMM-GUI POPC archive contains no PSF bond graph for old atom-name translation")
        old_types, old_edges, psf_counts = parse_psf_popc_graph(psf_file)
        rtp_file, new_types, new_edges = parse_rtp_residue_graph(ff_dir, "POPC")
        popc_name_map = graph_isomorphism(old_types, old_edges, new_types, new_edges)
        bilayer_lines, renamed_popcs = rename_archive_popc(bilayer_lines, old_types, popc_name_map)
        old_rtf = next(iter((inputs / "pdb_archive").rglob("top_all27_prot_lipid.rtf")), None)
        report["popc_atom_name_translation"] = {
            "method": "colored molecular graph isomorphism from CHARMM-GUI archived CHARMM27 PSF to the official CHARMM36 GROMACS POPC RTP; source PDB coordinates are unchanged",
            "source_psf": record_file(psf_file, root),
            "source_char27_rtf": record_file(old_rtf, root) if old_rtf else None,
            "target_c36_rtp": record_file(rtp_file, root),
            "psf_counts": psf_counts,
            "target_atom_count": len(new_types),
            "renamed_coordinate_residues": renamed_popcs,
            "atom_name_mapping": popc_name_map,
            "old_bond_count": len(old_edges), "new_bond_count": len(new_edges),
            "parameters_changed": False
        }
        bilayer_atoms = parse_atoms(bilayer_lines, {"POPC"})
        popc_template_atoms = parse_atoms((inputs / "popc_template.pdb").read_text(errors="replace").splitlines())
        sapi_lines = (inputs / "sapi24_template.pdb").read_text(errors="replace").splitlines()
        sapi_template_atoms = parse_atoms(sapi_lines)
        is_hydrogen = lambda a: atom_name(a).upper().startswith("H") or a[76:78].strip().upper() == "H"
        popc_h_counts = defaultdict(int)
        for a in bilayer_atoms:
            if is_hydrogen(a): popc_h_counts[resid(a)] += 1
        if not popc_h_counts or any(count == 0 for count in popc_h_counts.values()):
            raise RuntimeError("POPC bilayer coordinates do not contain complete lipid hydrogens; this CHARMM release has no safe lipid HDB reconstruction path")
        if not any(is_hydrogen(a) for a in sapi_template_atoms):
            raise RuntimeError("SAPI24 coordinate template has no hydrogens; no custom hydrogen coordinates will be invented")
        report["lipid_template_atom_evidence"] = {
            "popc_coordinate_template": {"atoms": len(popc_template_atoms), "hydrogens": sum(is_hydrogen(a) for a in popc_template_atoms),
                                         "sha256": sha256(inputs / "popc_template.pdb")},
            "popc_bilayer_coordinate_atoms": len(bilayer_atoms),
            "popc_bilayer_hydrogens": sum(is_hydrogen(a) for a in bilayer_atoms),
            "sapi24_coordinate_template": {"atoms": len(sapi_template_atoms), "hydrogens": sum(is_hydrogen(a) for a in sapi_template_atoms),
                                           "pdb_resname": resname(sapi_template_atoms[0]), "sha256": sha256(inputs / "sapi24_template.pdb")},
            "hydrogen_policy": "Preserve supplied all-atom POPC and SAPI24 coordinates; do not pass -ignh. Protein hydrogens absent from 1H0A are built from CHARMM amino-acid HDB."
        }
        box = pdb_box(bilayer_lines)
        # CHARMM-GUI archive coordinates can be centered about the origin. Move
        # the bilayer into its declared CRYST1 cell before placing the protein.
        all_xyz = [xyz(a) for a in bilayer_atoms]
        offsets = tuple(box[i] / 2 - (min(p[i] for p in all_xyz) + max(p[i] for p in all_xyz)) / 2 for i in range(3))
        bilayer_atoms = [set_xyz(a, add(xyz(a), offsets)) for a in bilayer_atoms]
        protein_lines = (inputs / "pdb_1h0a.pdb").read_text(errors="replace").splitlines()
        protein_atoms = [a for a in parse_atoms(protein_lines) if a.startswith("ATOM  ") and a[21:22] == "A"]
        ligand_atoms = [a for a in parse_atoms(protein_lines) if a.startswith("HETATM") and resname(a) == "I3P" and a[21:22] == "A"]
        if not protein_atoms or not ligand_atoms:
            raise RuntimeError("PDB 1H0A did not contain chain A protein and I3P ligand needed for anchor")
        oriented, anchor, mid_z, top_z = orient_insert(protein_atoms, ligand_atoms, bilayer_atoms, box)
        sapi_atoms, replaced = insert_sapi24(sapi_lines, bilayer_atoms, anchor, mid_z, box)
        # Remove the replaced lipid and any POPC molecule with a heavy atom within 3 Å of protein.
        protein_xyz = [xyz(a) for a in oriented if atom_name(a)[0] not in "HD"]
        xclear = min(min(p[0] for p in protein_xyz), box[0] - max(p[0] for p in protein_xyz))
        yclear = min(min(p[1] for p in protein_xyz), box[1] - max(p[1] for p in protein_xyz))
        # Image separation is the cell width minus the molecular span, not
        # distance to a cell face (which would impose twice the needed gap).
        image_clearance = min(box[i] - (max(p[i] for p in protein_xyz) - min(p[i] for p in protein_xyz))
                              for i in (0, 1))
        if image_clearance < 12.0:
            raise RuntimeError(f"Protein is too close to a periodic xy image: {image_clearance:.2f} A < 12 A")
        cell = 5.0
        grid = defaultdict(list)
        for p in protein_xyz:
            grid[tuple(math.floor(v / cell) for v in p)].append(p)
        removed = set(replaced)
        lipid_by_id = defaultdict(list)
        for a in bilayer_atoms:
            lipid_by_id[resid(a)].append(a)
        for rid, atoms in lipid_by_id.items():
            for a in atoms:
                ax, ay, az = xyz(a)
                gx, gy, gz = (math.floor(v / cell) for v in (ax, ay, az))
                nearby = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                          for q in grid.get((gx + dx, gy + dy, gz + dz), [])]
                if any((ax-q[0])**2 + (ay-q[1])**2 + (az-q[2])**2 < 3.0**2 for q in nearby):
                    removed.add(rid)
                    break
        kept = [a for a in bilayer_atoms if resid(a) not in removed]
        lipid_centers = {rid: mean([xyz(a) for a in atoms if atom_name(a) == "P"]) for rid, atoms in lipid_by_id.items()}
        upper_start = sum(1 for p in lipid_centers.values() if p[2] > mid_z)
        lower_start = len(lipid_centers) - upper_start
        upper_retained = sum(1 for rid, p in lipid_centers.items() if p[2] > mid_z and rid not in removed)
        lower_retained = sum(1 for rid, p in lipid_centers.items() if p[2] <= mid_z and rid not in removed)
        # Re-number lipid records to avoid duplicate residue ids with inserted PIP2; preserve residue labels.
        merged = ["REMARK 900 Reconstructed ENTH + POPC bilayer; not original CHARMM-GUI job\n"]
        cryst = next((x + "\n" for x in bilayer_lines if x.startswith("CRYST1")), None)
        if cryst is None:
            # Pure-bilayer archive supplies an orthorhombic System Size REMARK
            # rather than CRYST1. Carry those exact dimensions into the merged PDB.
            cryst = (f"CRYST1{box[0]:9.3f}{box[1]:9.3f}{box[2]:9.3f}"
                     f"{90.0:7.2f}{90.0:7.2f}{90.0:7.2f} P 1           1\n")
        merged.append(cryst)
        serial = 1
        for a in kept:
            merged.append(a[:6] + f"{serial % 100000:5d}" + a[11:] + "\n"); serial += 1
        for a in sapi_atoms:
            merged.append(a[:6] + f"{serial % 100000:5d}" + a[11:].rstrip("\r\n") + "\n"); serial += 1
        for a in oriented:
            merged.append(a[:6] + f"{serial % 100000:5d}" + a[11:] + "\n"); serial += 1
        merged.extend(["TER\n", "END\n"])
        complex_pdb = run_dir / "inserted_complex.pdb"
        complex_pdb.write_text("".join(merged))
        report["reconstruction"] = {"bilayer_archive_structure": str(bilayer_file.relative_to(root)),
                                    "box_angstrom": box, "protein_minimum_xy_image_clearance_angstrom": image_clearance,
                                    "popc_start_count": len(lipid_by_id),
                                    "popc_removed_for_protein_and_pip2": len(removed), "popc_retained": len(lipid_by_id) - len(removed),
                                    "leaflet_counts": {"upper_popc_start": upper_start, "lower_popc_start": lower_start,
                                                       "upper_popc_retained": upper_retained, "lower_popc_retained": lower_retained,
                                                       "upper_pip2_inserted": 1},
                                    "paper_composition_deviation": "Scaled to 128 total archived POPC molecules due the 100,000 atom cap; additional POPCs were removed near the protein to avoid overlaps. The paper reports 99 POPC plus one PIP2 above and 100 POPC below.",
                                    "pip2": "one CHARMM-GUI SAPI24, P4-protonated, net charge -4",
                                    "pip2_pdb_resname": resname(parse_atoms(sapi_lines)[0]),
                                    "protein_chain": "rat epsin ENTH 1H0A chain A, residues modeled 1-158",
                                    "assumed_h0": "chain A residues 1-18; paper-specific residue definition unavailable",
                                    "anchor_angstrom": anchor, "upper_headgroup_z_angstrom": top_z,
                                    "placement_assumption": "align crystallographic I3P centroid to upper-leaflet phosphate plane; orient protein centroid away from membrane along I3P-to-protein vector; replace nearest upper-leaflet POPC by SAPI24",
                                    "pdb": record_file(complex_pdb, root)}
        pdb2gmx_cmd = ["gmx", "pdb2gmx", "-f", str(complex_pdb), "-o", "processed.gro", "-p", "topol.top",
                       "-ff", ff_name, "-water", "tip3p"]
        pdb2gmx = run(pdb2gmx_cmd, run_dir, report, extra_env={"GMXLIB": str(ff_root)})
        if pdb2gmx.returncode != 0 or not (run_dir / "topol.top").exists():
            report["preparation_status"] = "blocked_forcefield_topology_conversion"
            report["summary"] = "Public coordinates and CHARMM36 files were acquired and a membrane-oriented PDB reconstruction was written, but GROMACS could not generate a complete topology for the mixed protein/POPC/SAPI24 structure. No simulation was started."
            report["interpretation"] = "No finite-energy, constraint, temperature, pressure/volume, or membrane-integrity checks are available because topology preparation failed."
            report["blocking_evidence"] = {"pdb2gmx_returncode": pdb2gmx.returncode, "stderr": pdb2gmx.stderr[-12000:]}
            report["preparation_status"] = "blocked_forcefield_topology_conversion"
            write_report(root, report)
            return 2
        report["preparation_status"] = "topology_generated"
        report["position_restraint_files"] = [record_file(p, root) for p in sorted(run_dir.glob("posre*.itp"))]
        if args.prepare_only:
            report["summary"] = "A reconstructed ENTH/POPC/SAPI24 coordinate set and GROMACS topology were generated. Solvation, MD, and analysis were intentionally skipped by --prepare-only."
            report["preparation_status"] = "prepared"
            write_report(root, report)
            return 0
        # Place the whole bilayer system in a 1.2 nm solvent buffer and add explicit TIP3P waters.
        # Preserve the pre-equilibrated bilayer's xy cell; extend only z to add
        # 1.2 nm solvent padding on each side, then center the assembled complex.
        cp = run(["gmx", "editconf", "-f", "processed.gro", "-o", "boxed.gro", "-c", "-box",
                  f"{box[0]/10:.5f}", f"{box[1]/10:.5f}", f"{box[2]/10+2.4:.5f}"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx editconf failed")
        cp = run(["gmx", "solvate", "-cp", "boxed.gro", "-cs", "spc216.gro", "-o", "solv.gro", "-p", "topol.top"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx solvate failed")
        n_atoms = sum(1 for line in (run_dir / "solv.gro").read_text().splitlines()[2:-1])
        report["atom_count"] = n_atoms
        if n_atoms > MAX_ATOMS:
            raise RuntimeError(f"Atom cap exceeded before ionization: {n_atoms} > {MAX_ATOMS}")
        em_mdp = run_dir / "em.mdp"; write_mdp(em_mdp, "min")
        cp = run(["gmx", "grompp", "-f", "em.mdp", "-c", "solv.gro", "-p", "topol.top", "-o", "ions.tpr"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx grompp for ion placement failed")
        # Literal published value. In this finite box, expected neutral KCl pairs < 1; neutralization adds counterions.
        cp = run(["gmx", "genion", "-s", "ions.tpr", "-o", "ions.gro", "-p", "topol.top", "-pname", "K", "-nname", "CL",
                  "-neutral", "-conc", "0.00015"], run_dir, report, stdin="SOL\n")
        if cp.returncode: raise RuntimeError("gmx genion failed")
        em_tpr = run_dir / "em.tpr"
        cp = run(["gmx", "grompp", "-f", "em.mdp", "-c", "ions.gro", "-p", "topol.top", "-o", "em.tpr"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx grompp for minimization failed")
        cp = run(["gmx", "mdrun", "-s", "em.tpr", "-deffnm", "em", "-ntmpi", "1", "-ntomp", "2", "-pin", "off", "-nb", "cpu", "-pme", "cpu", "-bonded", "cpu", "-maxh", "0.15"], run_dir, report)
        if cp.returncode: raise RuntimeError("energy minimization failed")
        nvt_mdp = run_dir / "nvt.mdp"; write_mdp(nvt_mdp, "nvt")
        cp = run(["gmx", "grompp", "-f", "nvt.mdp", "-c", "em.gro", "-r", "em.gro", "-p", "topol.top", "-o", "nvt.tpr"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx grompp for gradual restrained NVT warmup failed")
        cp = run(["gmx", "mdrun", "-s", "nvt.tpr", "-deffnm", "nvt", "-ntmpi", "1", "-ntomp", "2", "-pin", "off", "-nb", "cpu", "-pme", "cpu", "-bonded", "cpu", "-maxh", "0.10"], run_dir, report)
        if cp.returncode: raise RuntimeError("restrained NVT warmup failed")
        rest_mdp = run_dir / "npt_restraint.mdp"; write_mdp(rest_mdp, "npt_restraint")
        cp = run(["gmx", "grompp", "-f", "npt_restraint.mdp", "-c", "nvt.gro", "-r", "nvt.gro", "-t", "nvt.cpt", "-p", "topol.top", "-o", "npt_restraint.tpr"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx grompp for restrained NPT warmup failed")
        cp = run(["gmx", "mdrun", "-s", "npt_restraint.tpr", "-deffnm", "npt_restraint", "-ntmpi", "1", "-ntomp", "2", "-pin", "off", "-nb", "cpu", "-pme", "cpu", "-bonded", "cpu", "-maxh", "0.10"], run_dir, report)
        if cp.returncode: raise RuntimeError("restrained NPT warmup failed")
        release_mdp = run_dir / "npt_release.mdp"; write_mdp(release_mdp, "npt_release")
        cp = run(["gmx", "grompp", "-f", "npt_release.mdp", "-c", "npt_restraint.gro", "-t", "npt_restraint.cpt", "-p", "topol.top", "-o", "npt.tpr"], run_dir, report)
        if cp.returncode: raise RuntimeError("gmx grompp for released 80-ps NPT validation failed")
        report["execution_status"] = "running"
        cp = run(["gmx", "mdrun", "-s", "npt.tpr", "-deffnm", "npt", "-ntmpi", "1", "-ntomp", "2", "-pin", "off", "-nb", "cpu", "-pme", "cpu", "-bonded", "cpu", "-maxh", "0.35"], run_dir, report)
        if cp.returncode: raise RuntimeError("100-ps NPT validation mdrun failed")
        report["execution_status"] = "completed"
        energy = run(["gmx", "energy", "-f", "npt.edr", "-o", "energy.xvg"], run_dir, report,
                     stdin="Potential\nTemperature\nPressure\nVolume\n0\n")
        constraint_text = (run_dir / "npt.log").read_text(errors="replace") if (run_dir / "npt.log").exists() else ""
        lincs_warnings = sum(1 for line in constraint_text.splitlines() if "LINCS WARNING" in line or "constraint error" in line.lower())
        xvg_rows = []
        if (run_dir / "energy.xvg").exists():
            for line in (run_dir / "energy.xvg").read_text(errors="replace").splitlines():
                if not line.strip() or line.lstrip().startswith(("#", "@")): continue
                try:
                    row = [float(x) for x in line.split()]
                    if len(row) >= 5: xvg_rows.append(row)
                except ValueError: pass
        energy_finite = bool(xvg_rows) and all(math.isfinite(x) for row in xvg_rows for x in row)
        energy_summary = {}
        if xvg_rows:
            names = ["time_ps", "potential_kj_mol", "temperature_K", "pressure_bar", "volume_nm3"]
            for i, name in enumerate(names):
                values = [r[i] for r in xvg_rows]
                energy_summary[name] = {"mean": sum(values) / len(values), "first": values[0], "last": values[-1],
                                        "min": min(values), "max": max(values)}
        frame = run(["gmx", "trjconv", "-s", "npt.tpr", "-f", "npt.xtc", "-o", "final.gro", "-dump", "100"],
                    run_dir, report, stdin="System\n")
        leaflet = {"status": "unavailable"}
        final = run_dir / "final.gro"
        if frame.returncode == 0 and final.exists():
            glines = final.read_text(errors="replace").splitlines()
            coords = []
            for line in glines[2:-1]:
                try:
                    rnm = line[5:10].strip().upper(); anm = line[10:15].strip()
                    p = (float(line[20:28]) * 10, float(line[28:36]) * 10, float(line[36:44]) * 10)
                    if anm == "P" and (rnm == "POPC" or rnm.startswith("SAP") or rnm == "S24"): coords.append((rnm, p))
                except (ValueError, IndexError): pass
            z_vals = [p[2] for _, p in coords]
            z0 = (min(z_vals) + max(z_vals)) / 2 if z_vals else 0.0
            upper = [p[2] for _, p in coords if p[2] > z0]
            lower = [p[2] for _, p in coords if p[2] < z0]
            sep = abs(sum(upper) / len(upper) - sum(lower) / len(lower)) if upper and lower else None
            leaflet = {"phosphate_atoms": len(coords), "upper_leaflet_phosphates": len(upper),
                       "lower_leaflet_phosphates": len(lower), "mean_leaflet_separation_angstrom": sep,
                       "geometric_check": bool(sep is not None and 10.0 < sep < 80.0 and len(upper) >= 3 and len(lower) >= 3)}
        report["analysis"] = {"energy_extraction_returncode": energy.returncode, "finite_energy_series": energy_finite,
                              "energy_summary": energy_summary,
                              "energy_sample_count": len(xvg_rows), "lincs_warning_count": lincs_warnings,
                              "membrane_leaflet_check": leaflet,
                              "npt_log_contains_fatal": "Fatal error" in constraint_text}
        analysis_ok = energy.returncode == 0 and energy_finite and lincs_warnings == 0 and leaflet.get("geometric_check", False)
        report["analysis_status"] = "basic_physical_checks_passed" if analysis_ok else "physical_checks_failed_or_incomplete"
        report["summary"] = "The reconstructed mixed system completed a ≤100-ps bounded NPT smoke trajectory. Basic finite-energy, LINCS-log, and leaflet-geometry checks were " + ("satisfactory." if analysis_ok else "not all satisfactory; inspect validation.json and the raw logs.")
        report["interpretation"] = "This local reconstructed-system run validates only basic workflow and short-run physical behavior if checks pass. It does not reproduce Figure 4 and cannot establish biological agreement. H0 helicity/state comparison and independent-seed uncertainty were not assessed."
    except Exception as exc:
        if report.get("preparation_status") == "running": report["preparation_status"] = "failed_or_blocked"
        if report.get("execution_status") == "running": report["execution_status"] = "failed_or_interrupted"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["summary"] = "The attempt stopped at the first failed preflight or command; partial evidence is preserved."
        report["interpretation"] = "No scientific result is reported. Inspect the recorded command output and partial artifacts."
        write_report(root, report)
        return 1
    write_report(root, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
