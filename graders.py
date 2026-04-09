# graders.py

from typing import List, Dict, Any

# Strict safe bounds — scores will ALWAYS land inside (0, 1)
MIN_VALID_SCORE = 0.05
MAX_VALID_SCORE = 0.95


def clamp_score(raw_score: float) -> float:
    """
    Clamp any raw score into the strict open interval (0, 1).
    Guarantees: MIN_VALID_SCORE <= result <= MAX_VALID_SCORE
    which means 0.05 <= result <= 0.95, so never 0 and never 1.
    """
    try:
        val = float(raw_score)
    except (TypeError, ValueError):
        return MIN_VALID_SCORE

    if val <= MIN_VALID_SCORE:
        return MIN_VALID_SCORE
    if val >= MAX_VALID_SCORE:
        return MAX_VALID_SCORE

    return val


class ScoreGrader:
    """
    OpenEnv-compatible grader.
    Extracts final progress from the trajectory and clamps it
    into the safe (0, 1) interval.
    """

    def grade(self, trajectory: List[Dict[str, Any]], **kwargs) -> float:
        if not trajectory:
            return clamp_score(MIN_VALID_SCORE)

        final_step = trajectory[-1]

        # Safely extract progress regardless of whether final_step is dict or object
        progress = MIN_VALID_SCORE
        try:
            if isinstance(final_step, dict):
                final_state = final_step.get(
                    "state", final_step.get("observation", final_step)
                )
                if isinstance(final_state, dict):
                    progress = final_state.get("progress", MIN_VALID_SCORE)
                else:
                    progress = getattr(final_state, "progress", MIN_VALID_SCORE)
            else:
                final_state = getattr(
                    final_step,
                    "state",
                    getattr(final_step, "observation", final_step),
                )
                if isinstance(final_state, dict):
                    progress = final_state.get("progress", MIN_VALID_SCORE)
                else:
                    progress = getattr(final_state, "progress", MIN_VALID_SCORE)
        except Exception:
            progress = MIN_VALID_SCORE

        return clamp_score(float(progress) if progress is not None else MIN_VALID_SCORE)


def default_grader(trajectory, **kwargs) -> float:
    """Entry point called by the validator via openenv.yaml."""
    return ScoreGrader().grade(trajectory, **kwargs)
