# Astra-assisted ENTH retry result

Astra repaired the minimization constraint failure and produced a short trajectory that passed the available physical checks. The retry saved **28 ps of dynamics**, against a planned 100 ps, before the original 30-minute limit. This is an assisted workflow pilot, not an independent model score or a reproduction of Figure 4 in [Joseph et al. (2020)](https://doi.org/10.1038/s42003-020-01471-6).

Run `validation-007` used `gpt-6-astra` with high reasoning effort, inherited reconstruction/code and parent orchestration. It reused all five public source files and generated the same starting complex as validation-006; their hashes match. GROMACS 2023.3 ran on 39,045 atoms with two CPU threads, a 4 GiB cap, no GPU and no paid compute.

| Measurement | Luna-assisted 006 | Astra-assisted 007 |
| --- | --- | --- |
| Saved dynamics | 58 ps | 28 ps: 10 NVT + 10 restrained NPT + 8 released NPT |
| Final checkpoint progress | Incomplete | 28.4 ps cumulative; released step 4,200 at 8.4 ps |
| Planned 100 ps completed | No | No |
| Constraint check | Failed at minimization step 21 | Passed across both minimizations and all MD stages |
| Released mean temperature | 303.18 K | 303.51 K; target 303.15 K |
| Released volume change | +0.70% | +0.39% |
| Final phosphate separation | 37.53 Ã… | 38.04 Ã… |
| Released saved frames | 20 | 5, spanning 0â€“8 ps |

The repair first relaxed covalent bonds involving hydrogen without converting them to constraints, while retaining rigid-water SETTLE. A separate constrained minimization then checked compatibility with MD. Relaxation converged in 711 steps with maximum force 922.65 kJ/mol/nm; constrained minimization converged in two steps at 442.92 kJ/mol/nm. Both were warning-free. The contact audit found 21 initial intermolecular protein/lipid or lipid/lipid heavy-atom pairs below 1.8 Ã…, including a 0.575 Ã… PIP2â€“protein overlap. After each minimization, no audited pair was below the 2.5 Ã… search radius. These distances describe contact repair, not full system validation. [Protocol and assumptions](validation-reconstruction.md).

All segments shared the original start, **14:04:25 UTC on 2026-10-10**. Total elapsed time was **1,749.98 seconds**, including preparation and intervention gaps. The inherited six-minute NVT sublimit stopped at 7 ps; exact checkpoint continuation reached the original 10-ps endpoint. A new completion parser then rejected the valid endpoint because its GRO title omitted time. The parser was corrected to require final coordinates and the explicit final log step/time row, and a second continuation advanced to NPT without repeating dynamics. The supervisor requested the final graceful stop at 29 minutes. No new 30-minute allocation was granted. All original and intermediate sources/reports are retained.

The workflow used 17 recorded scientific subprocesses, within its 20-command cap. Read-only analysis followed outside the MD window: two seven-command passes and one checkpoint inspection. The first analysis incorrectly treated the valid `epsilon-rf = inf` configuration value as a nonfinite observable; the corrected parser retains that parameter explicitly and still rejects nonfinite energies. The initial analyzer and result are preserved. All 23 repository regression tests passed. Output was about 98 MiB at MD shutdown and 102 MiB after analysis, below 1 GiB. Throughput varied, so saved duration is not a model-speed score.

The final independent analysis reports `partial_run_physical_checks_passed`, with finite energies, no constraint errors, plausible coarse membrane geometry and a valid DSSP positive control. Pressure ranged from âˆ’442 to +406 bar over only 8.4 ps; this does not establish equilibration. The membrane retained upper 48 POPC + one PIP2 and lower 64 POPC. The unconfirmed H0 proxy retained 13â€“14 alpha-helical residues out of 18 over five released frames, versus 14 initially. This only shows brief persistence of an initially helical structure. No adsorbed/solvent comparison or biological agreement was assessed.

Evidence: [independent analysis](evidence/validation-007/independent-analysis.json), [source/input/budget audit](evidence/validation-007/provenance-audit.json), [final continuation supervisor](evidence/validation-007/continuation-result.json), [checkpoint time](evidence/validation-007/checkpoint-time.txt), [export manifest](evidence/validation-007/export-manifest.json), and [preserved 006 summary](evidence/validation-006/summary.md). All executed-source hashes and final non-self manifest hashes match. The audit explicitly excludes the final manifest's historical self-entry; the archived first continuation report is verified normally. Text inputs/logs are under `artifacts/enth/validation-007/run/`; full binary inputs, trajectories and checkpoints remain at `/home/gym/agent-gym-md/validation-007` in WSL.

The reconstructed membrane remains smaller and asymmetric relative to the paper. Placement, PIP2 protonation and H0 mapping remain assumptions; published 0.15 mM KCl was retained literally. A longer scientific comparison still needs resolved state definitions, original inputs where available, independent seeds and a separate compute budget.


## Colab GPU follow-up —11October2026

The corrected portable010 reconstruction completed a real T4 GPU validation:100ps NVT,500ps restrained NPT and100ps released NPT. All12 scientific commands returned0 and all runner physical gates passed. GROMACS2026.4 assigned PP and PME tasks to the GPU. The released segment reported24.147ns/day, mean303.300K, volume change+0.980%, exact200-lipid leaflets and37.283Å phosphate separation.

The recovered textual report is [validation-observed.json](evidence/colab-takeover-010/validation-observed.json). This was extracted from saved Colab notebook output, with raw DOM evidence retained locally. Colab expired afterward; an explicit recovery check found no prior checkpoint, trajectory directory or executable. Binary evidence was not recovered. Long equilibration and biological agreement remain untested. The model attribution is an assisted Astra reconstruction with parent-controlled execution, not an independent model score.
