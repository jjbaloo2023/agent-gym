# BioLBM module

BioLBM is Agent Gym's optional Lettuce-backed CFD module. Agents call structured tools; the numerical core also runs directly without a model API. This is an experimental workflow, not a validated bioreactor simulator.

## Included

- D2Q9/D3Q19 periodic Taylor–Green benchmark cases, BGK, CPU/PyTorch CUDA.
- YAML/JSON configurations, lattice scaling checks, resource estimates, mass/Mach diagnostics, VTK output and NPZ state saving.
- Synthetic rounded-bottom 5 L vessel with 3 L liquid, a 2.36-inch pitched paddle, 6 mm shaft, and 180 rpm CCW rotation viewed from above.
- Experimental diffuse moving-rotor force extension; CPU demonstration evidence in `cpu-demonstration.json`.
- Agent MCP operations and a [Colab GPU notebook](../../notebooks/BioLBM_Colab.ipynb).

The CPU vessel demo completed 1,200 steps in approximately 152 seconds. It used 0.1 Pa·s liquid (Re ≈108) and simulated only 0.368 s of startup. Water at this grid/RPM fails the declared BGK tau envelope and is rejected. Neither tank torque, steady state, nor mixing time is physically validated. See [vessel details](vessel-workflow.md).

## Install (Python 3.12+)

Keep this separate from the existing MCP/FreeCAD environment if those use Python 3.11. The standard-library Agent Gym baseline remains unchanged and requires no scientific dependencies.

```bash
python3.12 -m venv .venv-lbm
source .venv-lbm/bin/activate
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[biolbm]'
python -m agent_gym.biolbm check benchmarks/biolbm/cases/taylor_green_2d/case.yaml
python -m agent_gym.biolbm run benchmarks/biolbm/cases/taylor_green_2d/case.yaml --output runs/tgv-001
```

For GPU, use an appropriate CUDA-enabled PyTorch build instead of the CPU wheel. Colab normally supplies Torch; the notebook checks CUDA and keeps that environment. GPU and Colab execution have not been verified from the current CPU environment.

## Agent interface

The existing `scientific-agent-gym` MCP server adds:

| Tool | Behavior |
| --- | --- |
| `validate_lbm_case(kind, config)` | Normalize a `benchmark` or `vessel` case; report numerical and resource limits. Does not verify hardware availability. |
| `run_lbm_case(kind, config)` | Run inline, return an opaque job ID, status, and numerical summary. |
| `inspect_lbm_run(run_id)` | Inspect status and summary without caller-supplied filesystem paths. |

Configure the MCP process with:

```bash
export AGENT_GYM_BIOLBM_PYTHON=/absolute/path/to/.venv-lbm/bin/python
export AGENT_GYM_BIOLBM_RUNS=/absolute/writable/path/to/lbm-runs
```

The worker environment must have Agent Gym installed. Example tool input:

```json
{"kind":"benchmark","config":{"flow":"taylor_green_2d","resolution":32,"reynolds_number":20,"steps":100,"device":"cpu","precision":"float64"}}
```

Limits: one local job, ten minutes, at most 2,000 steps, CPU 250,000/GPU 2,000,000 lattice cells, reporting interval no greater than 100 steps, and two vessel CPU threads. A stale lock after a killed controller requires operator inspection. This initial API is synchronous; it is not a durable asynchronous queue, hard memory sandbox, or multiuser service. Multiuser authorization and cancellation are not implemented.

## Colab

[Open the feature-branch notebook in Colab](https://colab.research.google.com/github/jjbaloo2023/agent-gym/blob/feat/biolbm-module/notebooks/BioLBM_Colab.ipynb). Select a GPU runtime. It clones the feature branch, installs the optional module, compares CPU/GPU benchmark results, and optionally runs the viscous vessel. Update the notebook's branch once merged or pin a commit for reproducible tests.

## Roadmap and evidence

Validation comes first: canonical refinement studies, moving-wall/rotating-cylinder torque comparisons, tank resolution and temporal sensitivity, longer regime-matched tank comparisons, passive scalar conservation/mixing, then turbulence. See [TODO](TODO.md).

Checkpoint files save distributions and step; restart restoration is not yet implemented. The vessel's 3 mm cells under-resolve blades/shaft, use full-way voxel walls and a rigid liquid-level lid, and retain fictitious fluid inside diffuse rotor regions. Complete-grid mass conservation alone does not validate moving-boundary leakage. Benchmark pressure/velocity use normalized units; vessel VTK coordinates and velocities are SI.

Lettuce is pinned to revision `d57b061e6ea498ff959c549c58d352dac06ecf99` and retains its MIT license. The new BioLBM application code is under [MIT](LICENSE); retain [third-party notices](THIRD_PARTY_NOTICES.md). No third-party solver source is vendored. Geometry and cases are synthetic. Do not import workplace source/data into these examples.
