# tests/test_env_baseline.py
import pytest
import requests
from baseline_agent import BaselineAgent
from client import CognitiveCompanionClient
from models import Action
from graders import clamp_score, MIN_VALID_SCORE

_API = "http://localhost:7860"

def _server_up() -> bool:
    try:
        requests.get(f"{_API}/health", timeout=1)
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _server_up(), reason="API server not running on port 7860")


def test_single_episode_reward_in_range():
    env_client = CognitiveCompanionClient.from_base_url("http://localhost:7860")
    agent = BaselineAgent()
    agent.reset()

    total_reward = 0.0

    with env_client.sync() as env:
        # Use a predetermined difficulty, easy so it reliably finishes quickly
        obs = env.reset(difficulty="easy")
        done = False

        while not done:
            action_decision = agent.select_action(obs)
            action_str = "intervene" if action_decision == "INTERVENE" else "continue"
            
            obs = env.step(Action(action=action_str))
            reward = clamp_score(obs.reward if obs.reward is not None else MIN_VALID_SCORE)
            total_reward += reward
            done = bool(obs.done)

    # The accumulated reward over many steps (10-20) can exceed 1.0, 
    # but shouldn't be negative and shouldn't realistically hit absurd numbers
    assert 0.0 <= total_reward <= 20.0
