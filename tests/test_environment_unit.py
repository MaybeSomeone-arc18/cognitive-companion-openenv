"""Offline environment checks: no localhost server or external API needed."""
from models import Action
from server.environment import CognitiveCompanionEnvironment


def snapshot(seed, actions):
    env = CognitiveCompanionEnvironment()
    obs = env.reset(seed=seed, difficulty="hard", clear_qtable=True)
    values = [(obs.task_type, obs.progress, obs.stuck_level, obs.time_left)]
    for action in actions:
        obs = env.step(Action(action=action))
        values.append((obs.task_type, obs.progress, obs.stuck_level, obs.time_left, obs.reward, obs.done))
    return values


def test_seed_replays_reset_and_step_without_server():
    actions = ["continue", "intervene", "switch_task", "continue"]
    assert snapshot(42, actions) == snapshot(42, actions)
    assert snapshot(43, actions) != snapshot(42, actions)


def test_reset_reseeds_same_instance():
    env = CognitiveCompanionEnvironment()
    first = env.reset(seed=11, difficulty="easy")
    initial = (first.task_type, first.stuck_level)
    env.step(Action(action="continue"))
    second = env.reset(seed=11, difficulty="easy")
    assert (second.task_type, second.stuck_level) == initial


def test_episode_rewards_stay_bounded_offline():
    env = CognitiveCompanionEnvironment()
    obs = env.reset(seed=9, difficulty="easy")
    for _ in range(30):
        if obs.done:
            break
        obs = env.step(Action(action="continue"))
        assert 0.05 <= obs.reward <= 0.95
    assert obs.done
