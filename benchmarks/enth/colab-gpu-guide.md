# Running the ENTH benchmark on a Colab GPU

## Execution status

Updated2026-10-11. **Real GPU validation completed successfully** in the manual Colab notebook. It ran100ps NVT,500ps restrained NPT and100ps released NPT (700ps total dynamics), using GROMACS2026.4/CUDA13 on a T4. The released segment reported24.147ns/day. The saved notebook report has been extracted locally. Colab subsequently expired; reconnection explicitly confirmed that the validation directory, checkpoint and GROMACS executable were gone. No long equilibration was launched, and no binary trajectory/checkpoint transfer was confirmed. This is a passed short GPU validation with lost binary state, not a completed paper reproduction.

Notebook: [ENTH corrected GPU simulation](https://colab.research.google.com/drive/1W8Tw4ml0GNN6bkT97n9v2csIg55SmKe4).

## What the GPU run is testing

The scientific target is Figure 4 in [Joseph et al., Communications Biology (2020)](https://www.nature.com/articles/s42003-020-01471-6): how ENTH H0 helicity differs between membrane-inserted, adsorbed and solvent configurations. The published protocol used 70 ns equilibration and 150 ns production per configuration, with secondary structure measured over the last 100 ns. The paper acknowledges computing clusters but does not give a CPU core count.

The immediate GPU job is an inserted-state reconstruction and validation. A longer trajectory of that state alone cannot reproduce the three-state comparison or show lipid-induced folding from an initially helical crystal structure. Original CHARMM-GUI inputs, numerical pulling constants and exact state definitions were not available. Those uncertainties must remain visible in the interpretation.

## Hardware and runtime

The signed-in account allocated a Tesla T4 with 15,360 MiB GPU memory, two CPU cores and about 12.67 GB system memory. Its driver reported 580.82.07 and its CUDA compiler reported 13.0.88. These observations describe this allocation; Colab can assign different hardware in a later session. Premium GPU options were disabled in this account's selector. No subscription or compute-unit purchase was made.

The GPU accelerates expensive force calculations; CPU threads still coordinate work and perform tasks that remain on the CPU. Selecting a GPU in Colab does not automatically make a CPU-only GROMACS binary use it. Verify both the executable's build information and the simulation log's GPU task assignments.

Google's [Colab FAQ](https://research.google.com/colaboratory/faq.html) describes dynamic availability and session limits: free notebooks can run at most 12 hours depending on availability and usage; Pro+ can support up to 24 hours with sufficient compute units. These are maximums, not uninterrupted-runtime guarantees. Notebook code and outputs can be saved while runtime files remain ephemeral.

## Installing GROMACS with CUDA

The local pilot used Ubuntu's CPU-only GROMACS 2023.3. The Colab build uses the official GROMACS 2026.4 source, selected for the current CUDA 13 environment. This version change is recorded; numerical trajectories are not expected to match the local CPU trajectory bit for bit.

The notebook installs standard build tools and FFTW through Ubuntu apt, downloads the source from the [official release location](https://manual.gromacs.org/documentation/current/download.html), checks its published MD5 for transfer integrity and records SHA256 for provenance. It builds into `/content/enth-gpu/install`, leaving the source and logs under `/content/enth-gpu`.

Key CMake settings:

```text
-DGMX_GPU=CUDA
-DGMX_CUDA_TARGET_SM=75
-DGMX_CUDA_TARGET_COMPUTE=75
-DGMX_MPI=OFF
-DGMX_THREAD_MPI=ON
-DGMX_OPENMP=ON
-DGMX_BUILD_UNITTESTS=ON
-DGMX_FFT_LIBRARY=fftw3
-DCMAKE_BUILD_TYPE=Release
```

SM 75 targets the allocated T4. Thread-MPI supports this single-machine job; external MPI is unnecessary for a single Colab runtime. Two build jobs limit compilation load. The [GROMACS installation guide](https://manual.gromacs.org/documentation/current/install-guide/index.html) documents GPU and parallelization options.

After installation, run `/content/enth-gpu/install/bin/gmx --version` and retain its complete output. A successful build is only an installation check; it does not validate force-field parameters or molecular dynamics.

The initial configuration with unit-test targets disabled failed in the release's NB-LIB test linking rules. The retry enables upstream unit-test targets; the failed configure log is preserved. No simulation settings were changed to resolve this build problem.

## Corrected scientific inputs

The earlier 007 pilot had 112 POPCs plus one PIP2, and geometrically placed PIP2 rather than preserving its crystallographic binding pose. Its clean partial trajectory is retained as historical evidence. New preparation preserves the full PIP2 headgroup at the bound crystallographic I3P coordinates using an explicit atom map, and contains the paper's upper 99 POPC + one PIP2 and lower 100 POPC composition. The accepted preparation has 78,954 atoms and an 8.264381-nm square membrane, corresponding to 68.3 ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â² per lipid. Independent checks find 36.56 ÃƒÆ’Ã¢â‚¬Â¦ leaflet separation and zero intermolecular heavy-atom pairs below 1.8 ÃƒÆ’Ã¢â‚¬Â¦. The 24 mapped crystal headgroup heavy atoms have 0.00476 ÃƒÆ’Ã¢â‚¬Â¦ RMSD after GRO rounding. H0 proxy CÃƒÅ½Ã‚Â± positions span ÃƒÂ¢Ã‹â€ Ã¢â‚¬â„¢4.48 to +5.01 ÃƒÆ’Ã¢â‚¬Â¦ relative to the upper phosphate plane; PIP2 tail termini average ÃƒÂ¢Ã‹â€ Ã¢â‚¬â„¢15.77 ÃƒÆ’Ã¢â‚¬Â¦. These are starting-geometry checks, not MD validation.

The portable archive is `artifacts/enth/colab-input-010-portable.tar.gz` (13,715,543 bytes), SHA256 `dfb0d6eb2ea4a54b4b5dc225a678b28147bfc9585485b7dfd6568f89224814a1`. Earlier candidates and the archive with absolute topology paths are preserved but superseded.

The reconstruction retains explicit water, CHARMM36, 303.15 K and 1 bar. The paper's reported 0.15 mM KCl remains literal; it is not silently replaced with 0.15 M. PIP2 protonation and the provisional H0 residue mapping are recorded assumptions. Exact membrane packing and equilibration remain reconstruction choices.

## Transfer and provenance

Only the simulation bundle is transferred to Colab. It must contain coordinates, topology and include files, the force field, MDP settings and preparation metadata; checkpoint continuation additionally needs its matching TPR and checkpoint. A manifest records file sizes and SHA256 hashes. Verify hashes after upload and extract into a new run directory. Preserve all earlier evidence.

Run from Colab's local `/content` disk, rather than continuously reading trajectories from mounted Drive. Save durable checkpoint copies separately. Do not assume a saved notebook contains the runtime's binary files.

## Validation before a long run

1. Preprocess without overriding warnings with `-maxwarn`.
2. Relax starting contacts and require minimization convergence. Check constraints separately before dynamics; increasing LINCS tolerances to conceal bad geometry is not a repair.
3. Perform a 100-ps restrained NVT ramp from 100 to 303.15 K, 500-ps restrained NPT, then 100-ps released NPT validation. The ramp endpoint changes with its duration; merely extending nsteps would retain the old 10-ps heating schedule.
4. Confirm GPU use in the actual mdrun log and check utilization while it runs.
5. Inspect every stage for constraint warnings and fatal errors. Check finite energies, temperature, volume and leaflet geometry. Pressure fluctuations over a short segment do not establish equilibration.
6. Read the trajectory with `gmx check` and measure observed time explicitly. A successful process exit does not mean the requested duration completed.
7. Validate the secondary-structure analysis against the starting structure before interpreting H0 occupancy.

## Measuring GPU speed

Use the `Performance` line reported by mdrun after a sufficiently long benchmark. Record system size, GROMACS version, GPU model, task assignments and wall time with it. The local two-core pilot varied around 1.6ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ3.25 ns/day; its final released segment reported 2.624 ns/day. Those numbers are baselines, not a promised GPU speedup.

For measured speed `S` ns/day, estimated wall days are `simulation_ns / S`. The paper's 220 ns per state would take `220 / S` days; three states would take `660 / S` days if run sequentially at the same speed, before replicas and preparation. Short benchmark estimates can change during a longer job.

## Checkpoints and restart

GROMACS checkpoints preserve simulation state, including velocities and coupling state. Resume with the correct TPR and `-cpi`; do not generate fresh velocities and call it a continuation. Use `convert-tpr` to change a run endpoint when appropriate, and record that change. `-noappend` creates separately numbered output parts; `-append` requires the matching existing output files and their checksums.

Bound each session below Colab's expected maximum and request a graceful stop early enough to write a checkpoint. Save checkpoints and the corresponding inputs to durable storage during the session, not only at the end. Abrupt runtime loss can still lose progress since the last durable copy. No keep-alive or timeout-bypass mechanism is part of this workflow. The [long-simulation guide](https://manual.gromacs.org/documentation/current/user-guide/managing-simulations.html) explains restart behavior.

## Analysis and claims

Report residue-wise helix occupancy, membrane-relative insertion depth and contact behavior with their definitions. Correct for periodic boundaries and align to the membrane. The provisional first-18-residue H0 proxy is not a confirmed paper-specific mapping. The local pilot required DSSP's hydrogen-reconstruction mode to pass its structural positive control; recheck that behavior with the Colab GROMACS version.

Passing installation, a clean short trajectory and a completed long trajectory are separate outcomes. A stable inserted trajectory remains a single-state result. Reproducing the published ordering requires defensible adsorbed and solvent setups, comparable equilibration and sampling, independent seeds and uncertainty estimates. A disagreement from an approximate reconstruction must not be attributed to the model or biology without resolving setup differences.

## Exact GPU execution and session bounds

The executable in the replacement session is built with `cmake --build /content/enth-gpu/build --target gmx --parallel 2` and used directly at `/content/enth-gpu/build/bin/gmx`. Building only the executable target avoids compiling every upstream unit-test executable; their CMake targets remain enabled to satisfy this release's configuration. This does **not** claim upstream tests were run. The first allocation completed a full build and install; its files were lost on disconnect. The clean replacement records its own build logs.

The supervisor is `scripts/run-enth-colab.py`, with `scripts/enth_analysis.py` alongside it. It regenerates every TPR using Colab's installed GROMACS, without `-maxwarn`. Supplied preflight TPRs were made locally with 2023.3 and are provenance, not executable inputs for the new job.

For dynamics it requests:

```bash
gmx mdrun -s validation.tpr -deffnm validation \
  -ntmpi 1 -ntomp 2 -pin off \
  -nb gpu -pme gpu -bonded auto -update cpu -gpu_id 0 -cpt 5
```

Nonbonded and PME work are assigned to the T4; updates and constraints remain on CPU. Bonded work is selected by GROMACS. Steepest-descent minimization instead uses `-pme cpu`, because PME GPU offload is unsupported for that integrator. GPU selection is an execution choice, not a change to temperature, pressure or force-field parameters.

The validation command is:

```bash
python /content/run-enth-colab.py \
  --inputs /content/enth-gpu/enth-colab/run \
  --output /content/enth-gpu/gpu-validation-010 \
  --durable /content/enth-gpu/validation-backups \
  --gmx /content/enth-gpu/build/bin/gmx \
  --hours 1.5 --validate-only
```

Here `validation-backups` is session-local, despite the CLI argument name. It provides recovery within that runtime only; the validation evidence must be downloaded. For a long job, `--durable` must instead point to persistent storage, such as an authorized Drive mount. Mounting Drive gives the Colab runtime broad Drive access; it is a separate access decision from uploading these simulation files.

After a passed validation, `--continue-validated` accepts that complete checkpoint/output directory as `--inputs`, writes a new output directory, preserves its parent report and begins longer equilibration without repeating minimization or generating velocities. Long output is sampled every 100 ps. The first released 100 ps is the validation origin; the additional target is 70 ns. Each continuation extends the endpoint using `convert-tpr` and resumes the same checkpoint with `-cpi -append`. Simulation time and coupling state remain continuous.

The long session is limited to eight hours, one T4, two OpenMP threads and 2 GiB of combined working plus checkpoint files. The source build and uploaded input archive are separate preparation artifacts. Colab's system-memory quota applies; this GPU runner does not claim the local pilot's 4-GiB memory enforcement. The supervisor requests a graceful stop before its deadline and force-stops a process that fails to exit. It stops on LINCS/constraint/fatal errors, nonfinite values, implausible temperature/volume or failed starting-validation membrane checks. Broad sanity bands do not establish equilibrium.

GROMACS writes a local checkpoint every five minutes; the supervisor periodically copies an available checkpoint and its TPR, verifies the checkpoint stayed unchanged during copying, and marks incomplete copies unusable. Stage boundaries and one-ns continuation boundaries produce additional hashed snapshots. Periodic checkpoint-only backups support state restart with `-noappend`; they do not contain the complete earlier trajectory. Full validation and final snapshots include trajectories and energies. Separate, unique job directories preserve earlier evidence.

If free Colab expires before 70 ns, report the actual saved time and resume later. Do not interpret an eight-hour process as eight hours of molecular simulation. Installation, warmup and MD have separate wall times. No paid compute purchase, automatic subscription, timeout bypass or keep-alive is included.

## Long-run launch after both gates pass

The final notebook cell is prepared but deliberately unexecuted. It first checks a mounted persistent Drive, an accepted `short_gpu_validation_completed` report, and the uploaded long-run script's SHA256. It creates a unique timestamped job folder and launches:

```bash
python /content/run-enth-colab-long.py \
  --inputs /content/enth-gpu/gpu-validation-010 \
  --output /content/enth-gpu/enth-010-TIMESTAMP \
  --durable /content/drive/MyDrive/Agent_gym/ENTH/enth-010-TIMESTAMP \
  --gmx /content/enth-gpu/build/bin/gmx \
  --hours 8 --target-ns 70 --continue-validated
```

The reviewed long-run script SHA256 is `2eefdbd34a076ae4be037423a11444e85c62520ec7ad20ea59e6f99dc65733b6`. The validation script is a separately retained earlier revision; the long revision adds checkpoint continuation and completed-stage restart snapshots. Both require the uploaded `enth_analysis.py` module.

Read `colab-run.json` for actual status, each command's exit code, completed times, temperature/volume statistics, leaflet/contact checks and the final reason for stopping. Read the mdrun log for task assignments and measured `Performance` lines. A still-running background process will not keep producing new notebook output automatically; inspect the job files using a monitoring cell. Background execution does not prevent Colab from terminating a runtime.

For a checkpoint-only recovery, combine the selected verified checkpoint and matching TPR with the static `inputs` snapshot. Start in a new directory and use `gmx mdrun -s extended.tpr -cpi validation.cpt -noappend` with the recorded GPU/thread flags. Preserve output parts from every earlier session separately. If recovering the complete final output set, `-append` is possible only when GROMACS verifies the recorded file checksums. Never mix a checkpoint from validation-007 with this new 010 reconstruction.

## Evidence available so far

| Gate | Observed outcome |
|---|---|
| T4 allocation | Passed in two sessions;15,360 MiB GPU memory |
| First CUDA GROMACS build | Passed;2026.4 with CUDA13 and SM75 |
| Original session lifetime | Disconnected before ENTH MD;runtime files lost |
| Corrected portable geometry/topology | Passed independent preparation/preprocessing checks |
| Transfer | Archive and all60 extracted hashes verified in replacement session |
| Runner regressions |38 tests passed, including9 fake-engine failure/continuation tests |
| Corrected-system minimization and GPU MD | Passed:700ps total dynamics, including100ps released validation |
| GPU ns/day |24.147 reported for the100ps released validation;short benchmark estimate |
| Eight-hour equilibration |Not launched;binary state lost on expiry, persistent storage still required |
| Paper's three-state biological comparison |Not tested |

The CPU pilot and the corrected GPU reconstruction differ in atom count, membrane composition and binding-pose handling. Even after GPU speed is measured, their raw ns/day ratio is not a controlled hardware speedup benchmark. A fair speed comparison requires the same corrected TPR and comparable workload on CPU and GPU.

## Overnight takeover: observed physical results

The report is saved locally as `benchmarks/enth/evidence/colab-takeover-010/validation-observed.json`, extracted from the saved notebook output. Its raw browser observation is retained at `artifacts/enth/colab-takeover-observed.txt`. This is recovered textual evidence; complete logs, energies, trajectories and binary checkpoint files were not recovered independently.

All12 scientific subprocesses returned0. Both minimizations passed the runner's Fmax convergence gate. No LINCS/constraint/fatal error gate fired. Actual mdrun output assigned both PP short-range work and all PME aspects to the GPU. The700ps warmup/validation completed in2,976.943seconds, excluding compilation. The released100ps had501 energy samples: mean303.300K, range300.133–306.130K, volume755.566→762.972nm³ (+0.980%). The final geometry retained exactly99POPC+1PIP2 above and100POPC below, phosphate separation37.283Å, and zero audited intermolecular heavy pairs below1.8Å. These remain broad stability checks, not equilibrium or helicity-reproduction evidence.

At24.147ns/day, eight hours corresponds to approximately8.05ns,70ns to69.6wall hours, and220ns per state to9.11days. These extrapolations exclude compilation/preparation, interruptions and performance changes. The initial100ps validation alone cannot establish the paper's behavior.

The browser's download event did not confirm either download attempt; the direct file-pane operation stalled the controller for hours. Do not rely on automatic browser downloads for unattended durability in this environment. The long run was correctly left unlaunched after the accepted checkpoint became unavailable. Resolve persistent storage before repeating the validation and launching longer work.
