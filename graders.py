# graders.py

import json
from typing import List, Dict, Any

EPS = 1e-2  # final scores will be in [0.01, 0.99]

def clamp_score(raw_score: float, eps: float = EPS) -> float:
    """
    Clamp any raw score to be strictly within (0, 1),
    no matter what comes in.
    """
    try:
        val = float(raw_score)
    except (TypeError, ValueError):
        val = 0.0

    # First bound into [0, 1]
    val = max(0.0, min(1.0, val))
    # Then push off the edges into (0, 1)
    return max(eps, min(1.0 - eps, val))


class ScoreGrader:
    def grade(self, trajectory: List[Dict[str, Any]]) -> float:
        """
        OpenEnv-compatible grader.

        Takes a full trajectory (list of step dicts) and uses the final
        state's 'progress' as the base score, then clamps it into (0, 1).
        """
        # No trajectory → treat as worst case but not exactly 0
        if not trajectory:
            return clamp_score(0.0)

        final_step = trajectory[-1] or {}
        final_state = final_step.get("state", {}) or {}

        progress = final_state.get("progress", 0.0)

        # Whatever progress is, final returned score is strictly (0, 1)
        return clamp_score(progress)


def default_grader(trajectory) -> float:
    """
    Utility mapping for runner / OpenEnv.
    Ensures any call through this also gets (0, 1).
    """
    return ScoreGrader().grade(trajectory)
