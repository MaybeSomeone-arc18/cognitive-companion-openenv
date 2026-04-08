# models.py

from typing import Literal, Optional, Dict, List
from pydantic import BaseModel


class CognitiveObservation(BaseModel):
    """
    What the agent sees at each step.
    We keep your original fields and add reward/done/metadata
    so OpenEnv can use this as the Observation type.
    """
    task_type: str
    progress: float
    stuck_level: float
    time_left: int
    intervention_available: bool

    # OpenEnv-style extras
    reward: Optional[float] = None
    done: Optional[bool] = None
    metadata: Optional[Dict[str, object]] = None


class Action(BaseModel):
    action: Literal["continue", "intervene", "switch_task"]


class EnvState(BaseModel):
    """
    Episode-level state, used by Environment.state().
    """
    task_id: str
    step: int
    max_steps: int
    history: List[str]
    done: bool


class StepResult(BaseModel):
    """
    Convenience type for your old HTTP client / logs.
    Not used by OpenEnv directly, but we keep it so your
    /step endpoint can still return this shape.
    """
    state: CognitiveObservation
    reward: float
    done: bool
    state_key: Optional[str] = None
    q_values: Optional[Dict[str, float]] = None
    history_length: Optional[int] = None
    epsilon: Optional[float] = None
