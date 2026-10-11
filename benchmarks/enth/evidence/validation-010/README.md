# Corrected ENTH Colab inputs: validation-010

This is a fresh reconstructed inserted-state system, preprocessed with GROMACS
2023.3, and **not yet energy-minimized or dynamically validated**. It is not a
Figure 4 reproduction. Do not continue the old validation-007 checkpoint.

Run from `run/`; all topology includes and the complete CHARMM36 July 2020 force
field are local. Rebuild TPRs using the installed Colab GROMACS release.
Start from `ions.gro` and `topol.top`, relax using `em_relax.mdp`, then constrained
`em.mdp`. Both must reach Fmax <1000 kJ/mol/nm without LINCS/SETTLE/fatal errors.
Only then generate NVT velocities and proceed to restrained NPT and released
equilibration. The supplied dynamic MDPs retain the short validation-007 pilot
durations and 2-ps XTC interval: the GPU runner must explicitly record longer
warmup/endpoint and sparser output settings before production-sized execution.

The system contains 99 upper POPCs plus one SAPI24 PIP2 and 100 lower POPCs.
The original 256-lipid template is repacked by translating whole lipids into an
8.264381-nm square, retaining its 68.300-A^2 nominal area per lipid. Clashing
molecules are removed to exact composition, then rigid XY repulsion removes
remaining severe contacts. Protein and PIP2 remain fixed during packing.

SAPI24 C11-C16 map to crystal I3P C1-C6 (rigid-fit RMSD 0.1404 A). Because the
template phosphate torsions differ, all 24 mapped headgroup heavy coordinates
are replaced with their crystal positions, with an explicit bijective map and
minimum-displacement equivalent-oxygen mapping. Template H vectors move with
their heavy parents; the glycerol/tails translate with the bridging oxygen and
rotate 60 degrees around P-O11. This attachment is an explicit reconstruction
choice requiring minimization. The bound protein/headgroup move together.
H0 proxy residues1-14 define the membrane-parallel axis, the protein body defines
the outward normal; residues1-18 remain the reported H0 proxy for continuity.
The H0 C-alpha range is -4.48 to +5.01 A from the upper phosphate plane, protein
body +17.26 A, PIP2 terminal tail average -15.77 A. The exact original placement,
protonation, pulling protocol and state coordinates remain unavailable.

Salt is the paper's literal0.15 mM KCl. No added pairs fit this small neutral box;
this is not0.15 M. CHARMM36 uses the inherited USE_OLD_C36 protein toggle and P4-
protonated SAPI24 (-4 charge), both documented assumptions. The full paper's
70-ns equilibration and150-ns production, three states and replica uncertainty
have not been completed. Long dynamics must retain checkpoint/provenance and
enforce the explicitly authorized cloud time/output bounds.

`provenance/` holds preprocessing command output, geometry and independent
contact/leaflet checks; `source-inputs/` holds the cached public source files.
`manifest.json` hashes every packaged file except itself. No credentials or
private user data are included. Astra reconstruction was assisted by inherited
worker code and parent orchestration; it is not an independent model trial.
