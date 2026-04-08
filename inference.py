import os
from typing import List, Optional

from openai import OpenAI

from models import Action, CognitiveObservation
from client import CognitiveCompanionClient
from graders import clamp_score, safe_task_score, MIN_VALID_SCORE


ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is required")

client_llm = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
)

ENV_NAME = "cognitive_companion"


def _bool_str(value: bool) -> str:
    return "true" if bool(value) else "false"


def _fmt_reward(value: float) -> str:
    return f"{clamp_score(value):.2f}"


def _safe_token(value: Optional[str]) -> str:
    if value is None:
        return "null"
    return " ".join(str(value).split())


def _load_tasks_from_openenv() -> List[str]:
    tasks: List[str] = []
    with open("openenv.yaml", "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("- id:"):
                task = stripped.split(":", 1)[1].strip().strip("\"'")
                if task:
                    tasks.append(task)
    return tasks or ["easy", "medium", "hard"]


def get_action_from_llm(obs: CognitiveObservation) -> str:
    state_dict = obs.model_dump()
    system_prompt = (
        "You are a cognitive companion AI helping a human user who is working on a task.\n"
        "You must choose one of exactly three actions: 'continue', 'intervene', or 'switch_task'.\n"
        "Rules:\n"
        "- 'continue' if stuck_level is low or moderate and there is still time.\n"
        "- 'intervene' if stuck_level is very high (> 0.6).\n"
        "- 'switch_task' if time_left is low, progress is low, and stuck_level is extremely high.\n\n"
        "Reply with EXACTLY ONE word mapping to your chosen action: continue, intervene, or switch_task."
    )
    user_prompt = f"Current State: {state_dict}"

    try:
        resp = client_llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content or ""
        act_str = content.strip().lower()
        if act_str not in ["continue", "intervene", "switch_task"]:
            act_str = "continue"
        return act_str
    except Exception:
        stuck = state_dict.get("stuck_level", MIN_VALID_SCORE)
        return "intervene" if stuck > 0.7 else "continue"


def run() -> None:
    tasks = _load_tasks_from_openenv()
    env_client = CognitiveCompanionClient.from_base_url(ENV_BASE_URL)

    for task in tasks:
        print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}")

        rewards: List[str] = []
        step_idx = 0
        success = False
        last_error: Optional[str] = None
        final_score = safe_task_score(-0.5)
        last_obs: Optional[CognitiveObservation] = None
        reward_values: List[float] = []

        try:
            with env_client.sync() as env:
                obs = env.reset(difficulty=task)
                done = False
                while not done:
                    action_str = get_action_from_llm(obs)
                    obs = env.step(Action(action=action_str))
                    last_obs = obs
                    step_idx += 1

                    reward_val = clamp_score(obs.reward if obs.reward is not None else 0.01)
                    reward_values.append(reward_val)
                    rewards.append(_fmt_reward(reward_val))
                    done = bool(obs.done)

                    metadata = obs.metadata if isinstance(obs.metadata, dict) else {}
                    raw_last_error = metadata.get("last_action_error")
                    if raw_last_error is None:
                        error_val = "null"
                    else:
                        error_val = _safe_token(str(raw_last_error))
                        last_error = str(raw_last_error)

                    print(
                        f"[STEP] step={step_idx} action={_safe_token(action_str)} "
                        f"reward={_fmt_reward(reward_val)} done={_bool_str(done)} error={error_val}"
                    )
        except Exception as exc:
            last_error = str(exc)

        if reward_values:
            raw_score = sum(reward_values) / len(reward_values)
        elif last_obs is not None:
            raw_score = last_obs.progress
        else:
            raw_score = -0.5
        final_score = safe_task_score(raw_score)
        assert 0.0 < final_score < 1.0
        success = bool(final_score >= 0.5 and last_error is None)

        if not rewards:
            rewards = [_fmt_reward(0.01)]

        print(
            f"[END]  success={_bool_str(success)} steps={step_idx} rewards={','.join(rewards)}"
        )


if __name__ == "__main__":
    run()
