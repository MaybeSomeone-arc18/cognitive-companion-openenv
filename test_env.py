import random
from models import Action
from server.environment import CognitiveCompanionEnvironment


def test_heuristic(name: str, use_heuristic: bool, steps: int = 15):
    print(f"=== {name} ===")

    env = CognitiveCompanionEnvironment()
    random.seed(42)
    env.reset(difficulty="hard")

    total_reward = 0.05
    for i in range(steps):
        s = env.state
        obs = env._obs
        if use_heuristic and obs and obs.stuck_level > 0.7:
            act = "intervene"
        else:
            act = "continue"

        obs = env.step(Action(action=act))
        reward = obs.reward if obs.reward is not None else 0.05
        total_reward += reward

        print(
            f"Step {i+1:2d} | Action: {act:11s} | "
            f"Prog: {obs.progress:.2f} | Stuck: {obs.stuck_level:.2f} | "
            f"Reward: {reward:5.2f} | Done: {obs.done}"
        )

        if obs.done:
            break

    print(f"Total Cumulative Reward -> {total_reward:.2f}\n")


if __name__ == "__main__":
    test_heuristic("Brute Force Strategy (always 'continue')", use_heuristic=False)
    test_heuristic("Smart Heuristic (intervene if stuck > 0.7)", use_heuristic=True)
