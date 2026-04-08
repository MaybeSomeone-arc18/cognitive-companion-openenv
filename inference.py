# inference.py

import os
import json
import sys
import time
from typing import List, Optional, Any

from openai import OpenAI

from models import Action, CognitiveObservation
from client import CognitiveCompanionClient
from graders import clamp_score, MIN_VALID_SCORE, MAX_VALID_SCORE


ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

# Fallback values for local testing if env variables are not supplied
_default_api_base = "https://router.huggingface.co/v1"
_default_api_key = (
    os.environ.get("API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or os.environ.get("HF_TOKEN")
    or "dummy"
)

client_llm = OpenAI(
    base_url=os.environ.get("API_BASE_URL", _default_api_base),
    api_key=_default_api_key,
)

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
ENV_NAME = "cognitive_companion"


def _bool_str(value: bool) -> str:
    return "true" if bool(value) else "false"


def _fmt_reward(value: Any) -> str:
    # Keep log output deterministic for validators.
    try:
        val = clamp_score(float(value))
    except (TypeError, ValueError):
        val = MIN_VALID_SCORE
    return f"{val:.2f}"


def _safe_token(value: Optional[str]) -> str:
    if value is None:
        return "null"
    # Single-line logs only.
    return " ".join(str(value).split())


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
            temperature=0,
        )
        content = resp.choices[0].message.content or ""
        act_str = content.strip().lower()
        if act_str not in ["continue", "intervene", "switch_task"]:
            act_str = "continue"
        return act_str
    except Exception:
        stuck = state_dict.get("stuck_level", 0.01)
        return "intervene" if stuck > 0.7 else "continue"


def run() -> None:
    difficulties = ["easy", "medium", "hard"]
    episodes_per_diff = 3

    env_client = CognitiveCompanionClient.from_base_url(ENV_BASE_URL)

    for diff in difficulties:
        for episode in range(1, episodes_per_diff + 1):
            max_retries = 10
            print(f"[START] task={diff} env={ENV_NAME} model={MODEL_NAME}")

            rewards: List[str] = []
            total_reward = 0.0
            step_idx = 0
            success = False
            last_error: Optional[str] = None
            finished = False

            for attempt in range(max_retries):
                try:
                    with env_client.sync() as env:
                        obs = env.reset(difficulty=diff)
                        done = False

                        while not done:
                            action_str = get_action_from_llm(obs)
                            act = Action(action=action_str)
                            obs = env.step(act)
                            step_idx += 1

                            reward_val = clamp_score(float(obs.reward if obs.reward is not None else MIN_VALID_SCORE))
                            total_reward += reward_val
                            rewards.append(f"{reward_val:.2f}")

                            metadata = obs.metadata if isinstance(obs.metadata, dict) else {}
                            raw_last_error = metadata.get("last_action_error") if metadata else None
                            if raw_last_error:
                                last_error = str(raw_last_error)

                            done = bool(obs.done)

                            print(
                                "[STEP] "
                                f"step={step_idx} "
                                f"action={_safe_token(action_str)} "
                                f"reward={_fmt_reward(reward_val)} "
                                f"done={_bool_str(done)} "
                                f"error={_safe_token(last_error)}"
                            )

                        final_progress = float(max(MIN_VALID_SCORE, min(MAX_VALID_SCORE, obs.progress)))
                        final_score = clamp_score(final_progress)
                        success = bool(final_score >= 0.5)
                        finished = True
                        break  # Break out of retry loop on success
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        # Final fallback after max retries.
                        print(f"Episode {episode} failed: {e}", file=sys.stderr)
                        finished = False

            if not finished and not rewards:
                # Keep END format stable even if all attempts fail pre-step.
                rewards = [f"{MIN_VALID_SCORE:.2f}"]
                total_reward = MIN_VALID_SCORE
                success = False

            rewards_csv = ",".join(rewards)
            print(
                "[END] "
                f"success={_bool_str(success)} "
                f"steps={step_idx} "
                f"rewards={rewards_csv}"
            )


if __name__ == "__main__":
    run()
