---
title: "Cognitive Companion OpenEnv"
emoji: "🧠"
colorFrom: "blue"
colorTo: "green"
sdk: "docker"
sdk_version: "0.0.1"
pinned: false
---
# Cognitive Companion: Intervention-Aware Work Environment
*A simulation teaching AI agents when to intervene and when to stay out of the way.*

## Concept
The **Cognitive Companion Environment** simulates a human working on a task. As the user works, their `progress` and `stuck_level` fluctuate. The companion AI agent must decide whether to quietly `continue`, actively `intervene`, or suggest to `switch_task`.

This teaches agents timing: intervening during a "flow state" is disruptive and penalized, but waiting too long when the user is deeply stuck results in painful grinding and negative rewards. The AI must learn the ideal intervention window based on real-time frustration levels.

## Environment API
Built using FastAPI, the environment exposes a straightforward REST API:
- `POST /reset`: Accepts a `ResetRequest` tracking `{ "difficulty": "medium" }`. Resets the episode and returns the initial `State`.
- `POST /step`: Accepts an `Action` JSON payload `{ "action": "continue" }` and processes a single time step, returning a `StepResult`.
- `GET /state`: Returns the current `State` of the environment without advancing time.
- `GET /health`: Basic health check returning status ok.

## State Space
The environment uses a continuous observation space with a limited time horizon.

Example JSON:
```json
{
  "task_type": "coding",
  "progress": 0.35,
  "stuck_level": 0.85,
  "time_left": 15,
  "intervention_available": true
}
```

- **`task_type`**: Currently `"coding"` or `"content"`.
- **`progress`**: Float from `0.0` to `1.0` (task completion benchmark).
- **`stuck_level`**: Float from `0.0` to `1.0` (user frustration/blockage metric).
- **`time_left`**: Steps remaining before episode termination.
- **`intervention_available`**: Boolean flag indicator.

## Action Space
The companion chooses among three discrete actions per step:
- **`continue`**: Do nothing. Good when the user is in flow (`stuck_level` is low). Bad when they are stuck, causing heavy frustration.
- **`intervene`**: Offer assistance. Good when `stuck_level > 0.6`, clearing the block and giving massive progress. Bad when done too early (breaks flow).
- **`switch_task`**: Pivot directions. Toggle `task_type`. Halves progress but resets `stuck_level`. Applies a small baseline penalty. Best used sparingly if time is bleeding and progress is nil.

## Reward Design
Rewards range predominantly between `[-1.0, 1.0]`:
- **Good Continuation**: `+0.05` to `+0.2` (Flow state maintained).
- **Grinding While Stuck**: `-0.2` to `-0.4` (Letting the user suffer at `stuck_level > 0.7`).
- **Good Intervention**: `+0.5` to `+0.6` (Intervening closely at the right moment).
- **Bad Intervention**: `-0.3` (Early interruption, annoyance).
- **Switching Tasks**: `-0.2` (Overhead penalty for completely shifting gears unless critically beneficial `+0.3`).
- **Completion Bonus**: Flat `+1.0` (Whenever `progress` securely hits `1.0`).

## Scenarios & Difficulty Graders
The tasks are tracked and judged through three different difficulty settings using custom evaluations (`ScoreGrader` mapped across OpenEnv configurations):
- **`easy`**: Starts with very low `stuck_level` (`0.1 - 0.3`) and grants `30` time steps.
- **`medium`**: Starts moderately stuck (`0.3 - 0.6`) and gives `25` time steps.
- **`hard`**: Starts heavily stuck (`0.6 - 0.9`), giving only `20` time steps. A strong companion response is required immediately!

Outputs automatically scale final `progress` results cleanly representing native `0.0 -> 1.0` evaluations!

## Running Locally

1. Create a `virtualenv` and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install standard dependencies:
   ```bash
   pip install fastapi uvicorn[standard] pydantic requests openai
   ```
3. Run the backend server locally:
   ```bash
   uvicorn server.app:app --reload
   ```
4. Run the baseline evaluation agent mapping LLMs explicitly (while the server runs):
   ```bash
   export ENV_BASE_URL="http://localhost:8000"
   export API_BASE_URL="https://api.openai.com/v1"
   export HF_TOKEN="your-key-here"
   python inference.py
   ```

## Deploying on HF Spaces (Docker)
The attached `server/Dockerfile` operates `python:3.11-slim`, porting automatically through Port `7860`. You can easily compile this build setting the Environment Space directly inside HF deployments securely wrapping the local `openai` integrations securely isolated on-chain.
