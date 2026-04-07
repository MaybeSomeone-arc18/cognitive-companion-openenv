# main.py

from typing import Dict

from fastapi import FastAPI, HTTPException

from models import State, Action, StepResult

app = FastAPI(title="Cognitive Companion OpenEnv")

# Very simple in-memory env state; keyed by a single "current" episode
ENV_STATE: Dict[str, State] = {}


def initial_state_for_difficulty(difficulty: str) -> State:
    """
    Construct an initial State given a difficulty.
    Adjust these values to match your design if needed.
    """
    if difficulty == "easy":
        return State(
            task_type="reading",
            progress=0.0,
            stuck_level=0.2,
            time_left=100,
            intervention_available=True,
        )
    if difficulty == "medium":
        return State(
            task_type="coding",
            progress=0.0,
            stuck_level=0.4,
            time_left=80,
            intervention_available=True,
        )
    if difficulty == "hard":
        return State(
            task_type="project",
            progress=0.0,
            stuck_level=0.6,
            time_left=60,
            intervention_available=True,
        )
    # fallback
    return State(
        task_type="generic",
        progress=0.0,
        stuck_level=0.3,
        time_left=90,
        intervention_available=True,
    )


@app.post("/reset", response_model=State)
def reset(difficulty: str = "easy") -> State:
    """
    Reset the environment for the given difficulty, returning the initial State.
    """
    state = initial_state_for_difficulty(difficulty)
    ENV_STATE["current"] = state
    return state


@app.post("/step", response_model=StepResult)
def step(action: Action) -> StepResult:
    """
    Advance the environment one step with the given Action.
    Returns a StepResult with next state, reward, done, and extra info.
    """
    if "current" not in ENV_STATE:
        raise HTTPException(status_code=400, detail="Environment not reset")

    state = ENV_STATE["current"]

    progress = state.progress
    stuck_level = state.stuck_level
    time_left = state.time_left
    intervention_available = state.intervention_available

    # Simple, interpretable dynamics — replace with your real logic if needed
    if action.action == "continue":
        # keep working, modest progress, small stuck reduction
        progress = min(1.0, progress + 0.08)
        stuck_level = max(0.0, stuck_level - 0.05)
        time_left = max(0, time_left - 5)
    elif action.action == "intervene":
        # intervention helps a lot if available
        if intervention_available:
            progress = min(1.0, progress + 0.15)
            stuck_level = max(0.0, stuck_level - 0.25)
            intervention_available = False
        else:
            # no intervention left, small penalty
            progress = max(0.0, progress - 0.05)
            stuck_level = min(1.0, stuck_level + 0.1)
        time_left = max(0, time_left - 8)
    elif action.action == "switch_task":
        # reset some context; may help if very stuck, but lose some progress
        progress = max(0.0, progress * 0.5)
        stuck_level = max(0.0, stuck_level - 0.1)
        time_left = max(0, time_left - 3)
        intervention_available = True
    else:
        # unknown action, small penalty
        progress = max(0.0, progress - 0.05)
        stuck_level = min(1.0, stuck_level + 0.1)
        time_left = max(0, time_left - 5)

    new_state = State(
        task_type=state.task_type,
        progress=progress,
        stuck_level=stuck_level,
        time_left=time_left,
        intervention_available=intervention_available,
    )
    ENV_STATE["current"] = new_state

    # Reward: encourage progress, penalize being stuck, tiny penalty for time passing
    reward = float(progress - 0.3 * stuck_level - 0.001 * (100 - time_left))

    done = bool(progress >= 1.0 or time_left <= 0)

    result = StepResult(
        state=new_state,
        reward=reward,
        done=done,
        state_key="current",
        q_values={"continue": 0.0, "intervene": 0.0, "switch_task": 0.0},
        history_length=0,
        epsilon=0.0,
    )
    return result
