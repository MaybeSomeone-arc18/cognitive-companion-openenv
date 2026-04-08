# server/environment.py

import random
from typing import Union, Any, Dict, List, Optional

from openenv.core.env_server import Environment

from models import Action, CognitiveObservation, EnvState, StepResult
from graders import clamp_score, MIN_VALID_SCORE, MAX_VALID_SCORE


def clamp_reward(raw: float) -> float:
    return clamp_score(raw)


class CognitiveCompanionEnvironment(Environment[Action, CognitiveObservation, EnvState]):
    """
    OpenEnv-compatible environment for the Cognitive Companion.

    - reset() and step() return CognitiveObservation (with reward/done/metadata).
    - state property returns EnvState.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        # Core episode state
        self._obs: Optional[CognitiveObservation] = None
        self._task_id: str = "medium"
        self._step_idx: int = 0
        self._max_steps: int = 30  # loose upper bound via time_left
        self._done: bool = False
        self._history: List[str] = []

        # Embedded Q-Learning metrics (your original fields)
        self.q_table: Dict[str, Dict[str, float]] = {}
        self.alpha: float = 0.1
        self.epsilon: float = 0.1

        # Initialise one episode
        self.reset()

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _encode_state(self, obs: CognitiveObservation) -> str:
        """
        Bucketize state into a compact key for the Q-table.
        """
        stuck_bucket = min(9, int(obs.stuck_level * 10))
        progress_bucket = min(9, int(obs.progress * 10))
        time_bucket = obs.time_left // 5

        return f"{obs.task_type}_{stuck_bucket}_{progress_bucket}_{time_bucket}"

    def _get_q_values(self, encoded_state: str) -> Dict[str, float]:
        if encoded_state not in self.q_table:
            self.q_table[encoded_state] = {
                "continue": MIN_VALID_SCORE,
                "intervene": MIN_VALID_SCORE,
                "switch_task": MIN_VALID_SCORE,
            }
        return self.q_table[encoded_state]

    # ---------------------------------------------------------------------
    # OpenEnv interface
    # ---------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CognitiveObservation:
        """
        Reset the environment.

        Accepts difficulty via kwargs["difficulty"], matching openenv.yaml tasks:
        - "easy"
        - "medium"
        - "hard"
        """
        difficulty = kwargs.get("difficulty", "medium")
        clear_qtable = kwargs.get("clear_qtable", False)

        if clear_qtable:
            self.q_table.clear()
            self._history.clear()

        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"

        self._task_id = difficulty
        self._step_idx = 0
        self._done = False

        if difficulty == "easy":
            stuck_level = random.uniform(0.1, 0.3)
            time_left = 30
        elif difficulty == "hard":
            stuck_level = random.uniform(0.6, 0.9)
            time_left = 20
        else:  # medium
            stuck_level = random.uniform(0.3, 0.6)
            time_left = 25

        self._obs = CognitiveObservation(
            task_type=random.choice(["coding", "content"]),
            progress=MIN_VALID_SCORE,
            stuck_level=stuck_level,
            time_left=time_left,
            intervention_available=True,
            reward=None,
            done=False,
            metadata={"difficulty": self._task_id, "step": self._step_idx},
        )

        # Use time_left as a soft upper bound for max_steps
        self._max_steps = max(1, self._obs.time_left)

        return self._obs

    def step(self, action: Action) -> CognitiveObservation:
        """
        Apply an action and return the next observation.
        """
        if self._obs is None:
            raise RuntimeError("Call reset() before step()")

        if self._done:
            raise RuntimeError("Episode is finished")

        s = self._obs
        act_str = action.action
        reward = MIN_VALID_SCORE

        old_state_enc = self._encode_state(s)

        if s.time_left > 0:
            s.time_left -= 1

        # Already terminal
        if s.progress >= MAX_VALID_SCORE or s.time_left <= 0:
            reward = clamp_reward(MIN_VALID_SCORE)
            self._done = True
            s.reward = reward
            s.done = True
            s.metadata = {
                "difficulty": self._task_id,
                "step": self._step_idx,
                "reason": "terminal_before_action",
            }
            return s

        # --- Your original transition logic, adapted to CognitiveObservation ---

        if act_str == "continue":
            base_inc = random.uniform(0.05, 0.15)
            actual_inc = base_inc * (MAX_VALID_SCORE - s.stuck_level)
            s.progress += actual_inc

            if s.stuck_level > 0.7:
                s.stuck_level += random.uniform(0.05, 0.15)
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
                s.progress += random.uniform(MIN_VALID_SCORE, 0.02)
                s.stuck_level += random.uniform(0.05, 0.15)
                reward = -0.3

        elif act_str == "switch_task":
            s.task_type = "content" if s.task_type == "coding" else "coding"
            s.progress *= random.uniform(0.5, 0.8)  # Lose 20–50%

            if s.stuck_level > 0.8 and s.progress < 0.2 and s.time_left <= 10:
                reward = 0.3
            else:
                reward = -0.2

            s.stuck_level = random.uniform(MIN_VALID_SCORE, 0.2)

        else:
            raise ValueError(f"Unknown action: {act_str}")

        # Clamp state attributes
        reached_goal = s.progress >= MAX_VALID_SCORE
        s.progress = float(max(MIN_VALID_SCORE, min(MAX_VALID_SCORE, s.progress)))
        s.stuck_level = float(max(MIN_VALID_SCORE, min(MAX_VALID_SCORE, s.stuck_level)))

        self._step_idx += 1
        done = reached_goal or s.time_left <= 0

        if reached_goal:
            reward = max(reward, MAX_VALID_SCORE)

        # FINAL: clamp reward into (MIN_VALID_SCORE, MAX_VALID_SCORE)
        reward = clamp_reward(reward)

        # Q-table update
        q_vals = self._get_q_values(old_state_enc)
        current_q = q_vals[act_str]
        q_vals[act_str] = current_q + self.alpha * (reward - current_q)

        # History
        history_entry = f"step={self._step_idx}, action={act_str}, reward={reward:.3f}"
        self._history.append(history_entry)

        # Update observation with OpenEnv-style metadata
        self._done = done
        s.reward = reward
        s.done = done
        s.metadata = {
            "difficulty": self._task_id,
            "step": self._step_idx,
            "state_key": self._encode_state(s),
            "history_length": len(self._history),
            "epsilon": self.epsilon,
        }

        self._obs = s
        return self._obs

    @property
    def state(self) -> EnvState:
        """
        Return the current comprehensive state for OpenEnv.
        """
        return EnvState(
            task_id=self._task_id,
            step=self._step_idx,
            max_steps=self._max_steps,
            history=list(self._history),
            done=self._done,
        )

    # ---------------------------------------------------------------------
    # Compatibility helper: keep your old StepResult shape for /step endpoint
    # ---------------------------------------------------------------------

    def step_legacy(self, action: Union[Action, str]) -> StepResult:
        """
        Wrapper that uses the OpenEnv step() internally but returns the
        old StepResult shape for your existing HTTP client and logs.
        """
        if isinstance(action, str):
            action = Action(action=action)

        obs = self.step(action)

        encoded = self._encode_state(obs)
        q_vals = self._get_q_values(encoded)

        return StepResult(
            state=obs,
            reward=clamp_score(obs.reward if obs.reward is not None else MIN_VALID_SCORE),
            done=obs.done or False,
            state_key=encoded,
            q_values=q_vals,
            history_length=len(self._history),
            epsilon=self.epsilon,
        )
