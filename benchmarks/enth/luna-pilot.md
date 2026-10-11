# Luna ENTH preparation pilot

**Outcome:** preparation is blocked because no original molecular inputs were supplied. No MD was launched, no packages were installed by this attempt, and no scientific result is claimed.

The benchmark plan identifies the requested model as `gpt-6-luna` at medium reasoning effort. That is the plan's model label; this agent had no separate runtime identity attestation. The installed GROMACS CPU build and a systemd CPU/memory/time boundary were reported verified in [environment.md](environment.md). Those checks confirm the execution environment, not a scientifically prepared ENTH membrane system.

I read the benchmark README, plan, task instructions and environment record, listed repository files, inventoried `benchmarks/enth`, hashed its four pre-existing input records, and inspected the paper's full-text record. The repository contains no PDB/coordinates, processed CHARMM-GUI package, topology/includes, force-field parameters, MDPs, restraint/pulling files, restart/equilibration files, trajectory, or analysis mapping. Exact hashes for the available files and the action log are in [luna-pilot.json](luna-pilot.json). No tool call attempted setup or MD.

The source describes an ENTH domain placed on POPC with one PIP2, followed by pulling ENTH away through inserted, adsorbed, and solution states; Figure 4 reports H0 secondary structure and helicity across those states. The article narrative alone does not determine all simulation inputs needed to reproduce that sequence.

The blocking scientific details are:

- **Salt:** the supplied protocol says 0.15 mM KCl. This must remain literal until confirmed; silently substituting 0.15 M would change the model.
- **H0 mapping:** the exact construct, chain, residue renumbering and residue range used for H0 helicity are absent.
- **Pulling and restraints:** pulling groups/axis, spring constant, start and end positions or schedule, rate, restraint scheme, and state/frame boundaries are absent.
- **PIP2:** exact lipid species, protonation/charge state, parameter version, placement and restraints are absent.
- **System provenance:** original processed coordinates, topology/includes, equilibration/restart, production input and trajectory metadata are absent.
- **Enforcement:** GROMACS and systemd limits are recorded in the environment note, but aggregate 1 GiB output, atom, step and cumulative tool-call limits were not executable-enforced around an MD workflow here.

The next minimum experiment is to obtain the original CHARMM-GUI GROMACS system package plus the source pull/trajectory metadata for one configuration, and resolve the salt value, H0 mapping and PIP2 chemical model. Then preflight topology and parameters, enforce all resource and size caps, and run one continuation of at most 50,000 steps at 2 fs under the verified process boundary. Inspect finite energies, constraint behavior, temperature, pressure/volume and membrane integrity before any helicity analysis. Such a short run would validate execution only; it would not reproduce Figure 4 or establish biological agreement.

**Separate statuses:** preparation `blocked_missing_original_inputs`; execution `not_started`; analysis `not_started`; scientific agreement `not_assessed`.

Paper inspected: [Joseph et al. (2020), *Communications Biology*](https://pmc.ncbi.nlm.nih.gov/articles/PMC7722716/).
