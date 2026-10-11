# Luna-assisted ENTH validation result

The local CPU validation ran, but failed the strict physical checks and did not finish its planned duration. This is an assisted workflow pilot, not an independent Luna score or reproduction of Figure 4 in [Joseph et al. (2020)](https://doi.org/10.1038/s42003-020-01471-6).

Run `validation-006` used GROMACS 2023.3, 39,045 atoms, two CPU threads, a 4 GiB memory cap and a 30-minute wall limit. The supervisor stopped it after 1,790 seconds, with about 98 MiB of output. No GPU or paid compute was used. Preparation attempts and subsequent read-only analysis were separate from this dynamics clock.

| Measurement | Result |
| --- | --- |
| Saved dynamics | 10 ps restrained NVT + 10 ps restrained NPT + 38 ps released NPT = 58 ps |
| Planned dynamics | 100 ps |
| Released trajectory | 20 readable frames, 0–38 ps |
| Minimization | Converged in 766 steps, maximum force 915.34 kJ/mol/nm |
| Constraint check | Failed: LINCS constraint error at minimization step 21 |
| Released mean temperature | 303.18 K; target 303.15 K |
| Released volume change | +0.70% |
| Final phosphate geometry | Upper 48 POPC + 1 PIP2; lower 64 POPC; separation 37.53 Å |

Finite energies and coarse leaflet geometry do not override the constraint error. Pressure was highly variable and this short segment cannot establish equilibration. Future runs now stop at a minimization constraint error; that guard was added after this run and has not been exercised in another MD run.

The secondary-structure positive control caught a hydrogen-mode problem: GROMACS DSSP's `gromacs` mode assigned no alpha helix to the starting protein, while `dssp` mode assigned 115 of 158 residues. With `dssp` mode, the provisional H0 proxy (first 18 residues) retained 13–14 alpha-helical residues across the saved released frames. Its starting value was 14/18. This only describes persistence of an initially helical structure. The H0 mapping remains unconfirmed, and no adsorbed or solvent comparison was run.

The reconstructed membrane is smaller and asymmetric relative to the paper. Placement, lipid removal and PIP2 protonation are documented assumptions. The published 0.15 mM KCl was preserved literally, rather than changed to 0.15 M. Original simulation inputs were unavailable.

Evidence: [independent analysis](evidence/validation-006/independent-analysis.json), [supervisor result and file hashes](evidence/validation-006/supervisor-result.json), [executed worker source](evidence/validation-006/worker.executed.py), and [export manifest](evidence/validation-006/export-manifest.json). The worker snapshot matches the supervisor's recorded SHA256. The worker's final report was interrupted by the wall limit; the independent analyzer recovered the saved trajectory. Exported text inputs and logs are under `artifacts/enth/validation-006/run/`; full binary trajectories and inputs remain at `/home/gym/agent-gym-md/validation-006` in WSL.

Next scientific gate: repair and validate starting contacts and minimization constraints before any longer run. A new compute budget and confirmed state definitions would then be needed to compare the three states.
