# Agent-decided numerical-validity experiments

Follow-up requested by the user after the CFD recovery pilot. Agents independently audited their own cases, chose whether correction was needed, recorded plans and adaptations, and performed bounded experiments. Scientific strategies were not prescribed by the coordinator. Planning could overlap; solver and meshing slots remained sequential: Luna, Sol, Astra. Water properties, volume flow 3.000 L/min and the approved Venturi geometry remained fixed.

## Luna (C): mesh-refinement experiments complete

Luna chose two independent refinements of its original 8,246-cell mesh. The 26,391-cell case passed checkMesh but diverged during the solver loop. The 61,416-cell case conserved the prescribed flow and had stable probes, but missed its strict velocity residual thresholds at the iteration cap. Compared with the baseline, sampled throat pressure-deficit magnitude changed by about 22.5% and peak sampled centerline axial velocity by 8.2%.

Luna judged that a third solve aimed only at crossing residual thresholds would not resolve the material mesh sensitivity, and stopped. Mesh independence is not established; the fine-grid comparison is diagnostic, not a converged grid study. The laminar model also does not validate transition physics.

## Sol (A): higher-order and transient correction experiments complete

Sol revisited higher-order convection with tight linear solvers on its unchanged mesh. It stopped the steady case at 693 iterations after a demonstrated nonlinear residual plateau and pressure oscillations, despite excellent mass conservation and small inner linear residuals. It then selected a time-accurate diagnostic rather than refining an unconverged steady solution.

Sol discovered inherited steady-run time bookkeeping in its transient setup and preserved the defect, then corrected it in its third and final run while halving the time-step/Courant limits. At the common physical time 0.55 seconds, inlet-minus-outlet static pressure difference changed from 13.2124 to 15.3789 Pa (16.4%); volume-weighted cell pressure and velocity relative L2 differences were about 10.16% and 6.78%. This is combined restart/setup and temporal sensitivity, not an isolated time-convergence study. The corrected case also retained outlet backflow.

Sol keeps the old 8.519 Pa upwind result unvalidated and claims no reliable replacement pressure prediction, mesh convergence, formal time convergence, or physical transition validation. Three additional actual solves were used; all exited within their watchdog budgets. The transient experiments are finite-time diagnostics.

## Astra (B): transient, temporal and mesh experiments complete

Astra independently chose transient higher-order flow with backflow-capable outlet treatment, followed by temporal and mesh sensitivity. Measured throughput showed the original 2.6-second physical horizon would exceed its runtime budget. It recorded an adaptation to two controlled 0.2-second coarse-grid diagnostics, then a 0.125-second independently refined-mesh diagnostic (50,929 cells). Original and revised horizons are kept separate; no multi-residence stationarity claim is made.

On the same coarse grid, halving the time step changed time-weighted mean inlet-minus-outlet static pressure difference by about 0.0665% and throat speed by 0.0134% over the common 0.1-to-0.2-second window. This supports low observed temporal sensitivity only for that short window. On the matched 0.075-to-0.125-second window, refinement changed static pressure difference from 11.26466 to 12.01471 Pa (6.66%), exceeding the model's 5% spatial screening limit. Mapped initial fields and the short transient confound a pure steady mesh-error estimate. Net flow conservation was excellent, while outlet backflow persisted.

All three additional actual solves exited normally within their watchdog limits. Astra leaves the old first-order result and full numerical/physical validity unestablished. No formal grid convergence, long-time statistical convergence or experimental validation is claimed.

## Evidence and interpretation

Plans, report, metrics, event ledger, dictionaries, solver logs, fields and comparisons are retained under artifacts/venturi-benchmark/cfd/{C,A,B}/validity-audit. Initial plan hashes and captured adaptations are in artifacts/venturi-benchmark/validity-audit/plan-hashes.json. Prior pilot artifacts remain intact; generated artifacts are excluded from Git.

These experiments assess agent decisions and numerical weaknesses in the pilot. Independently chosen strategies, different meshes, incomplete convergence and finite horizons preclude a controlled model accuracy ranking. Small residuals, checkMesh success and net flux balance do not validate a transitional-flow engineering prediction. No new human score or training eligibility is implied.

Eight additional actual solves were performed: Luna two, Sol three, Astra three. The coordinator verified solver exits before advancing compute slots. All solver processes are stopped. Correction choices and budget adaptations were made by the respective models; the coordinator enforced resources, sequencing and evidence preservation. All three audits retain material validity limitations; none supplies a validated replacement engineering prediction.
