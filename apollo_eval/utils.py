import json
import os


def lookup(run_id: str, position_index: int, trajectory_dir: str) -> dict:
    """Load a trajectory JSON and return the turn record at the given position_index."""
    path = os.path.join(trajectory_dir, f"{run_id}.json")
    with open(path) as f:
        trajectory = json.load(f)
    for turn in trajectory["turns"]:
        if turn["position_index"] == position_index:
            return turn
    raise KeyError(
        f"No turn with position_index={position_index} in run {run_id}"
    )
