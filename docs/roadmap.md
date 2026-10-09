# Roadmap

## 0: runnable foundation (implemented)
Analytical pipe inverse-design environment, deterministic hill climb, reproducible restart, process replicas, and invariant tests. This validates the harness only.

## 1: one real scientific workflow
Use an explicit dimensioned pipe specification, a CAD adapter, a mesh adapter, and a pinned OpenFOAM environment. Select and validate tool versions when implementing. Compare pressure drop against the analytical solution; record mesh convergence and mass balance. Include known broken cases and a scripted successful baseline.

Exit: a fresh environment reproduces the result; a failed stage produces an actionable diagnostic.

## 2: agent evaluation
Add a provider-neutral structured action adapter and one authorized API integration. Compare scripted and LLM agents on held-out dimensions and geometry variants. Track success, numerical error, invalid actions, latency, tokens/cost, and intervention count.

Exit: repeated runs and a failure taxonomy distinguish agent errors from tool/runtime errors.

## 3: robustness and portability
Add restart fault injection, container/remote execution, dependency fingerprints, stage caching, idempotency keys, and per-stage artifacts. Expand to ambiguous blueprints only after structured geometry works.

Exit: interruption and backend changes preserve valid artifacts and scientifically equivalent outcomes within documented tolerances.

## 4: scale and optimization
Queue independent episodes with resource quotas and provider rate limits. Run bounded search over prompts/tool policies and engineering designs. Separate development, validation, and sealed test sets; report distributions, not best-of-N alone.

## 5: split into three products
- Evaluation suite and regression dashboard.
- RL environment with standard spaces and independently protected scoring.
- Curated dataset pipeline with provenance, verification, license review, and destination-specific approval.

The products reuse tasks and evidence but have separate release and data policies.
