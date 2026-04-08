# client.py

from typing import Optional

from openenv.core.env_client import EnvClient

from models import Action, CognitiveObservation, EnvState


class CognitiveCompanionClient(EnvClient[Action, CognitiveObservation, EnvState]):
    """
    OpenEnv-compatible client for the Cognitive Companion environment.
    """

    @classmethod
    def from_base_url(cls, base_url: str) -> "CognitiveCompanionClient":
        return cls(base_url=base_url)


# For compatibility with your existing code, keep simple helpers.

def reset(base_url: str, difficulty: str = "medium") -> CognitiveObservation:
    """
    Synchronous helper to reset the environment using HTTP/WS via EnvClient.
    """
    with CognitiveCompanionClient.from_base_url(base_url).sync() as client:
        return client.reset(difficulty=difficulty)


def step(base_url: str, action: Action) -> CognitiveObservation:
    """
    Synchronous helper to step the environment.
    """
    with CognitiveCompanionClient.from_base_url(base_url).sync() as client:
        return client.step(action)
