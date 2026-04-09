---
title: "Cognitive Companion OpenEnv"
emoji: "🧠"
colorFrom: "blue"
colorTo: "green"
sdk: "docker"
pinned: false
---
# Cognitive Companion: Intervention-Aware Work Environment

A real‑world style OpenEnv environment that tests **when** an AI companion should help a human, not just **how**.

---

## 1. Overview

Cognitive Companion simulates a person working on a task (coding or content).  
At each step, the agent must choose exactly one of:

- `continue` – let them stay in flow  
- `intervene` – step in and help  
- `switch_task` – change the task to reset context  

The goal is to learn **intervention timing**: interrupting too early breaks flow, waiting too long leaves the user grinding while stuck. The environment is fully OpenEnv‑compatible and designed to match all Round 1 requirements.

---

## 2. OpenEnv & Round 1 Compliance

This project implements a complete OpenEnv environment as required in the Round 1 problem statement:

- **Real‑world task**: study / work session (coding and content tasks), not a toy game.
- **Full OpenEnv spec**:
  - Typed models for `State`, `Action`, and `StepResult`.
  - REST endpoints: `/reset`, `/step`, `/state`.
  - `openenv.yaml` describing tasks and graders.
- **3 tasks**: `easy`, `medium`, `hard`, each with a grader and score strictly in `(0, 1)`.
- **Meaningful reward function**: dense feedback for progress, flow, and frustration.
- **Baseline `inference.py`**:
  - Uses OpenAI Client.
  - Uses `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`.
  - Emits strictly formatted `[START]`, `[STEP]`, `[END]` logs.
- **Deployment**:
  - Dockerfile based on `python:3.11-slim`.
  - Deployed as a Docker Space on Hugging Face.

---

## 3. Environment Design

### 3.1 State Space

The environment exposes a continuous observation space with a finite horizon. Example:

```json
{
  "task_type": "coding",
  "progress": 0.35,
  "stuck_level": 0.85,
  "time_left": 15,
  "intervention_available": true
}
```

- `task_type` (str): `"coding"` or `"content"`.
- `progress` (float): normalized task completion, strictly in `(0, 1)`.
- `stuck_level` (float): user frustration / blockage, strictly in `(0, 1)`.
- `time_left` (int): steps before the episode ends.
- `intervention_available` (bool): whether the agent can currently intervene.

### 3.2 Action Space

At each step, the agent chooses one discrete action:

- `continue`  
  Do nothing. Suitable when `stuck_level` is low (user in flow).  
  Harmful if user is highly stuck and time is being wasted.

- `intervene`  
  Offer help. Powerful when `stuck_level` is high (unblocks and boosts `progress`).  
  Penalized if used too early, interrupting productive flow.

- `switch_task`  
  Change the task type (e.g., coding → content).  
  - Toggles `task_type`
  - Halves current `progress`
  - Resets `stuck_level`
  - Applies a small baseline penalty  
  Useful when progress is very low, time is short, and `stuck_level` is very high.

### 3.3 Reward Function

Rewards are shaped to encourage:

- Preserving flow when the user is not stuck.
- Reducing unproductive grinding when frustration is high.
- Completing tasks when possible.

Approximate reward design:

- Good continuation (low `stuck_level`): `+0.1` to `+0.2`.
- Grinding while stuck (`stuck_level > 0.7`): `-0.2` to `-0.4`.
- Good intervention (well‑timed help): `+0.5` to `+0.6`.
- Bad intervention (too early): `-0.3`.
- Switch task: baseline `-0.2`, up to `+0.3` if it rescues a failing episode.
- Completion bonus: up to `+0.95` when `progress` reaches `0.99`.

All rewards and scores are clamped into `[0.05, 0.95]` — strictly inside `(0, 1)`.

---

## 4. Tasks & Graders

The environment defines three difficulty levels in `openenv.yaml`, all using a shared grader `graders.default_grader`.

### 4.1 Tasks

- `easy`  
  - Initial `stuck_level`: `0.1–0.3`.  
  - Time steps: `30`.  
  - Focus: basic boundary of when to intervene vs stay silent.

- `medium`  
  - Initial `stuck_level`: `0.3–0.6`.  
  - Time steps: `25`.  
  - Focus: adapting interventions as frustration and time pressure change.

- `hard`  
  - Initial `stuck_level`: `0.6–0.9`.  
  - Time steps: `20`.  
  - Focus: urgent, early, and correct interventions under strict deadlines.

### 4.2 Grading Logic – `ScoreGrader`

`ScoreGrader` is an OpenEnv‑compatible grader that maps the full trajectory to a normalized score:

- Input: the **entire episode trajectory** (list of step dictionaries).
- It inspects the final step's `state.progress`.
- Output: final progress clamped into `[0.05, 0.95]` (strictly inside `(0, 1)`):

```python
final_step = trajectory[-1]
final_state = final_step.get("state", {})
progress = final_state.get("progress", 0.05)
score = clamp_score(progress)  # always in [0.05, 0.95]
```

This satisfies the requirement that task scores are real‑valued, normalized, and strictly between 0 and 1.

---

## 5. API: FastAPI + OpenEnv

The environment is implemented with FastAPI and exposes the standard OpenEnv endpoints:

- `POST /reset`  
  Request body: `{"difficulty": "easy" | "medium" | "hard"}`.  
  - Initializes a new episode for the given difficulty.
  - Samples `task_type`, `progress`, `stuck_level`, `time_left`.
  - Returns the initial `State`.

- `POST /step`  
  Request body: `{"action": "continue" | "intervene" | "switch_task"}`.  
  - Advances the environment by one step.
  - Applies the action and reward logic.
  - Returns a `StepResult` with:
    - `state`
    - `reward`
    - `done`
    - additional metadata (e.g. `q_values`, `history_length`, `epsilon`).

- `GET /state`  
  Returns the current `State` without advancing time.

- `GET /health`  
  Health‑check endpoint used by validators to confirm availability.

`openenv.yaml` declares:

- Environment name and description.
- Endpoint paths for `reset`, `step`, and `state`.
- Task definitions (`easy`, `medium`, `hard`) and their grader (`graders.default_grader`).

---

## 6. Baseline Inference Script (`inference.py`)

A baseline agent is provided to demonstrate how to interact with the environment and to satisfy the evaluation requirements.

### 6.1 Configuration

`inference.py` expects the following environment variables:

- `ENV_BASE_URL` – base URL of the environment (default: `http://localhost:7860`).
- `API_BASE_URL` – LLM API endpoint (e.g. `https://api.openai.com/v1`).
- `MODEL_NAME` – model identifier for the LLM.
- `HF_TOKEN` – API key (Hugging Face / OpenAI). **Required**.

The script uses the **OpenAI Client** with these parameters.

### 6.2 Policy Logic

`get_action_from_llm(obs)`:

- Serializes the current state as a dict.
- Sends a system prompt that:
  - Describes the companion's role.
  - Defines the three actions.
  - Specifies decision rules in terms of `stuck_level`, `progress`, and `time_left`.
  - Instructs the model to reply with exactly one token:
    - `continue`, `intervene`, or `switch_task`.
- Parses the response:
  - If invalid, falls back to `continue`.
  - On LLM failure, uses a heuristic: if `stuck_level > 0.7` → `intervene`, else `continue`.

### 6.3 Logging Format (Required)

For compliance with the Round 1 validator, `inference.py` emits structured stdout logs:

```
[START] task=<task_name> env=cognitive_companion model=<model_name>
[STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn> score=<0.0000>
```

All reward and score values are:
- Formatted to 2 decimal places (rewards) or 4 decimal places (score).
- Strictly within `(0, 1)` — never exactly 0 and never exactly 1.

---

## 7. Running Locally

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the environment server:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

4. In a separate terminal, set the required variables and run the baseline agent:

```bash
export ENV_BASE_URL="http://localhost:7860"
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-key-here"

python inference.py
```

You should see `[START]`, `[STEP]`, and `[END]` logs for all three task difficulties.

---

## 8. Hugging Face Spaces (Docker)

The repository includes a Docker setup compatible with Hugging Face Spaces:

- Base image: `python:3.11-slim`.
- Installs project dependencies.
- Exposes port `7860`.
- Launches the FastAPI app.

When connected to a Docker‑type Space:

- Hugging Face builds using the provided Dockerfile.
- The deployed Space:
  - Responds to `/health` for availability checks.
  - Exposes `/reset`, `/step`, `/state` for OpenEnv interaction.
- The same `inference.py` can target the Space by setting `ENV_BASE_URL` to the Space URL.

This satisfies the requirement for a **deployed, Dockerized OpenEnv environment** with a working baseline evaluation script.