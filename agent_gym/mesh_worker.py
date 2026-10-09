"""Gmsh volume mesh from the FreeCAD fluid STEP, with named OpenFOAM patches."""
import json
from pathlib import Path
import sys
import gmsh

folder = Path(sys.argv[1])
size_m = float(sys.argv[2]) / 1000
spec = json.loads((folder / "spec.json").read_text())
length_m = sum(spec[n] for n in ["inlet_length_mm", "convergent_length_mm",
                                "throat_length_mm", "diffuser_length_mm", "outlet_length_mm"]) / 1000
gmsh.initialize()
try:
    gmsh.option.setNumber("General.NumThreads", 2)
    gmsh.option.setString("Geometry.OCCTargetUnit", "M")
    gmsh.model.occ.importShapes(str(folder / "fluid.step"))
    gmsh.model.occ.synchronize()
    volumes = gmsh.model.getEntities(3)
    if len(volumes) != 1:
        raise RuntimeError("Expected one fluid volume")
    surfaces = gmsh.model.getBoundary(volumes, oriented=False)
    patches = {"inlet": [], "outlet": [], "walls": []}
    for _, tag in surfaces:
        bounds = gmsh.model.getBoundingBox(2, tag)
        if abs(bounds[0]) < 1e-6 and abs(bounds[3]) < 1e-6:
            patches["inlet"].append(tag)
        elif abs(bounds[0] - length_m) < 1e-6 and abs(bounds[3] - length_m) < 1e-6:
            patches["outlet"].append(tag)
        else:
            patches["walls"].append(tag)
    if any(not tags for tags in patches.values()):
        raise RuntimeError("Missing inlet, outlet, or walls")
    for name, tags in patches.items():
        gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, tags), name)
    gmsh.model.setPhysicalName(3, gmsh.model.addPhysicalGroup(3, [volumes[0][1]]), "fluid")
    gmsh.option.setNumber("Mesh.MeshSizeMin", size_m)
    gmsh.option.setNumber("Mesh.MeshSizeMax", size_m)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3)
    nodes = len(gmsh.model.mesh.getNodes()[0])
    cells = sum(len(tags) for tags in gmsh.model.mesh.getElements(3)[1])
    if cells > 250000:
        raise RuntimeError("Mesh exceeds 250,000-cell local limit")
    gmsh.write(str(folder / "fluid.msh"))
    (folder / "mesh-report.json").write_text(json.dumps({
        "gmsh_version": gmsh.__version__, "units": "m", "nodes": nodes,
        "cells": cells, "size_mm": size_m*1000, "patches": patches,
        "length_m": length_m}, indent=2))
finally:
    gmsh.finalize()
