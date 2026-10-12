# Mini LBM development roadmap

Goal: build a validated Lettuce-backed lattice Boltzmann application, progressing from canonical benchmarks to stirred-tank mixing with moving geometry, scalar transport, turbulence, GPU acceleration, and practical case management.

Implementation decision: reuse Lettuce numerical logic through a pinned MIT-licensed dependency. Application-specific configuration, diagnostics, validation, and future mixing models live in this project. The original phase list remains a capability/validation checklist; it does not require reimplementing available upstream operators.

Development principle: major physics additions require quantitative validation and regression gates. All tasks below are pending.

## Execution order and scope

Keep the phase labels as topic groups. Establish backend boundaries in Phase 0 and bring up a small GPU benchmark after Phase 2/3, before large moving-geometry cases. Preserve the CPU reference. The first tank must be laminar or sufficiently resolved; industrial turbulent mixing claims require Phase 7 validation. Initially model a fully filled tank with an explicit lid boundary; a physical free surface is deferred.

## Numerical definitions

Use angular speed omega = 2*pi*RPM/60 and rotation frequency N = RPM/60. Report power P = mean(torque)*omega, P/V using the actual fluid volume, power number N_P = P/(rho*N^3*D^5), and impeller Reynolds number Re = rho*N*D^2/mu. Document torque sign and pressure reference. Standard isothermal LBM pressure is linked to density; report gauge pressure consistently.

Specify benchmark error norms, tolerances, reference sources, refinement paths, and averaging windows before claiming a gate passed. Lattice Mach limits and tau bounds are operating-envelope checks, not guarantees of stability.

## Phase 0 — Numerical contract

- [ ] Python-first implementation
- [ ] SI ↔ lattice conversion module, including pressure convention and reference density
- [ ] Versioned YAML/JSON case schema
- [ ] Field/output format independent of solver internals
- [ ] Conservation, convergence, and regression framework
- [ ] Public or synthetic geometry/test data with provenance
- [ ] Backend interface and reproducible command-line run contract
- [ ] Define quantitative benchmark thresholds before implementation

Validation gate: Case configuration and unit conversions are reproducible and dimensionally consistent.

## Phase 1 — D2Q9 reference solver

- [ ] Lattice velocities, weights, and opposite-direction mapping
- [ ] Equilibrium distributions and BGK collision
- [ ] Streaming and recovery of density and velocity
- [ ] Periodic boundaries and stationary half-way bounce-back walls
- [ ] Consistent body forcing, including velocity correction
- [ ] Mass/momentum monitoring with boundary and force budgets
- [ ] Checkpoint/restart
- [ ] ParaView-compatible VTK/XDMF or equivalent output

Validation gate: Shear-wave decay reproduces viscosity; Poiseuille profile matches analytical solution; errors decrease under refinement.

## Phase 2 — D3Q19

- [ ] Generalize lattice representation instead of duplicating solver
- [ ] D3Q19 equilibrium, collision, and streaming
- [ ] 3D periodic and solid boundaries
- [ ] Arbitrary voxelized geometry masks
- [ ] Pressure/density and velocity output
- [ ] Wall force and shear diagnostics

Validation gate: 3D channel and pipe benchmarks pass; quantitative grid convergence is reported; mass drift stays below the case-defined tolerance.

## Phase 3 — Robustness

- [ ] Track lattice Mach number, relaxation time, and viscosity
- [ ] Reject cases outside the declared operating envelope
- [ ] Compare BGK and TRT
- [ ] Investigate regularized, cumulant, or MRT approaches only when justified
- [ ] NaN/divergence detection and explicit failure status
- [ ] Automated stability report
- [ ] Regression benchmark suite

Validation gate: Invalid inputs and diverging cases fail explicitly; previous benchmark cases still pass.

## Phase 4 — Moving boundaries

- [ ] Moving-wall condition
- [ ] Rotating-cylinder case
- [ ] Hydrodynamic force and torque with consistent unit conversion
- [ ] Select and validate immersed or interpolated boundary method
- [ ] Arbitrary triangulated/voxelized moving objects
- [ ] Handle newly covered/uncovered cells and track fluid-volume changes
- [ ] STL geometry pipeline
- [ ] Rotation axis and RPM configuration

Validation gate: Rotating-cylinder benchmark passes; torque converges; moving geometry meets declared mass-leakage tolerance.

## Phase 5 — First stirred tank

- [ ] Cylindrical tank, simple impeller, and baffles
- [ ] Rotating impeller with stationary vessel
- [ ] Torque, power, P/V, and power number
- [ ] Velocity probes and time-averaged fields
- [ ] Vorticity and Q-criterion visualization
- [ ] Explicit filled-tank/lid boundary condition and fluid volume

Validation gate: Start in a laminar or resolved regime. Compare against regime-matched public data; demonstrate spatial and temporal sensitivity and averaging uncertainty.

## Phase 6 — Passive scalar and mixing

- [ ] Scalar advection-diffusion solver
- [ ] Dye injection with accounted source mass
- [ ] Molecular diffusivity and scalar stability checks
- [ ] Scalar conservation tests
- [ ] Probe concentration histories
- [ ] Define ±5% criterion, reference concentration, and sustained duration
- [ ] Compute t95 and volume-weighted coefficient of variation
- [ ] Define mixing-time map and unresolved/unmixed cells
- [ ] Scalar positivity/boundedness diagnostics

Validation gate: Pure diffusion and advection-diffusion benchmarks pass; scalar mass balance includes injection and boundary fluxes.

## Phase 7 — Turbulence

- [ ] LES interface and Smagorinsky baseline
- [ ] Local effective viscosity with consistent stress/forcing treatment
- [ ] Dynamic or WALE closure only after baseline validation
- [ ] Time averages and RMS fluctuations
- [ ] Resolved turbulent kinetic energy diagnostics
- [ ] Distinguish resolved and modeled dissipation
- [ ] Declare scalar turbulent diffusivity/Schmidt treatment

Validation gate: Canonical turbulent benchmark passes; tank power, velocity, and mixing comparisons use matched conditions and quantified uncertainty.

## Phase 8 — GPU backend

- [ ] Profile CPU reference
- [ ] Separate physics definition from execution backend
- [ ] CuPy prototype
- [ ] Custom CUDA collision/streaming kernels
- [ ] Fuse collide-stream where profiling supports it
- [ ] AoS/SoA experiments
- [ ] FP32/FP64 comparison
- [ ] Memory estimator including temporaries and headroom
- [ ] CPU/GPU regression comparisons
- [ ] MLUPS plus end-to-end timing

Validation gate: CPU and GPU benchmark observables agree within declared tolerances; measured memory fits the device budget.

## Phase 9 — Case management and deployment

- [ ] case.yaml and STL import
- [ ] Fluid properties, RPM, and automatic lattice scaling
- [ ] Stability and resource reports
- [ ] Run manager and durable job identifiers
- [ ] Progress/heartbeat and cancellation
- [ ] Checkpoint recovery: resume recoverable jobs, fail invalid cases
- [ ] Automated ParaView output
- [ ] Summary: Reynolds number, Mach number, P/V, power number, torque, mixing time, convergence
- [ ] Containerized solver worker with versioned inputs/outputs
- [ ] Integrate existing web UI through an asynchronous queue
- [ ] Keep agent/model provider outside numerical core
- [ ] User isolation, quotas, reproducibility, and worker observability

Validation gate: A committed case runs unattended and regenerates results; jobs survive frontend disconnects and recover from a valid checkpoint.

## Deferred beyond v1

- [ ] Free surfaces
- [ ] Gas-liquid systems and bubbles
- [ ] Particle tracking and population balances
- [ ] Non-Newtonian fluids
- [ ] Heat transfer and reactions/species
- [ ] Multi-GPU/domain decomposition
- [ ] Adaptive/local refinement

## First major finish line

STL tank and impeller → fluid properties and RPM → validated D3Q19 simulation → velocity, torque, P/V, and tracer mixing time → ParaView. Quantitative defensibility is limited to the validated flow regime, geometry resolution, and scalar treatment.

## Definition of done for every phase

1. Reproducible committed case definition.
2. Relevant unit tests pass.
3. Analytical or published quantitative comparisons pass predeclared thresholds.
4. Conservation errors and source/boundary budgets are reported.
5. Grid/time-step sensitivity characterized where applicable.
6. Previous regression cases pass.
7. Numerical failures produce explicit errors.
8. Results and metrics regenerate without manual intervention.

## Planned structure

```text
mini-lbm/
├── README.md
├── TODO.md
├── pyproject.toml
├── cases/{shear_wave,poiseuille,channel_3d,pipe,rotating_cylinder,stirred_tank}/
├── src/agent_gym.biolbm/
│   ├── lattice/
│   ├── collision/
│   ├── streaming/
│   ├── boundaries/
│   ├── forcing/
│   ├── geometry/
│   ├── scalar/
│   ├── turbulence/
│   ├── diagnostics/
│   ├── io/
│   └── backends/
├── tests/{unit,regression,validation}/
├── benchmarks/
├── docs/
└── outputs/  # generated; ignored by version control
```
