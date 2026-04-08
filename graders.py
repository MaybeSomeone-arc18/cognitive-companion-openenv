# graders.py

from typing import List, Dict, Any

MIN_VALID_SCORE = 0.1
MAX_VALID_SCORE = 0.9


def safe_task_score(raw: float) -> float:
    """
    Map a raw performance signal to a dynamic, safe task score:
    raw (bounded by +/- MAX_VALID_SCORE) -> normalized safe span -> clamped safe score.
    """
    try:
        raw_val = float(raw)
    except (TypeError, ValueError):
        raw_val = -MAX_VALID_SCORE
    bounded_raw = max(-MAX_VALID_SCORE, min(raw_val, MAX_VALID_SCORE))
    normalized = (bounded_raw + MAX_VALID_SCORE) / (2.0 * MAX_VALID_SCORE)
    score = MIN_VALID_SCORE + ((MAX_VALID_SCORE - MIN_VALID_SCORE) * normalized)
    score = max(MIN_VALID_SCORE, min(score, MAX_VALID_SCORE))
    assert MIN_VALID_SCORE <= score <= MAX_VALID_SCORE
    return score


def clamp_score(raw_score: float) -> float:
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = MIN_VALID_SCORE
    score = max(MIN_VALID_SCORE, min(score, MAX_VALID_SCORE))
    assert MIN_VALID_SCORE <= score <= MAX_VALID_SCORE
    return score


class ScoreGrader:
    def grade(self, trajectory: List[Dict[str, Any]], **kwargs) -> float:
        raw_score = MIN_VALID_SCORE
        if not trajectory:
            return clamp_score(raw_score)

        final_step = trajectory[-1]
        
        # Safely extract progress regardless of if final_step is dict or object
        progress = MIN_VALID_SCORE
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
            progress = MIN_VALID_SCORE

        raw_score = float(progress or MIN_VALID_SCORE)
        return safe_task_score(raw_score)


def default_grader(trajectory, **kwargs) -> float:
    raw_score = ScoreGrader().grade(trajectory, **kwargs)
    return safe_task_score(raw_score)
