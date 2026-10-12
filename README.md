# Agent Gym

This is a repo I built to test how different agent pipelines perform on multicomponent, long-horizon scientific tasks.

The goal is to see how agents connect scientific tools, handle failures, resume interrupted work, and check whether their results are scientifically valid. Runs preserve inputs, actions, tool outputs, checkpoints, and verification evidence so the workflow can be inspected and compared.

Current experiments include:

- **BioLBM:** Lettuce-backed CPU/GPU flow benchmarks and an experimental synthetic 5 L stirred-vessel workflow, exposed through bounded agent tools. [Setup and Colab testing](benchmarks/biolbm/README.md).
- **Pipe-flow optimization:** a lightweight analytical baseline with deterministic search, checkpoint/restart, and parallel replicas.
- **Venturi CAD and CFD:** geometry construction in FreeCAD, meshing with Gmsh, and OpenFOAM experiments covering solver execution, correction, and recovery.
- **ENTH molecular dynamics:** GROMACS preparation, bounded simulation runs, restart workflows, and analysis toward a published protein–membrane benchmark.

This is an experimental evaluation workspace. The scientific pilots include assisted runs and partial results; they are not independent model rankings or completed physical validation.

## Quick start

Python 3.11+; the analytical baseline uses only the standard library:

```sh
python -m agent_gym --run-dir runs/demo --steps 40
python -m agent_gym --run-dir runs/demo --steps 80 --resume
python -m unittest discover -s tests -v
```

Scientific workflows require additional software. See the [setup guide](docs/scientific-mcp.md), [Venturi benchmark](benchmarks/venturi/README.md), and [ENTH benchmark](benchmarks/enth/README.md).

For implementation details and current limits, see [project status](docs/project-status.md), [architecture](docs/architecture.md), and [data provenance](docs/data-policy.md).
