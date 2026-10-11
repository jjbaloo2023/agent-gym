# Agent Gym
A test system for agents that use scientific software. Each run records inputs, agent actions, tool results, failures, corrections and verification checks.

The current focus is agent evaluation. RL environments and domain-specific training datasets are planned, not implemented. Dataset use requires source-rights and destination review.

## Current state

| Component | What works | Limit |
| --- | --- | --- |
| Analytical task | Pipe search, deterministic hill climbing, checkpoint restart, process replicas | No LLM or CFD solver |
| Scientific MCP | FreeCAD Venturi construction, Gmsh mesh, OpenFOAM conversion and mesh checks | No CFD solve tool or general CAD programming |
| Model evaluation | Luna, Sol and Astra completed CAD, sequential CFD, and self-directed correction experiments | CFD ran through shell tools; physical accuracy remains unvalidated |
| Recovery demo | A real solver was suspended, detected as stalled, killed, then restarted from a saved checkpoint | One process-stall test; not power-loss or interrupted-write recovery |
| Evidence | A compact run bundle is committed, with trajectory, logs, inputs, fields and verification | Full experiment outputs remain outside Git |

See the [CFD pilot](benchmarks/venturi/cfd-results.md), [validity audit](benchmarks/venturi/validity-audit-results.md), and [inspectable recovery run](evidence/cfd-interruption-v1/README.md). Exit code zero, a mesh check, or small residuals do not establish physical accuracy.

## First experiment
The runnable prototype is an analytical laminar pipe-flow inverse-design task. An agent changes pipe radius to match a target pressure drop. A deterministic hill-climbing baseline accepts improving proposals. It establishes scoring, checkpoint/restart, and process-level parallel runs without API fees or solver installation.

This analytical experiment runs without CAD, CFD, an LLM agent, or Gymnasium. The separate scientific MCP below adds CAD and meshing. It uses the Hagen-Poiseuille relation for steady, fully developed, incompressible laminar flow in a circular pipe. Those assumptions do not generalize to arbitrary geometries.

## Run in Docker
With Docker Desktop running in Linux-container mode:
```sh
docker compose build
docker compose run --rm --entrypoint python gym -m unittest discover -s tests -v
docker compose run --rm gym --run-dir /data/demo --steps 40
docker compose run --rm gym --run-dir /data/demo --steps 80 --resume
```
Checkpoints persist in a Docker-managed volume outside OneDrive and the repository. The container is limited to two CPU equivalents and 2 GiB RAM. See [container instructions](docs/containers.md) for parallel runs, shells, and artifact export. Rebuild after source changes.

## Run
Python 3.11+; standard library only. From the repository root:
```sh
python -m agent_gym --run-dir runs/demo --steps 40
python -m agent_gym --run-dir runs/demo --steps 80 --resume
python -m agent_gym --run-dir runs/batch --steps 80 --replicas 4 --workers 2
python -m unittest discover -s tests -v
```
Steps are a total episode budget; resume continues to that total. A run directory belongs to one writer. Existing runs cannot be overwritten accidentally. Each replica has a distinct directory and seed.

## Run records
Each checkpoint contains task configuration and its hash, baseline identity, seed, Python/platform metadata, RNG state, incumbent, every candidate, validity, acceptance, and physical metrics. Writes use temporary-file replacement. The recorded seed and RNG state allow deterministic restart; machine metadata supports comparison but does not prove cross-platform parity.

The agent sees only task observations and solver feedback. Future hidden scoring, reference answers, and held-out cases belong outside the agent workspace.

OpenFOAM field checkpoints are separate from the analytical JSON checkpoint. The controlled demo checks that restart loads the saved time and compares the recovered fields with an uninterrupted control. Verify its committed evidence without WSL or OpenFOAM:

```sh
python scripts/verify-cfd-evidence.py evidence/cfd-interruption-v1
```

The bundle README gives solver replay instructions. File hashes detect changes; they are not external signatures. Current verification runs on the same local machine as execution.

## Scientific CAD and meshing
The WSL scientific MCP builds an editable axisymmetric Venturi with FreeCAD, meshes its fluid STEP with Gmsh, and converts/checks the mesh in OpenFOAM 14. See [scientific MCP setup](docs/scientific-mcp.md) and [Venturi benchmark](benchmarks/venturi/README.md). Drawing approval, CAD scoring, CFD pilots and numerical-validity audits are complete. The user awarded all three CAD attempts 100/100. This does not imply a CFD accuracy score.

## Epsin ENTH molecular dynamics

The [ENTH benchmark](benchmarks/enth/README.md) targets Figure 4 of Joseph et al. (2020), Communications Biology. An Astra-assisted CPU retry repaired the earlier minimization constraint failure and saved 28 ps with passing partial-run physical checks within the original 30-minute limit. The planned 100 ps and biological comparison remain incomplete. See [results and evidence](benchmarks/enth/validation-results.md), [environment](benchmarks/enth/environment.md) and [pilot bounds](benchmarks/enth/plan.json). These assisted workflow pilots are not independent model scores.

## Scientific workflow target
Dimensioned 2D blueprint -> structured geometry specification -> CAD/STEP -> mesh -> OpenFOAM case -> solver -> physical validation -> report.

Use bounded tasks before general workflows. Check geometry, units, mesh, boundary conditions, convergence and mass balance. Assess numerical sensitivity, then compare with physical reference data. Keep execution success, numerical verification and physical validation separate.

Portability and scaling remain experiment goals. Process replicas and environment records exist; a cross-platform scientific suite and distributed scheduler do not. The analytical Docker boundary does not apply to WSL scientific processes.

Documentation uses short sentences and fixed terms. The [writing guide](docs/writing.md) follows ASD-STE100 principles without claiming formal compliance.

See [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [data provenance](docs/data-policy.md).
