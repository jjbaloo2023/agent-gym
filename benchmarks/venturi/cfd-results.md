# Venturi CFD recovery pilot

The three model workflows ran sequentially: Luna (C), Sol (A), Astra (B). Each used water at 20 degrees C, density 998.2 kg/m3, kinematic viscosity 1.004e-6 m2/s, and prescribed volume flow 3.000 L/min. Nominal inlet/throat Reynolds numbers were approximately 2439/3963. All solver processes exited before the next model's solver started.

| Model | Initial actual solve | Final actual solve | Interpretation |
| --- | --- | --- | --- |
| Luna | SST RANS diverged at 1200 iterations; unbounded turbulence field and unacceptable flux | Steady laminar recovery, OpenFOAM reported convergence at 741 iterations | Numerically converged laminar reference; physics changed during recovery and does not validate transition |
| Sol | Steady laminar run reached 1200 with oscillatory residuals and pressure | Steady laminar upwind recovery reached 1200; stable monitors and residuals below post-run 1e-5 check, but pressure residual about 2.64e-6 misses stricter 1e-6 | Qualified numerical result; no automatic residual stop; audit criteria were post-run |
| Astra | Steady laminar run reached 1200; physical monitors stable but nonlinear residual checks failed | Steady laminar upwind recovery reached 1200 and passed its residual, monitor stability, conservation and target-flow checks | Numerically settled under model-defined checks; iteration cap alone was not used as evidence |

Every model used two actual solves and preserved the unsuccessful first solve. Luna and Sol also repaired diagnostic/startup configuration failures. Astra reached its first solution loop without a startup repair. No actual hang was encountered; bounded watchdogs were present, but this pilot does not demonstrate recovery from a deliberately injected hang.

Final cases enforced the specified volume flow on the actual faceted inlet. Luna's first solve instead used analytical-area velocity, producing approximately 0.84% less flow; the agent corrected this after the coordinator requested an achieved-flow audit. This intervention is part of the record and limits claims of fully unassisted performance. The coordinator also expanded Luna's initial overly restrictive startup-launch budget; see cfd-protocol.md and its event ledger.

The final laminar cases do not resolve transition. Coarse tetrahedral meshes have no demonstrated boundary-layer resolution or grid independence, the geometry has no upstream/downstream straight extensions, and inlet disturbances are unspecified. Sol and Astra added first-order upwind convection during recovery; their reports explicitly acknowledge diffusion and possible suppression of physical unsteadiness. Their pressure-drop changes across schemes show that numerical convergence alone does not establish accuracy. Model-specific meshes and diagnostics differ, so these attempts are workflow evidence rather than a controlled accuracy ranking.

The existing scientific MCP handles CAD and meshing. These CFD cases were generated and run through shell tools; no solver MCP capability or overnight job is claimed. No new human CFD scores have been assigned.

Local evidence is retained under artifacts/venturi-benchmark/cfd/C (Luna), A (Sol), and B (Astra): reports, machine-readable metrics, event ledgers, solver logs, dictionaries, monitoring histories and final fields. Generated artifacts are excluded from Git; this summary and protocol provide the durable repository record.
