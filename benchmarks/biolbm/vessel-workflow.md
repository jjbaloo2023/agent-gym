# Synthetic 5 L stirred-vessel test

This experimental CPU workflow tests the software path from geometry to flow results. It is not a validated water/bioreactor prediction.

## Geometry and operating conditions

- Synthetic hemispherical-bottom vessel, 160 mm internal diameter.
- 5 L internal capacity before displacement by internals.
- 3 L nominal liquid volume after analytic solids displacement; calculated liquid height 176.21 mm.
- Vessel height 275.35 mm.
- Four 45-degree pitched blades; total impeller outside diameter 59.944 mm (2.36 inches).
- 6 mm diameter shaft; impeller centre 50.8 mm above the lowest inner point.
- No baffles. Counterclockwise viewed from above; nominal speed 180 rpm, smoothly ramped over 0.05 s.
- Rigid stationary lid at the liquid level. No modeled headspace, gas, or deformable free surface.

The vessel surface STL is an open-top inner surface for inspection, not a watertight shell with wall thickness. Shaft and impeller are separate triangle surfaces. The LBM lattice comes from analytic geometry, not STL tetrahedral meshing.

## Reproduce

From the repository root after installing the solver extra:

```bash
python -m agent_gym.biolbm.bioreactor.workflow geometry --case benchmarks/biolbm/cases/bioreactor_5l/water.yaml --output outputs/vessel-geometry
python -m agent_gym.biolbm.bioreactor.workflow check --case benchmarks/biolbm/cases/bioreactor_5l/water.yaml
python -m agent_gym.biolbm.bioreactor.workflow check --case benchmarks/biolbm/cases/bioreactor_5l/viscous_demo.yaml
python -m agent_gym.biolbm.bioreactor.workflow run --case benchmarks/biolbm/cases/bioreactor_5l/viscous_demo.yaml --output outputs/vessel-demo-001
```

Use a new directory for each run. The default run uses CPU float64 with two Torch threads. `viscous_demo_gpu.yaml` selects PyTorch CUDA; this path is wired but has not been GPU-verified. Native compiled kernels remain disabled.

## Fluid choice and numerical scaling

Water settings: density 998 kg/m³, dynamic viscosity 0.001 Pa·s. At 180 rpm, impeller Reynolds number is approximately 10,758. With 3 mm cells and tip Mach 0.1, BGK tau is approximately 0.500102, outside the initial [0.51, 2] operating envelope. The workflow refuses that case; it does not silently change viscosity.

Demonstration settings: same density, dynamic viscosity 0.1 Pa·s, Re approximately 107.6, tau approximately 0.51024. This is a deliberately viscous liquid. Its numerical mapping passes the envelope, which alone is not proof of stability or accuracy.

The grid has 58 × 58 × 63 = 211,932 cells including solid padding. Time step is approximately 0.00030658 s; 1,200 steps cover 0.3679 s. After the startup ramp, the rotor has turned about one revolution. This is a short startup transient, not steady-state mixing.

## Where the logic lives

| Module | Responsibility |
| --- | --- |
| `geometry.py` | SI dimensions, volume contract, analytic vessel mask, STL/lattice export |
| `model.py` | Lettuce flow adapter, spatial Guo force, smooth moving rotor penalty |
| `workflow.py` | Configuration, unit mapping, CPU execution, guards, artifacts, plots |

Lettuce supplies D3Q19, equilibrium, BGK collision, periodic streaming, stationary full-way bounce back, and SI/lattice conversion. Our experimental extension imposes rotor velocity using a diffuse volumetric penalty and a spatial Guo force source. Force-source zeroth/first moments are unit-tested. This is not a sharp-interface validated rotating-wall implementation.

## How to assess whether it works

First check that execution completes, output fields are finite, the rotating rotor drives a nonzero tangential flow, and reported conservation errors remain within guards. Then inspect SI VTK output in ParaView, applying the fluid envelope and rotor fraction masks. Grid coordinates are SI metres.

The fluid-only mass can vary slightly because full-way solid nodes temporarily store populations. Both fluid-envelope and complete-grid mass drift are reported. Complete-grid conservation includes fictitious populations at solid nodes and is not by itself a moving-boundary mass-leakage validation.

The force-penalty torque includes shaft, hub, and blades. It is an unvalidated diagnostic, not a defensible impeller power number. Cells also contain fictitious fluid inside the diffuse rotor. At 3 mm spacing, blade thickness and shaft diameter are inadequately resolved.

Before physical conclusions: validate moving-wall/rotating-cylinder behavior and torque, demonstrate tank grid/time sensitivity, run longer and establish stationarity, then compare regime-matched experimental data. Water at the requested operating conditions needs a validated high-Re numerical/turbulence approach or substantially finer resolution.

## Recorded CPU demonstration

The 1,200-step demonstration completed in approximately 152 seconds. At 0.3679 s, maximum speed was 0.5466 m/s and the fluid-envelope mean speed was 0.02250 m/s, including diffuse rotor regions. Closed-grid mass drift was 6.86e-14 and fluid-envelope drift was 5.00e-7. These are software checks, not accuracy or mixing validation.
