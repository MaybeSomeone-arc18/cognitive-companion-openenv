import os
import json
from openai import OpenAI
from models import Action
from client import reset, step

# Explicitly decoupling the Environment interface from configuring OpenAI hooks natively.
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1") 
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", "dummy-key"))

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

def get_action_from_llm(state_dict) -> str:
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
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        act_str = response.choices[0].message.content.strip().lower()
        if act_str not in ["continue", "intervene", "switch_task"]:
            act_str = "continue" # fallback
        return act_str
    except Exception as e:
        # Fallback heuristic if LLM routing fails entirely preventing inference lockups
        stuck = state_dict.get("stuck_level", 0.0)
        return "intervene" if stuck > 0.7 else "continue"

def run():
    difficulties = ["easy", "medium", "hard"]
    episodes_per_diff = 3
    
    for diff in difficulties:
        for episode in range(1, episodes_per_diff + 1):
            state = reset(ENV_BASE_URL, difficulty=diff)
            
            # Print standard START tag required by bootcamps
            start_payload = {
                "episode": episode,
                "task": diff,
            }
            print(f"[START] {json.dumps(start_payload)}")
            
            done = False
            total_reward = 0.0
            step_idx = 1
            
            while not done:
                state_dict = state.model_dump() if hasattr(state, "model_dump") else state.dict()
                chosen_act_str = get_action_from_llm(state_dict)
                act = Action(action=chosen_act_str)
                
                result = step(ENV_BASE_URL, act)
                
                # Emit STEP JSON formatted properly
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
                
            # Score mocks the formal trajectory tracking mapped 0.0 to 1.0 reliably.
            final_progress = state.progress
            score = float(max(0.0, min(1.0, final_progress)))
            
            end_payload = {
                "episode": episode,
                "task": diff,
                "total_reward": total_reward,
                "score": score
            }
            print(f"[END] {json.dumps(end_payload)}")

if __name__ == "__main__":
    run()
