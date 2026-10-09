"""Verify independent analytical volume and editing after reopening native CAD."""
import sys
sys.path.insert(0, '/opt/agent-gym-cad/lib')
import FreeCAD as App
import Part
import json
import math
from pathlib import Path
summary = json.loads(Path('/home/gym/agent-gym-runs/toolchain-check.json').read_text())
folder = Path(summary['cad']['path'])
s = json.loads((folder/'spec.json').read_text())
r, t = s['inlet_diameter_mm']/2, s['throat_diameter_mm']/2
volume = math.pi*(r*r*(s['inlet_length_mm']+s['outlet_length_mm']) + t*t*s['throat_length_mm'] + (r*r+r*t+t*t)*(s['convergent_length_mm']+s['diffuser_length_mm'])/3)
doc = App.openDocument(str(folder/'venturi.FCStd'))
assert math.isclose(doc.FluidDomain.Shape.Volume, volume, rel_tol=1e-9)
before = doc.FluidDomain.Shape.Volume
doc.Dimensions.set('B2', '16 mm')
doc.recompute(None, True, True)
for obj in doc.Objects:
    obj.touch()
doc.recompute(None, True, True)
assert doc.FluidDomain.Shape.Volume > before
assert doc.Pipe.Shape.isValid() and len(doc.Pipe.Shape.Solids) == 1
App.closeDocument(doc.Name)
print('Analytical volume and native spreadsheet edit/recompute checks passed')
