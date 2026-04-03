import json

class ScoreGrader:
    def grade(self, trajectory: list) -> float:
        """
        An OpenEnv-compatible grader.
        Takes a full trajectory history (list of step dictionaries) and extracts the score.
        For Cognitive Companion, the normalized 0.0 to 1.0 score maps perfectly to the 
        final 'progress' achieved in the session.
        """
        if not trajectory:
            return 0.0
            
        final_step = trajectory[-1]
        final_state = final_step.get("state", {})
        progress = final_state.get("progress", 0.0)
        
        # Ensure bounds mapping explicitly
        return float(max(0.0, min(1.0, progress)))

# Utility mapping for runner
def default_grader(trajectory) -> float:
    return ScoreGrader().grade(trajectory)
