# Execution and evidence architecture

Agent Gym tests how agents complete bounded scientific tasks. A run must show what the agent did, what tools returned, what failed, and what checks passed.

## Run contract

1. The task defines inputs, units, allowed actions, resource limits and success checks.
2. The agent selects an action or correction.
3. The executor runs the tool in a run directory.
4. The recorder stores the action, result, process status and artifacts.
5. The verifier checks the recorded evidence.

Task, agent, executor and verifier should remain separate. Current code covers parts of this contract. It is not a general workflow scheduler.

## Implemented components

| Component | Location | Execution boundary |
| --- | --- | --- |
| Analytical task and hill climber | `agent_gym/core.py` | Local Python or bounded Docker container |
| Analytical checkpoint | Run-directory JSON | One writer; atomic file replacement |
| CAD and mesh operations | `agent_gym/science.py`, `mcp_server.py` | WSL processes; bounded parameters |
| Model experiments | `benchmarks/venturi/` | Separate agent run directories; sequential solver slots |
| CFD experiments | Agent-written cases and shell scripts | WSL OpenFOAM; experiment-specific budgets |
| Controlled interruption | `scripts/demo-cfd-interruption.py` | Owned process group; injected stall; field restart |
| Evidence verification | `scripts/verify-cfd-evidence.py` | Offline checks on committed files |

The MCP does not expose a CFD solver. Existing CFD scripts are not a general solver adapter. The committed demo includes a case and mesh, so replay does not require FreeCAD or Gmsh.

## Two checkpoint types

The analytical checkpoint stores the task state, RNG state and candidate history. A resumed hill climber continues deterministically.

An OpenFOAM checkpoint stores fields at a written iteration or physical time. Restart also depends on the mesh, dictionaries and time metadata. The controlled demo validates saved fields, selects `latestTime`, and checks the loaded time. It compares recovered fields with an uninterrupted control.

The demo suspends a solver with SIGSTOP. The kernel confirms the stopped state. A progress watchdog detects the stall and kills that process group. Restart uses a checkpoint completed before the interruption. This tests one process-failure path. It does not test power loss, corrupted checkpoints, interrupted writes or recovery of an LLM conversation.

## Evidence boundaries

Full outputs remain under ignored `artifacts/` directories and native WSL directories. A compact bundle under `evidence/` is committed. It includes a readable trajectory, compressed raw logs, case inputs, saved fields, checksums and a verification result.

The offline verifier checks hashes, failure/restart events, solver logs and control-field agreement. Hashes detect changes; they are not external signatures. Execution and verification use the same local machine. A protected scorer, signed records and hidden reference data are not implemented.

| Term | Meaning |
| --- | --- |
| Execution success | The tool completed its declared operation |
| Numerical verification | Stated numerical checks passed within their limits |
| Physical validation | Predictions agree with suitable physical reference data |
| Recovery | Execution continued from saved state after a recorded failure |

The Venturi audits found material numerical sensitivity. Convergence of a discrete problem does not establish physical accuracy. The interruption demo tests execution recovery, not transition-flow accuracy.

## Resource and security limits

The analytical Docker container has a pinned image, non-root user, read-only filesystem and persistent data volume. WSL scientific processes do not inherit this boundary. Watchdogs and CPU limits bound resource use; they do not sandbox arbitrary agent commands. Isolation for untrusted generated commands remains future work.

One writer owns each run directory. No general concurrent-writer lock, transactional event store, distributed scheduler, provider API, Gymnasium wrapper or training-data exporter is implemented.

## Next experiments

Portability requires the same inputs and checks across environments. Scaling requires measured throughput, queue delay and resource use. Further persistence tests should inject interrupted writes, worker loss and agent loss separately. Each test needs its own recovery criteria.

RL and dataset use will share the run contract. They require bounded actions, independent checks and reviewed data rights. Current experiment records are not approved training datasets.
