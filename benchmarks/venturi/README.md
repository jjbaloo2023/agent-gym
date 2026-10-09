# Venturi CAD benchmark

The input drawing must be approved before download or model runs. Freeze its checksum, dimensions, allowed assumptions, and task prompt before comparing models. One independent attempt per model initially; same reasoning setting, tool set, time limit, and call budget. This is a constrained geometry-interpretation benchmark using a parametric Venturi tool, not a benchmark of unrestricted CAD programming.

Models: GPT-6 Luna, GPT-6.1 Sol, GPT-6 Astra. The CAD attempts ran through Codex subagents. Their use is not tracked as separate API cost by this benchmark.

Create blinded design labels A/B/C with a private label-to-model mapping. Models must not see each other's results or reference solutions. Launch a separate MCP server instance per attempt with AGENT_GYM_SCIENCE_RUNS pointing to its own directory; the default global server shares a workspace and must not be used for isolated benchmark attempts. Keep generated native FCStd, STEP, STL, previews, tool logs, and provenance under the run ID. Human scoring determines the preferred design; tool-generated validity checks are evidence, not human scores.

## Scoring (100 points)
- Drawing fidelity and correct dimensions: 40.
- Editable parameterization and sensible construction: 20.
- Solid validity and fluid-domain topology: 15.
- Mesh readiness and correct patches/units: 15.
- Clear assumptions and deliverable explanation: 10.

Record scores per criterion and comments. Missing dimensions or undocumented additions must be explicit. Invalid topology blocks CFD even if the human total is highest. With one attempt per model, results compare these attempts and do not estimate general model performance.

## Next CFD phase
The user subsequently authorized CFD on all three designs in order Luna, Sol, Astra, at a common transitional flow. See [cfd-protocol.md](cfd-protocol.md) for fixed conditions, budgets, recovery rules, and evidence requirements. The earlier best-design-only plan below is superseded for this pilot.

After scores are entered, select the best valid design. Freeze fluid, inlet flow/velocity, viscosity, density, outlet pressure, and the physical objective. Perform a small solver check and mesh-refinement study before an overnight run. Use convergence, mass balance, and pressure loss/recovery checks. A long runtime by itself does not improve accuracy.

No overnight job is scheduled. Before dispatch, set a hard runtime/resource budget and verify checkpoints, computer sleep/power settings, and restart behavior.
