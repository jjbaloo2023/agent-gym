# ENTH inserted-state bounded validation

Preparation: **failed_or_blocked**. Execution: **not_started**. Analysis: **not_started**.

The attempt stopped at the first failed preflight or command; partial evidence is preserved.

## Reconstruction choices

- Protein: chain A of rat epsin ENTH PDB 1H0A; the bound Ins(1,4,5)P3 ligand was used only to define the modeled membrane-contact anchor and removed from the final system.
- Assumed H0: chain A residues 1–18; exact Figure 4 residue mapping was not supplied, so this is an explicit structural convention, not confirmed paper mapping.
- Membrane: public CHARMM-GUI 128-lipid POPC pure-bilayer archive, the smaller archived size selected to meet the 100,000-atom cap after solvation. The protein was oriented by the vector from protein C-alpha centroid to crystallographic InsP3 centroid; the ligand centroid was aligned to the upper-leaflet POPC phosphate plane. This is a reproducible geometric reconstruction, not the authors' original placement.
- PIP2: one CHARMM-GUI SAPI24 molecule replaces the upper-leaflet POPC nearest the crystallographic ligand anchor. SAPI24 is the CHARMM lipid model protonated on P4 (formal residue charge -4). The paper does not report this protonation choice.
- Salt: 0.15 mM KCl is passed literally to GROMACS. At this system size it is below a single neutral KCl pair; only charge-neutralizing K+ counterions may be present. This does not emulate 0.15 M.
- Only inserted-state setup/validation is attempted. Pulling and adsorbed/solvent states are outside this experiment.

## Commands and outputs

Elapsed: 2.65 s; aggregate output: 23075534 bytes; atom count: None; MD step cap: 50000 at 0.002 ps (100 ps).

See `validation.json` for downloaded/input hashes, exact commands, stdout/stderr, and per-file output hashes.

## Interpretation

No scientific result is reported. Inspect the recorded command output and partial artifacts.

This local 100-ps validation cannot reproduce 70-ns equilibration plus 150-ns production, establish independent-seed uncertainty, or support a biological agreement score.
