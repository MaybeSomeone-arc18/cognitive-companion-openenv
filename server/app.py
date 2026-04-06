from fastapi import FastAPI
from pydantic import BaseModel
from models import State, Action, StepResult
from server.environment import CognitiveCompanionEnv

app = FastAPI(title="Cognitive Companion Environment")

env = CognitiveCompanionEnv()

class ResetRequest(BaseModel):
    difficulty: str = "medium"
    clear_qtable: bool = False

@app.get("/")
def root():
    return JSONResponse(
        {
            "name": "Cognitive Companion Environment",
            "status": "ok",
            "endpoints": ["/health", "/reset", "/step", "/state", "/qtable"],
        }
        
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset", response_model=State)
def reset(req: ResetRequest = ResetRequest()):
    return env.reset(difficulty=req.difficulty, clear_qtable=req.clear_qtable)

@app.post("/step", response_model=StepResult)
def step(action: Action):
    return env.step(action)

@app.get("/state", response_model=State)
def state():
    return env.state()
    
@app.get("/qtable")
def get_qtable():
    # Flattens natively hashed dicts mapping strictly into string parameters for seamless extraction frameworks.
    serialized_qtable = {k: v for k, v in env.q_table.items()}
    return {"q_table": serialized_qtable}

def main():
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("server.app:app", host=host, port=port)

if __name__ == "__main__":
    main()
