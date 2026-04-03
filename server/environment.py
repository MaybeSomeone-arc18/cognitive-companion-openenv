import random
from typing import Union
from models import State, Action, StepResult

class CognitiveCompanionEnv:
    def __init__(self):
        self.state_obj = None
        
        # Embedded Q-Learning metrics
        self.q_table = {}
        self.history = []
        self.alpha = 0.1
        self.epsilon = 0.1
        
        self.reset()
        
    def _encode_state(self, state: State) -> str:
        """
        Converts detailed continuity into standardized mapping buckets tracking
        predictive structures optimizing flat Q-tables accurately over time.
        """
        stuck_bucket = min(9, int(state.stuck_level * 10))
        progress_bucket = min(9, int(state.progress * 10))
        time_bucket = state.time_left // 5
        
        return f"{state.task_type}_{stuck_bucket}_{progress_bucket}_{time_bucket}"
        
    def _get_q_values(self, encoded_state: str) -> dict:
        """Retrieve Q-values safely generating absolute 0.0 presets."""
        if encoded_state not in self.q_table:
            self.q_table[encoded_state] = {"continue": 0.0, "intervene": 0.0, "switch_task": 0.0}
        return self.q_table[encoded_state]

    def reset(self, difficulty: str = "medium", clear_qtable: bool = False) -> State:
        # Prevent wiping tables unintentionally leaving baseline tracking
        if clear_qtable:
            self.q_table = {}
            self.history = []
            
        if difficulty == "easy":
            stuck_level = random.uniform(0.1, 0.3)
            time_left = 30
        elif difficulty == "hard":
            stuck_level = random.uniform(0.6, 0.9)
            time_left = 20
        else: # medium
            stuck_level = random.uniform(0.3, 0.6)
            time_left = 25

        self.state_obj = State(
            task_type=random.choice(["coding", "content"]),
            progress=0.0,
            stuck_level=stuck_level,
            time_left=time_left,
            intervention_available=True
        )

        return self.state_obj

    def state(self) -> State:
        return self.state_obj

    def step(self, action: Union[Action, str]) -> StepResult:
        if isinstance(action, Action):
            act_str = action.action
        elif isinstance(action, str):
            act_str = action
        else:
            raise ValueError(f"Invalid action type: {type(action)}")
            
        # Capture strictly previous parameters mapping updates accurately against step routines
        old_state_enc = self._encode_state(self.state_obj)

        s = self.state_obj
        reward = 0.0

        if s.time_left > 0:
            s.time_left -= 1
            
        if s.progress >= 1.0 or s.time_left < 0:
            return StepResult(state=s, reward=0.0, done=True)

        if act_str == "continue":
            base_inc = random.uniform(0.05, 0.15)
            actual_inc = base_inc * (1.0 - s.stuck_level)
            s.progress += actual_inc

            if s.stuck_level > 0.7:
                s.stuck_level += random.uniform(0.05, 0.15)
                # Penalty for grinding while very stuck
                reward = -0.4 if s.stuck_level > 0.8 else -0.2
            elif 0.4 <= s.stuck_level <= 0.7:
                s.stuck_level += random.uniform(-0.02, 0.08)
                reward = 0.05
            else:
                s.stuck_level -= random.uniform(0.02, 0.08)
                reward = 0.2 if actual_inc > 0.03 else 0.1
                
        elif act_str == "intervene":
            if s.stuck_level > 0.6:
                s.progress += random.uniform(0.2, 0.4)
                s.stuck_level -= random.uniform(0.3, 0.6)
                reward = random.uniform(0.5, 0.6)
            else:
                s.progress += random.uniform(0.0, 0.02)
                s.stuck_level += random.uniform(0.05, 0.15)
                reward = -0.3
                
        elif act_str == "switch_task":
            s.task_type = "content" if s.task_type == "coding" else "coding"
            s.progress *= random.uniform(0.5, 0.8) # Lose 20-50%
            
            # Meaningful, partial reward signal explicitly mapping penalty exceptions constraints
            if s.stuck_level > 0.8 and s.progress < 0.2 and s.time_left <= 10:
                reward = 0.3
            else:
                reward = -0.2
                
            s.stuck_level = random.uniform(0.0, 0.2)
            
        else:
            raise ValueError(f"Unknown action: {act_str}")

        # Clamp bounds strictly
        s.progress = float(max(0.0, min(1.0, s.progress)))
        s.stuck_level = float(max(0.0, min(1.0, s.stuck_level)))

        done = s.progress >= 1.0 or s.time_left <= 0

        if s.progress >= 1.0:
            reward = max(reward, 1.0)
            
        # Handle Q-Table updates following discrete logic formulas directly inside OpenEnv states without overriding the API returns.
        q_vals = self._get_q_values(old_state_enc)
        current_q = q_vals[act_str]
        
        # Basic Bellman formula Q(s,a) = Q(s,a) + alpha * (reward - Q(s,a)) natively implemented inside state loops
        q_vals[act_str] = current_q + self.alpha * (reward - current_q)
        
        # Prevent histories drifting without tracking context
        self.history.append({
            "state": old_state_enc,
            "action": act_str,
            "reward": reward
        })

        return StepResult(
            state=s,
            reward=reward,
            done=done,
            state_key=self._encode_state(s),
            q_values=self._get_q_values(self._encode_state(s)), # Push active references evaluating NEW state choices for external tracking 
            history_length=len(self.history),
            epsilon=self.epsilon
        )
