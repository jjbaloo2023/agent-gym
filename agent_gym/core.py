"""A bounded analytical environment and resumable baseline; no external tools."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import sys
import tempfile
import time

BASELINE = "radius-hill-climb-v1"

@dataclass(frozen=True)
class PipeTask:
    length_m: float = 1.0
    viscosity_pa_s: float = 0.001
    density_kg_m3: float = 1000.0
    flow_m3_s: float = 1e-6
    target_drop_pa: float = 4.0
    min_radius_m: float = 0.003
    max_radius_m: float = 0.02
    initial_radius_m: float = 0.012

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError("Task values must be finite and positive")
        if not self.min_radius_m <= self.initial_radius_m <= self.max_radius_m:
            raise ValueError("Initial radius must be within bounds")

    def evaluate(self, radius):
        if not math.isfinite(radius) or not self.min_radius_m <= radius <= self.max_radius_m:
            return {"valid": False, "reason": "radius outside finite bounds", "reward": -1.0}
        drop = 8 * self.viscosity_pa_s * self.length_m * self.flow_m3_s / (math.pi * radius**4)
        reynolds = 2 * self.density_kg_m3 * self.flow_m3_s / (math.pi * self.viscosity_pa_s * radius)
        if reynolds >= 2000:
            return {"valid": False, "reason": "outside conservative laminar regime", "reward": -1.0}
        error = abs(math.log(drop / self.target_drop_pa))
        return {"valid": True, "pressure_drop_pa": drop, "reynolds": reynolds,
                "log_error": error, "reward": 1 / (1 + error)}

def task_hash(task):
    return hashlib.sha256(json.dumps(asdict(task), sort_keys=True).encode()).hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".checkpoint-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        # Windows sync/indexing software can briefly lock the destination.
        for attempt in range(7):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 6:
                    raise
                time.sleep(0.02 * 2**attempt)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def tuples(value):
    return tuple(tuples(v) for v in value) if isinstance(value, list) else value

class PipeEnv:
    """Small reset/step contract. Not a Gymnasium subclass."""
    def __init__(self, task=None, budget=40):
        if not isinstance(budget, int) or budget < 1:
            raise ValueError("Budget must be a positive integer")
        self.task = task or PipeTask()
        self.budget = budget
        self.reset()

    def reset(self):
        self.steps = 0
        self.radius = self.task.initial_radius_m
        self.metrics = self.task.evaluate(self.radius)
        return self.observe()

    def observe(self):
        return {"radius_m": self.radius, "metrics": dict(self.metrics),
                "steps": self.steps, "remaining": self.budget - self.steps,
                "target_drop_pa": self.task.target_drop_pa,
                "bounds_m": [self.task.min_radius_m, self.task.max_radius_m]}

    def step(self, radius):
        if self.steps >= self.budget:
            raise RuntimeError("Episode budget exhausted")
        candidate = self.task.evaluate(radius)
        accepted = candidate["valid"] and candidate["reward"] > self.metrics["reward"]
        if accepted:
            self.radius, self.metrics = radius, candidate
        self.steps += 1
        return self.observe(), candidate["reward"], self.steps == self.budget, {
            "accepted": accepted, "candidate": candidate}

def run(run_dir, steps=40, seed=0, resume=False, task=None):
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("Steps must be a positive integer")
    task = task or PipeTask()
    if not task.evaluate(task.initial_radius_m)["valid"]:
        raise ValueError("Initial state must be physically valid")
    path = Path(run_dir) / "checkpoint.json"
    env = PipeEnv(task, steps)
    rng = random.Random(seed)
    if resume:
        state = json.loads(path.read_text(encoding="utf-8"))
        if (state["schema_version"] != 1 or state["task_hash"] != task_hash(task)
                or state["baseline"] != BASELINE or state["seed"] != seed):
            raise ValueError("Checkpoint configuration mismatch")
        if steps < state["steps"]:
            raise ValueError("Cannot reduce budget below completed steps")
        env.steps, env.radius = state["steps"], state["radius_m"]
        env.metrics = task.evaluate(env.radius)
        rng.setstate(tuples(state["rng_state"]))
    else:
        if path.exists():
            raise FileExistsError("Run exists; use --resume or a new directory")
        state = {"schema_version": 1, "task": asdict(task), "task_hash": task_hash(task),
                 "baseline": BASELINE, "seed": seed,
                 "provenance": {"source": "deterministic_baseline",
                                "training_eligibility": "unreviewed"},
                 "runtime": {"python": sys.version, "platform": platform.platform()},
                 "history": []}

    def save():
        state.update(steps=env.steps, radius_m=env.radius, metrics=env.metrics,
                     rng_state=rng.getstate())
        atomic_json(path, state)

    save()
    while env.steps < steps:
        # Decay by absolute episode index so split and uninterrupted runs agree.
        scale = 0.35 / math.sqrt(1 + env.steps / 10)
        radius = env.radius * math.exp(rng.uniform(-scale, scale))
        _, reward, _, info = env.step(radius)
        state["history"].append({"step": env.steps, "radius_m": radius,
                                 "reward": reward, **info})
        save()
    return {"run_dir": str(run_dir), "steps": env.steps,
            "radius_m": env.radius, **env.metrics}
