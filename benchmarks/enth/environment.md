# Verified CPU environment

Verified 2026-10-09 on Ubuntu-24.04 WSL as user gym.

- Installed Ubuntu package gromacs=2023.3-1ubuntu3 with apt (12 packages; approximately 429 MB installed).
- `/usr/bin/gmx --version` succeeds: mixed precision, thread-MPI, OpenMP, SSE4.1, FFTW; GPU support disabled.
- WSL reported approximately 7.6 GiB RAM. Existing CAD and CFD environments remain separate.
- A transient systemd service successfully ran GROMACS as gym with CPUQuota=200%, MemoryMax=4G, MemorySwapMax=0, TasksMax=64 and RuntimeMaxSec=30. Reported peak memory was 4.4 MB and exit status was zero.

Recheck installed build:

```powershell
wsl -d Ubuntu-24.04 -u root -- bash -lc 'systemd-run --wait --pipe --collect -p User=gym -p CPUQuota=200% -p MemoryMax=4G -p MemorySwapMax=0 -p RuntimeMaxSec=30 -p TasksMax=64 /usr/bin/gmx --version'
```

The systemd service provides a process-group resource boundary, not an agent security sandbox. For a real pilot, wrap the entire sequential workflow in one service with RuntimeMaxSec=1800; use OMP_NUM_THREADS=2 and explicit GROMACS thread options. Run artifacts should live outside OneDrive in a dedicated gym-owned WSL directory and be exported with hashes afterward.

Verified through validation-007 on 2026-10-10: reconstructed ENTH/POPC/SAPI24 preparation, CHARMM36 topology conversion, bounded CPU trajectory generation, checkpoint continuation, independent energy/membrane analysis and a DSSP positive control. The retry saved 28 ps; its checkpoint reached 28.4 ps. Available partial-run physical checks passed, while the planned 100 ps did not complete. This is not a reproduction of the paper.

The worker enforces the atom/MD-step and 20-scientific-subprocess limits and persists a command ledger. The supervisor monitors aggregate output every 0.5 seconds, sets a 256 MiB per-file limit, and preserves source snapshots and hashes. Aggregate output is monitored rather than protected by a filesystem quota. Systemd enforces CPU, memory and process-tree time limits. The retry's continuations received only the time remaining from the original start; total elapsed time was 1,749.98 seconds. [The provenance audit](evidence/validation-007/provenance-audit.json) and [the full result](validation-results.md) document the executed boundary and its limitations.

Reference installation guidance: https://manual.gromacs.org/2024.2/install-guide/index.html . The installed distro build is deliberately recorded rather than presented as the newest GROMACS release.
