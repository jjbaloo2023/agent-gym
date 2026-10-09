# Container workflow

Docker Desktop must be running in Linux-container mode. A separate Ubuntu WSL distribution is optional for these commands. Run from the repository root in PowerShell or a Linux shell.

## Build and verify
```sh
docker compose build
docker compose run --rm --entrypoint python gym -m unittest discover -s tests -v
```
The image pins the official Python 3.13 slim base by digest. Source and tests are copied into the image; rebuild after changes. There are no runtime third-party Python dependencies.

## Run and resume
```sh
docker compose run --rm gym --run-dir /data/demo --steps 40
docker compose run --rm gym --run-dir /data/demo --steps 80 --resume
docker compose run --rm gym --run-dir /data/batch --steps 80 --replicas 4 --workers 2
```
These are disposable containers sharing persistent storage. Choose a new run directory for each experiment; existing checkpoints require --resume. Only one container may write a given run directory at a time.

## Inspect or export
Open a shell in the built environment:
```sh
docker compose run --rm --entrypoint sh gym
```
Inside it, inspect /data/demo/checkpoint.json. Exit with exit.

Export to the host using a temporary stopped container:
```sh
docker compose create gym
docker compose cp gym:/data ./artifacts/container-runs
docker compose rm -f gym
```
Create the host artifacts directory first if needed. Exports are ignored by Git.

## Boundaries and resources
Compose limits each container to two CPU equivalents, 2 GiB RAM with no additional swap, and 128 processes. It runs as a non-root user with a read-only root filesystem, no network, dropped capabilities, and temporary /tmp storage. Python multiprocessing can use shared memory provided by Docker.

The agent-gym_gym-runs named volume lives in Docker-managed Linux storage, outside the repository and OneDrive. Container removal and image rebuilds preserve it. docker compose down preserves it; adding --volumes deletes its checkpoints. Back up important artifacts before any volume deletion or Docker reset.

These are per-container limits. Multiple containers multiply resource use. Start with one container and two workers on this laptop. Docker/WSL global resource settings are independent and have not been changed.

This configuration runs the analytical baseline. It does not implement a sandbox suitable for arbitrary hostile agent code, external solver adapters, or API connectivity. Add narrowly scoped networking and credentials when implementing provider adapters. CAD/OpenFOAM will get separately versioned images rather than changing the analytical task's dependencies.
