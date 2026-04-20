# run_baseline.py

import os
import json
from baseline_agent import BaselineAgent
from client import CognitiveCompanionClient
from models import Action
from graders import clamp_score, MIN_VALID_SCORE

ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

def run_episode():
    # Instantiate the env client and our baseline agent
    env_client = CognitiveCompanionClient.from_base_url(ENV_BASE_URL)
    agent = BaselineAgent()
    agent.reset()

    total_reward = 0.0
    num_interventions = 0

    print("=== Starting Baseline Episode ===")

    with env_client.sync() as env:
        obs = env.reset(difficulty="medium")  # Starting with medium difficulty
        done = False
        step = 0

        while not done:
            step += 1
            # Baseline decides what to do based on the current observation
            agent_decision = agent.select_action(obs)

            if agent_decision == "INTERVENE":
                num_interventions += 1
                env_action_str = "intervene"
            else:
                env_action_str = "continue"

            # Execute action in the environment using the required Action model
            obs = env.step(Action(action=env_action_str))
            
            # Keep track of rewards
            reward = clamp_score(obs.reward if obs.reward is not None else MIN_VALID_SCORE)
            total_reward += reward
            done = bool(obs.done)

        # In this env, progress is often tracked inside the observation directly
        completion = obs.progress if obs.progress is not None else 0.0

    print("\n=== Baseline episode summary ===")
    print(f"Total steps:        {step}")
    print(f"Total reward:       {total_reward:.3f}")
    print(f"Total interventions:{num_interventions}")
    print(f"Task completion:    {completion:.3f}")

    summary = {
        "episode_id": "baseline-run",
        "total_steps": step,
        "total_reward": round(total_reward, 3),
        "interventions": num_interventions,
        "completion": round(completion, 3),
    }
    print(json.dumps(summary))

if __name__ == "__main__":
    run_episode()
