import random
from models import Action
from server.environment import CognitiveCompanionEnv

def test_heuristic(name: str, use_heuristic: bool, steps: int = 15):
    print(f"=== {name} ===")
    
    env = CognitiveCompanionEnv()
    random.seed(42) # Use fixed seed to compare the exact same starting conditions
    env.reset(difficulty="hard") # Start stuck so the heuristic actually triggers
    
    total_reward = 0.0
    for i in range(steps):
        s = env.state()
        if use_heuristic and s.stuck_level > 0.7:
            act = "intervene"
        else:
            act = "continue"
            
        res = env.step(act)
        total_reward += res.reward
        
        print(f"Step {i+1:2d} | Action: {act:11s} | Prog: {res.state.progress:.2f} | Stuck: {res.state.stuck_level:.2f} | Reward: {res.reward:5.2f} | Done: {res.done}")
        
        if res.done:
            break
            
    print(f"Total Cumulative Reward -> {total_reward:.2f}\n")


if __name__ == "__main__":
    test_heuristic("Brute Force Strategy (always 'continue')", use_heuristic=False)
    test_heuristic("Smart Heuristic (intervene if stuck > 0.7)", use_heuristic=True)
