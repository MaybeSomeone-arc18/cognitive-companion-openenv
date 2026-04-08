# graders.py

from typing import List, Dict, Any

MIN_VALID_SCORE = 0.01
MAX_VALID_SCORE = 0.99


def clamp_score(raw_score: float) -> float:
    try:
        val = float(raw_score)
    except (TypeError, ValueError):
        return MIN_VALID_SCORE
    if val < MIN_VALID_SCORE:
        return MIN_VALID_SCORE
    if val > MAX_VALID_SCORE:
        return MAX_VALID_SCORE
    return val


class ScoreGrader:
    def grade(self, trajectory: List[Dict[str, Any]], **kwargs) -> float:
        raw_score = 0.0
        if not trajectory:
            return clamp_score(raw_score)

        final_step = trajectory[-1]
        
        # Safely extract progress regardless of if final_step is dict or object
        progress = 0.0
        try:
            if isinstance(final_step, dict):
                final_state = final_step.get("state", final_step.get("observation", final_step))
                if isinstance(final_state, dict):
                    progress = final_state.get("progress", 0)
                else:
                    progress = getattr(final_state, "progress", 0)
            else:
                final_state = getattr(final_step, "state", getattr(final_step, "observation", final_step))
                if isinstance(final_state, dict):
                    progress = final_state.get("progress", 0)
                else:
                    progress = getattr(final_state, "progress", 0)
        except Exception:
            progress = 0.0

        raw_score = float(progress or 0.0)
        return clamp_score(raw_score)


def default_grader(trajectory, **kwargs) -> float:
    raw_score = ScoreGrader().grade(trajectory, **kwargs)
    return clamp_score(raw_score)
