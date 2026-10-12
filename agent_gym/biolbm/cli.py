# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
import argparse
import json
import sys
from .config import load_case


def main():
    parser = argparse.ArgumentParser(description="Lettuce-backed benchmark runner")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Validate a case without loading Torch or Lettuce")
    check.add_argument("case")
    run = sub.add_parser("run")
    run.add_argument("case")
    run.add_argument("--output", required=True, help="New output directory; existing paths are refused")
    args = parser.parse_args()
    try:
        case = load_case(args.case)
        if args.command == "check":
            result = case.estimate()
        else:
            from .runner import run
            result = run(case, args.output)
        print(json.dumps(result, indent=2))
        return 1 if result.get("benchmark_passed") is False else 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"BioLBM: {exc}", file=sys.stderr)
        return 1
