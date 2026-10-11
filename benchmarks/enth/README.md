# Epsin ENTH MD benchmark

Source: Joseph et al. (2020), https://doi.org/10.1038/s42003-020-01471-6.

Latest: [Astra-assisted retry results](validation-results.md). The retry repaired the minimization constraint failure and passed the available partial-run physical checks. It saved 28 ps before the shared 30-minute deadline; the planned 100 ps and biological agreement remain incomplete. The previous Luna-assisted run saved 58 ps but failed its constraint check.

The first target is Figure 4: compare H0 helicity in inserted, adsorbed and solvent configurations. The local CPU pilots test preparation, bounded execution and analysis of a reconstructed system. Both runs used assistance and inherited work; neither is an independent model score or a biological result.

## Source protocol

The paper specifies 1H0A, one PIP2 plus 99 POPC in the upper leaflet, 100 POPC below, TIP3 water, CHARMM36, GROMACS, 303.15 K and 1 bar. It reports 70 ns equilibration and 150 ns production per configuration, with helicity evaluated over the last 100 ns. The published salt concentration is 0.15 mM KCl; do not silently reinterpret it as 0.15 M. Pulling and PIP2 restraints need original input files or explicitly documented assumptions.

## CPU pilot bounds

See plan.json. The authorized Astra retry had one shared 30-minute execution window, including preparation and checkpoint-continuation gaps, two CPU threads, 4 GiB memory, no GPU or paid compute, and one simulation at a time. Read-only post-run analysis was separate. At most 100,000 atoms and 50,000 MD steps (100 ps at 2 fs). Continuation did not reset the clock or extend the TPR endpoints. Enforce CPU/memory/time at process-group or container level before launching MD; configuration values alone are not enforcement. Limit generated artifacts to 1 GiB.

## Evidence and evaluation

Keep inputs and their SHA256 hashes, software/package versions, commands, random seeds, stdout/stderr, processed topology, MDP, TPR, trajectory, energies and checkpoint. Record actual elapsed time and output size. Stop at budget exhaustion and preserve partial evidence. Never suppress GROMACS warnings with maxwarn to force a pass.

Score separately: (1) preparation and parameter provenance, (2) a physically valid short MD trajectory, (3) correct analysis, (4) biological agreement. Missing topology or inputs means blocked preparation, not a zero scientific result. A toy water/protein-only test may validate installation but does not count as ENTH-membrane simulation. Exiting successfully is insufficient: inspect finite energies, constraint errors, temperature, pressure/volume behavior and membrane integrity.

Before full reproduction, fix H0 residue mapping and state definitions independently of helicity; unwrap and align the membrane; calculate residue-wise helix occupancy with a documented secondary-structure method. Report uncertainty across independent seeds and avoid choosing frames to favor the expected ordering. Starting from a helical crystal structure and observing persistence in a short run does not demonstrate lipid-induced folding.

Original CHARMM-GUI inputs would make the pilot much more useful. Otherwise reconstructing the membrane and validating lipid parameters is a separate, documented preparation task. No full-length epsin, cellular endocytosis or tension-response claim follows from this initial target.
