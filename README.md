# Agent Gym
A scientific workflow laboratory for measuring agent reliability, portability, persistence, and scaling.

Three eventual uses share the same execution and evidence core:
1. **Agent evaluation**: compare agents, tools, recovery strategies, budgets, and environments.
2. **RL environments**: expose bounded actions, observations, rewards, and termination to training systems.
3. **Domain datasets**: curate verified demonstrations with explicit source rights and destination eligibility.

## First experiment
The runnable prototype is an analytical laminar pipe-flow inverse-design task. An agent changes pipe radius to match a target pressure drop. A deterministic hill-climbing baseline accepts improving proposals. It establishes scoring, checkpoint/restart, and process-level parallel runs without API fees or solver installation.

This is **not yet CAD, CFD, an LLM agent, or a Gymnasium integration**. It uses the Hagen-Poiseuille relation for steady, fully developed, incompressible laminar flow in a circular pipe. Those assumptions do not generalize to arbitrary geometries.

## Run
Python 3.11+; standard library only. From the repository root:
```sh
python -m agent_gym --run-dir runs/demo --steps 40
python -m agent_gym --run-dir runs/demo --steps 80 --resume
python -m agent_gym --run-dir runs/batch --steps 80 --replicas 4 --workers 2
python -m unittest discover -s tests -v
```
Steps are a total episode budget; resume continues to that total. A run directory belongs to one writer. Existing runs cannot be overwritten accidentally. Each replica has a distinct directory and seed.

## Evidence
Each checkpoint contains task configuration and its hash, baseline identity, seed, Python/platform metadata, RNG state, incumbent, every candidate, validity, acceptance, and physical metrics. Writes use temporary-file replacement. The recorded seed and RNG state allow deterministic restart; machine metadata supports comparison but does not prove cross-platform parity.

The agent sees only task observations and solver feedback. Future hidden scoring, reference answers, and held-out cases belong outside the agent workspace.

## Scientific workflow target
Dimensioned 2D blueprint -> structured geometry specification -> CAD/STEP -> mesh -> OpenFOAM case -> solver -> physical validation -> report.

Start with a specified laminar pipe before arbitrary blueprint images. Validate geometry, units, topology, mesh quality, boundary conditions, convergence, mass balance, and agreement with an analytical reference. A solver exit code alone is not success.

See [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [data provenance](docs/data-policy.md).
