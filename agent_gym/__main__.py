import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
from .core import run

def main():
    parser = argparse.ArgumentParser(description="Run analytical scientific agent baseline")
    parser.add_argument("--run-dir", type=Path, default=Path("runs/demo"))
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if min(args.steps, args.replicas, args.workers) < 1:
        parser.error("steps, replicas and workers must be positive")
    try:
        if args.replicas == 1:
            results = [run(args.run_dir, args.steps, args.seed, args.resume)]
        else:
            with ProcessPoolExecutor(max_workers=min(args.workers, args.replicas)) as pool:
                futures = [pool.submit(run, args.run_dir / f"seed-{args.seed + i}",
                                       args.steps, args.seed + i, args.resume)
                           for i in range(args.replicas)]
                results = [future.result() for future in futures]
    except (ValueError, FileExistsError, FileNotFoundError) as error:
        parser.error(str(error))
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
