# inference.py

import os
import json
import sys
import time
from typing import List, Optional

from openai import OpenAI

from models import Action, CognitiveObservation
from client import CognitiveCompanionClient
from graders import clamp_score


ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

# Fallback values for local testing if env variables are not supplied
_default_api_base = "https://router.huggingface.co/v1"
_default_api_key = os.environ.get("HF_TOKEN", "dummy")

client_llm = OpenAI(
    base_url=os.environ.get("API_BASE_URL", _default_api_base),
    api_key=os.environ.get("API_KEY", _default_api_key)
)

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")


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
    user_prompt = f"Current State: {json.dumps(state_dict, ensure_ascii=False)}"

    try:
        resp = client_llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        content = resp.choices[0].message.content or ""
        act_str = content.strip().lower()
        if act_str not in ["continue", "intervene", "switch_task"]:
            act_str = "continue"
        return act_str
    except Exception:
        stuck = state_dict.get("stuck_level", 0.0)
        return "intervene" if stuck > 0.7 else "continue"


def run() -> None:
    difficulties = ["easy", "medium", "hard"]
    episodes_per_diff = 3

    env_client = CognitiveCompanionClient.from_base_url(ENV_BASE_URL)

    for diff in difficulties:
        for episode in range(1, episodes_per_diff + 1):
            max_retries = 10
            started = False
            for attempt in range(max_retries):
                try:
                    with env_client.sync() as env:
                        obs = env.reset(difficulty=diff)

                        start_payload = {
                            "episode": episode,
                            "task": diff,
                        }
                        if not started:
                            print(f"[START] {json.dumps(start_payload)}")
                            started = True

                        done = False
                        total_reward = 0.0
                        step_idx = 1

                        while not done:
                            action_str = get_action_from_llm(obs)
                            act = Action(action=action_str)

                            obs = env.step(act)

                            step_payload = {
                                "step": step_idx,
                                "state": obs.model_dump(),
                                "action": action_str,
                                "reward": obs.reward,
                                "done": obs.done,
                                "task": diff,
                            }
                            print(f"[STEP] {json.dumps(step_payload)}")

                            total_reward += obs.reward or 0.0
                            done = bool(obs.done)
                            step_idx += 1

                        final_progress = float(max(0.0, min(1.0, obs.progress)))
                        score = clamp_score(final_progress)

                        end_payload = {
                            "episode": episode,
                            "task": diff,
                            "total_reward": total_reward,
                            "score": score,
                        }
                        print(f"[END] {json.dumps(end_payload)}")
                        break  # Break out of retry loop on success
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        # Fallback after max_retries
                        print(f"Episode {episode} failed: {e}", file=sys.stderr)
                        if not started:
                            print(f"[START] {json.dumps({'episode': episode, 'task': diff})}")
                        print(f"[END] {json.dumps({'episode': episode, 'task': diff, 'total_reward': 0.0, 'score': clamp_score(0.0)})}")


if __name__ == "__main__":
    run()
