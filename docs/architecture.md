# Execution and evidence architecture

## Shared core
A task specifies versioned inputs, units, constraints, action space, budgets, and success checks. An agent adapter selects actions. A tool adapter executes them in an isolated workspace. A verifier evaluates resulting artifacts. A recorder stores observations, actions, tool outcomes, costs, provenance, and checkpoints.

Keep task, agent, execution backend, and scoring independently replaceable. Compare agent frameworks by wrapping this contract, not by embedding a framework into the task.

## Current implementation
One analytical task, reset/step interface, deterministic hill climber, atomic checkpoint with embedded trace, and independent process replicas. Docker Compose provides a pinned Python image, a persistent checkpoint volume, and bounded non-root execution. No distributed scheduling, provider API, dataset exporter, or external scientific tool is implemented.

One writer per run directory is required. Checkpoints do not implement concurrent-writer locking or recover arbitrary external solver side effects. Embedded history is deliberately simple; replace it with a transactional event store plus content-addressed artifacts before long episodes.

## Scientific adapters
Blueprint interpretation emits a geometry specification with dimension evidence and uncertainty. CAD emits native files plus STEP. Meshing records topology, quality, cell count, and boundary names. Solver adapters record exact tool/image versions, configuration, stdout/stderr, timing, and numerical output. Verification runs outside the agent's writable scope.

Pin solver/container versions and hash inputs/artifacts. Use independent checks for dimension errors, non-manifold geometry, bad meshes, divergence, mass imbalance, incorrect boundary conditions, and inaccurate physics.

## Experiments
- Portability: repeat a fixed suite across OS, container/remote backends, providers, and agent frameworks. Measure artifact validity, numerical tolerances, and outcome agreement.
- Persistence: interrupt at stage boundaries; restart tool, agent, and worker independently. Measure duplicated work, lost state, and successful recovery.
- Scaling: increase independent episodes first; then study collaborative agents separately. Report throughput, queue delay, resource use, cost, failure rate, and scientific quality.
- Hill climbing: optimize workflow policy (prompts, tool descriptions, retry rules), engineering design variables, or model weights as separate experiments. Freeze held-out geometry families and budgets. Compare against scripted, random-search, and expert baselines.

## Three consumers
Evaluation produces scorecards and failure analysis.
RL wraps the task in a standard environment contract, with bounded tool actions and rewards from independent physical checks.
Dataset curation exports only rights-cleared, verified, explicitly approved trajectories. Keep model-generated text separate from solver measurements and human demonstrations; provenance follows all derived artifacts.

## External execution boundaries
Before enabling generated commands: isolated containers/VMs, bounded resources and wall time, restricted mounts and network, secret separation, safe process-tree termination, immutable scoring inputs, and artifact limits. These controls are future requirements, not features of this prototype.
