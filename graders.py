import json

EPS = 1e-3  # small margin so scores are strictly between 0 and 1

def clamp_score(raw_score: float, eps: float = EPS) -> float:
    """
    Clamp a raw score in [0, 1] to be strictly within (0, 1).
    """
    return max(eps, min(1.0 - eps, raw_score))

class ScoreGrader:
    def grade(self, trajectory: list) -> float:
        """
        An OpenEnv-compatible grader.
        Takes a full trajectory history (list of step dictionaries) and extracts the score.
        For Cognitive Companion, the normalized 0.0 to 1.0 score maps perfectly to the 
        final 'progress' achieved in the session.
        """
        if not trajectory:
            # Previously 0.0, now a tiny >0 value
            return clamp_score(0.0)
            
        final_step = trajectory[-1]
        final_state = final_step.get("state", {})
        progress = final_state.get("progress", 0.0)
        
        # Ensure bounds mapping explicitly, then clamp to (0, 1)
        raw_score = float(max(0.0, min(1.0, progress)))
        return clamp_score(raw_score)

# Utility mapping for runner
def default_grader(trajectory) -> float:
    return ScoreGrader().grade(trajectory)
