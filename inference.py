# inference.py

import os
import json
from typing import Optional

from openai import OpenAI
from models import Action
from client import reset, step


# Environment + LLM configuration
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None or HF_TOKEN.strip() == "":
    raise RuntimeError(
        "HF_TOKEN environment variable is not set. "
        "Per submission rules, this must be provided with no default."
    )

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


def get_action_from_llm(state_dict: dict) -> str:
    system_prompt = (
        "You are a cognitive companion AI helping a human user who is working on a task.\n"
        "You must choose one of exactly three actions: 'continue', 'intervene', or 'switch_task'.\n"
        "Rules:\n"
        "- 'continue' if stuck_level is low/moderate.\n"
        "- 'intervene' if stuck_level is very high (> 0.6).\n"
        "- 'switch_task' if time_left is low, progress is low, and stuck_level is extremely high.\n\n"
        "Reply with EXACTLY ONE word mapping to your chosen action: continue, intervene, or switch_task."
    )

    user_prompt = f"Current State: {json.dumps(state_dict)}"

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        act_str = response.choices[0].message.content.strip().lower()
        if act_str not in ["continue", "intervene", "switch_task"]:
            act_str = "continue"  # fallback
        return act_str
    except Exception:
        # Fallback heuristic if LLM fails, to avoid stalling inference
        stuck = state_dict.get("stuck_level", 0.0)
        return "intervene" if stuck > 0.7 else "continue"


def safe_reset(env_base_url: str, difficulty: str):
    """
    Wrapper around reset() that catches all network / client errors
    and returns None instead of raising, so inference.py never crashes.
    """
    try:
        return reset(env_base_url, difficulty=difficulty)
    except Exception as e:
        # Emit a diagnostic line (not part of [START]/[STEP]/[END] protocol)
        print(f"[ERROR] reset failed for difficulty='{difficulty}': {e}")
        return None


def safe_step(env_base_url: str, action: Action):
    """
    Wrapper around step() that catches all network / client errors
    and returns None instead of raising.
    """
    try:
        return step(env_base_url, action)
    except Exception as e:
        print(f"[ERROR] step failed for action='{action.action}': {e}")
        return None


def run() -> None:
    difficulties = ["easy", "medium", "hard"]
    episodes_per_diff = 3

    for diff in difficulties:
        for episode in range(1, episodes_per_diff + 1):
            # Use safe_reset to avoid unhandled MaxRetryError / ConnectionRefusedError
            state = safe_reset(ENV_BASE_URL, difficulty=diff)

            # If reset completely failed, emit [START] + [END] with 0 score and continue.
            if state is None:
                start_payload = {
                    "episode": episode,
                    "task": diff,
                    "note": "env_reset_failed",
                }
                print(f"[START] {json.dumps(start_payload)}")

                end_payload = {
                    "episode": episode,
                    "task": diff,
                    "total_reward": 0.0,
                    "score": 0.0,
                    "note": "env_unreachable",
                }
                print(f"[END] {json.dumps(end_payload)}")
                continue

            # [START] log
            start_payload = {
                "episode": episode,
                "task": diff,
            }
            print(f"[START] {json.dumps(start_payload)}")

            done = False
            total_reward = 0.0
            step_idx = 1

            while not done:
                # Pydantic v2: model_dump; v1: dict()
                state_dict = (
                    state.model_dump()
                    if hasattr(state, "model_dump")
                    else state.dict()
                )

                chosen_act_str = get_action_from_llm(state_dict)
                act = Action(action=chosen_act_str)

                # Use safe_step to avoid unhandled connection errors
                result = safe_step(ENV_BASE_URL, act)
                if result is None:
                    # If step fails mid-episode, stop this episode gracefully.
                    end_payload = {
                        "episode": episode,
                        "task": diff,
                        "total_reward": total_reward,
                        "score": 0.0,
                        "note": "env_step_failed",
                    }
                    print(f"[END] {json.dumps(end_payload)}")
                    break

                # [STEP] log
                step_payload = {
                    "step": step_idx,
                    "state": state_dict,
                    "action": chosen_act_str,
                    "reward": result.reward,
                    "done": result.done,
                    "task": diff,
                    "q_values": result.q_values,
                    "history_length": result.history_length,
                    "epsilon": result.epsilon,
                }
                print(f"[STEP] {json.dumps(step_payload)}")

                state = result.state
                total_reward += result.reward
                done = result.done
                step_idx += 1

            # If we exited the loop via done == True, compute a score normally.
            if done:
                final_progress = getattr(state, "progress", 0.0)
                score = float(max(0.0, min(1.0, final_progress)))
                end_payload = {
                    "episode": episode,
                    "task": diff,
                    "total_reward": total_reward,
                    "score": score,
                }
                print(f"[END] {json.dumps(end_payload)}")


if __name__ == "__main__":
    run()
