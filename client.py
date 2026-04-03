import requests
from models import State, Action, StepResult

def reset(base_url: str, difficulty: str = "medium") -> State:
    url = f"{base_url}/reset"
    # Adhere closely with the mapped server/app.py schema taking formal payload JSON arguments.
    response = requests.post(url, json={"difficulty": difficulty})
    response.raise_for_status()
    return State(**response.json())

def step(base_url: str, action: Action) -> StepResult:
    url = f"{base_url}/step"
    # Support both Pydantic v1 and v2 for dumping to dictionary
    payload = action.model_dump() if hasattr(action, "model_dump") else action.dict()
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return StepResult(**response.json())
