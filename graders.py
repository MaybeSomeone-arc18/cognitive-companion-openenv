# graders.py

import json
from typing import List, Dict, Any

MIN_VALID_SCORE = 0.002   # 0.2%
MAX_VALID_SCORE = 0.998   # 99.8%


def clamp_score(raw_score: float) -> float:
    """
    Clamp any raw score so that MIN_VALID_SCORE < score < MAX_VALID_SCORE.
    """
    try:
        val = float(raw_score)
    except (TypeError, ValueError):
        val = 0.0

    # First bound into [0, 1]
    if val < 0.0:
        val = 0.0
    elif val > 1.0:
        val = 1.0

    # Then enforce strict interior using the given min/max
    if val <= 0.0:
        return MIN_VALID_SCORE
    if val >= 1.0:
        return MAX_VALID_SCORE

    # If already strictly inside (0,1), still bound to [MIN_VALID_SCORE, MAX_VALID_SCORE]
    if val < MIN_VALID_SCORE:
        return MIN_VALID_SCORE
    if val > MAX_VALID_SCORE:
        return MAX_VALID_SCORE

    return val


class ScoreGrader:
    def grade(self, trajectory: List[Dict[str, Any]]) -> float:
        """
        OpenEnv-compatible grader.

        Uses the final state's 'progress' as base score, then clamps it
        into (MIN_VALID_SCORE, MAX_VALID_SCORE).
        """
        if not trajectory:
            raw_score = 0.0
            return clamp_score(raw_score)

        final_step = trajectory[-1] or {}
        final_state = final_step.get("state", {}) or {}

        progress = final_state.get("progress", 0.0)
        raw_score = float(progress)

        final_score = clamp_score(raw_score)
        return final_score


def default_grader(trajectory) -> float:
    return ScoreGrader().grade(trajectory)
