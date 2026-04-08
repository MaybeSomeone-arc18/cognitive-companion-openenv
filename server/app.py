# server/app.py

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from openenv.core.env_server.http_server import create_app

from models import Action, CognitiveObservation, EnvState, StepResult
from server.environment import CognitiveCompanionEnvironment
from graders import default_grader, safe_task_score

# OpenEnv FastAPI app
openenv_app = create_app(
    CognitiveCompanionEnvironment,
    Action,
    CognitiveObservation,
    env_name="cognitive_companion",
    max_concurrent_envs=10,
)

# Wrap in a top-level FastAPI so we can add extra endpoints if needed
app = FastAPI(title="Cognitive Companion Environment")

# Mount the OpenEnv routes under root
app.mount("", openenv_app)

# Access to the underlying singleton environment for extras
_env = CognitiveCompanionEnvironment()


@app.get("/")
def root():
    return JSONResponse(
        {
            "name": "Cognitive Companion Environment",
            "status": "ok",
            "endpoints": ["/health", "/reset", "/step", "/state", "/schema", "/ws", "/qtable"],
        }
    )


@app.get("/health")
def health():
    return {"status": "ok"}


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

    raw = graders[task_id](episode_log)
    score = safe_task_score(float(raw))
    assert 0.0 < score < 1.0
    return {"task_id": task_id, "score": score}


def main():
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0" + ".0.0.0")
    uvicorn.run("server.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
