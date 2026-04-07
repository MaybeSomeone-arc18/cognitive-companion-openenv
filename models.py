# models.py

from typing import Literal, Optional, Dict
from pydantic import BaseModel


class State(BaseModel):
    task_type: str
    progress: float
    stuck_level: float
    time_left: int
    intervention_available: bool


class Action(BaseModel):
    action: Literal["continue", "intervene", "switch_task"]


class StepResult(BaseModel):
    state: State
    reward: float
    done: bool
    state_key: Optional[str] = None
    q_values: Optional[Dict[str, float]] = None
    history_length: Optional[int] = None
    epsilon: Optional[float] = None
