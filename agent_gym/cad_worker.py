"""Executed with FreeCAD's dedicated Python environment; dimensions are mm."""
import json
from pathlib import Path
import sys
sys.path.insert(0, "/opt/agent-gym-cad/lib")
import FreeCAD as App
import Part
import Mesh
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1])
s = json.loads((folder / "spec.json").read_text())
doc = App.newDocument("Venturi")
sheet = doc.addObject("Spreadsheet::Sheet", "Dimensions")
for row, (name, value) in enumerate(s.items(), 1):
    sheet.set(f"A{row}", name)
    sheet.set(f"B{row}", f"{value} mm")
    sheet.setAlias(f"B{row}", name)
doc.recompute()

lengths = ["inlet_length_mm", "convergent_length_mm", "throat_length_mm",
           "diffuser_length_mm", "outlet_length_mm"]
radii = [("inlet_diameter_mm", "inlet_diameter_mm"),
         ("inlet_diameter_mm", "throat_diameter_mm"),
         ("throat_diameter_mm", "throat_diameter_mm"),
         ("throat_diameter_mm", "inlet_diameter_mm"),
         ("inlet_diameter_mm", "inlet_diameter_mm")]
rotation = App.Rotation(App.Vector(0, 0, 1), App.Vector(1, 0, 0))

def segments(prefix, outer=False):
    parts = []
    for i, (length, (a, b)) in enumerate(zip(lengths, radii)):
        if s[length] == 0:
            continue
        kind = "Part::Cylinder" if a == b else "Part::Cone"
        obj = doc.addObject(kind, f"{prefix}{i}")
        obj.Placement = App.Placement(App.Vector(0, 0, 0), rotation)
        obj.setExpression("Height", f"Dimensions.{length}")
        offset = " + Dimensions.wall_thickness_mm" if outer else ""
        if a == b:
            obj.setExpression("Radius", f"Dimensions.{a}/2{offset}")
        else:
            obj.setExpression("Radius1", f"Dimensions.{a}/2{offset}")
            obj.setExpression("Radius2", f"Dimensions.{b}/2{offset}")
        if i:
            obj.setExpression("Placement.Base.x", " + ".join(f"Dimensions.{n}" for n in lengths[:i]))
        parts.append(obj)
    fused = doc.addObject("Part::MultiFuse", f"{prefix}Domain")
    fused.Shapes = parts
    fused.Refine = True
    return fused

fluid = segments("Fluid")
outer = segments("Outer", True)
pipe = doc.addObject("Part::Cut", "Pipe")
pipe.Base, pipe.Tool = outer, fluid
pipe.Refine = True
doc.recompute()
for obj in [fluid, pipe]:
    if not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
        raise RuntimeError(f"{obj.Name} is not a valid single solid")
doc.saveAs(str(folder / "venturi.FCStd"))
Part.export([fluid], str(folder / "fluid.step"))
Part.export([pipe], str(folder / "pipe.step"))
Mesh.export([pipe], str(folder / "pipe.stl"))

# Standalone axial section for human review; a generated preview, not the input drawing.
x = 0
top = []
for length, (a, b) in zip(lengths, radii):
    top.append((x, s[a]/2))
    x += s[length]
    top.append((x, s[b]/2))
points = " ".join(f"{a},{-b}" for a,b in top + [(a,-b) for a,b in reversed(top)])
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 {-s["inlet_diameter_mm"]} {x+20} {s["inlet_diameter_mm"]*2}"><polygon points="{points}" fill="#dbeafe" stroke="#1e40af" stroke-width="0.5"/><path d="M 0 0 H {x}" stroke="#777" stroke-width="0.2" stroke-dasharray="2 2"/></svg>'
(folder / "profile.svg").write_text(svg)
report = {"freecad_version": ".".join(App.Version()[:3]), "units": "mm",
          "fluid_valid": True, "pipe_valid": True, "fluid_solids": 1, "pipe_solids": 1,
          "fluid_volume_mm3": fluid.Shape.Volume, "pipe_volume_mm3": pipe.Shape.Volume,
          "length_mm": fluid.Shape.BoundBox.XLength,
          "inlet_diameter_mm": s["inlet_diameter_mm"], "throat_diameter_mm": s["throat_diameter_mm"]}
(folder / "cad-report.json").write_text(json.dumps(report, indent=2))
App.closeDocument(doc.Name)
