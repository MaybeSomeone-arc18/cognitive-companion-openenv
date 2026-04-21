# server/app.py

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from openenv.core.env_server.http_server import create_app

from models import Action, CognitiveObservation, EnvState, StepResult
from server.environment import CognitiveCompanionEnvironment
from graders import default_grader, clamp_score, MIN_VALID_SCORE, MAX_VALID_SCORE

# OpenEnv FastAPI app
openenv_app = create_app(
    CognitiveCompanionEnvironment,
    Action,
    CognitiveObservation,
    env_name="cognitive_companion",
    max_concurrent_envs=10,
)


@openenv_app.get("/", response_class=HTMLResponse)
def openenv_root():
    return """
    <html>
        <head><title>Cognitive Companion OpenEnv</title></head>
        <body>
            <h1>Cognitive Companion OpenEnv</h1>
            <p>Space is running. Basic API is live.</p>
            <p>Use endpoints: /reset, /step, /state, /health</p>
        </body>
    </html>
    """

# Wrap in a top-level FastAPI so we can add extra endpoints if needed
app = FastAPI(title="Cognitive Companion Environment")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Access to the underlying singleton environment for extras
_env = CognitiveCompanionEnvironment()


@app.get("/")
def root():
    return {"message": "API running. Visit /dashboard/index.html"}


from baseline_agent import BaselineAgent

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/baseline/run-once")
def run_baseline_once():
    # Instantiate standalone local environment & agent for isolated synchronous run
    local_env = CognitiveCompanionEnvironment()
    agent = BaselineAgent()
    
    obs = local_env.reset(difficulty="medium")
    
    total_reward = 0.0
    num_interventions = 0
    done = False
    
    steps_log = []
    
    while not done:
        action_decision = agent.select_action(obs)
        action_str = "intervene" if action_decision == "INTERVENE" else "continue"
        
        if action_decision == "INTERVENE":
            num_interventions += 1
            
        is_stuck_val = agent.is_stuck
        is_err_val = agent.is_error_spiral
        
        obs = local_env.step(Action(action=action_str))
        reward = clamp_score(obs.reward if obs.reward is not None else MIN_VALID_SCORE)
        total_reward += reward
        done = bool(obs.done)
        
        steps_log.append({
            "step": local_env._step_idx,
            "action": action_decision,
            "reward": round(reward, 3),
            "is_stuck": is_stuck_val,
            "is_error_spiral": is_err_val
        })
        
    completion = obs.progress if obs.progress is not None else 0.0
    
    return {
        "summary": {
            "difficulty": "medium",
            "total_reward": round(total_reward, 3),
            "interventions": num_interventions,
            "completion": round(completion, 3)
        },
        "steps": steps_log
    }



@app.get("/qtable")
def get_qtable():
    serialized_qtable = {k: v for k, v in _env.q_table.items()}
    return {"q_table": serialized_qtable}


@app.post("/grader")
def grade_episode(payload: dict):
    task_id = payload.get("task_id")
    episode_log = payload.get("episode_log")
    if not isinstance(task_id, str):
        raise HTTPException(status_code=400, detail="task_id must be a string")
    if not isinstance(episode_log, list):
        raise HTTPException(status_code=400, detail="episode_log must be a list")

    graders = {
        "easy": default_grader,
        "medium": default_grader,
        "hard": default_grader,
    }
    if task_id not in graders:
        raise HTTPException(status_code=400, detail=f"unknown task_id: {task_id}")

    score = graders[task_id](episode_log)
    assert MIN_VALID_SCORE <= score <= MAX_VALID_SCORE
    return {"task_id": task_id, "score": score}


# Serve static dashboard — accessible at /dashboard on the deployed Space
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dashboard_path = os.path.join(BASE_DIR, "dashboard")

if os.path.isdir(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

# Mount the core OpenEnv sub-app at the root, AFTER all custom overrides so they don't get shadowed
app.mount("/api", openenv_app)

def main():
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("server.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
