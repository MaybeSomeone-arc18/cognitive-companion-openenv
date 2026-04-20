---
title: "Cognitive Companion OpenEnv"
emoji: "🧠"
colorFrom: "blue"
colorTo: "green"
sdk: "docker"
pinned: false
---

# 🧠 Cognitive Companion

**An OpenEnv‑compatible environment to evaluate when an AI "cognitive companion" should intervene in a user's workflow — and when it should stay silent.**

---

## Why This Exists

AI assistants have a timing problem. They either over‑help — interrupting you mid‑flow with suggestions you didn't ask for — or under‑help, sitting idle while you grind on a problem you'll never solve alone. Most benchmarks test *answer quality*, but none of them test the thing that actually matters in a real work session: **should the assistant speak up right now, or shut up?**

Cognitive Companion is an environment built to answer that question. It lets you train and evaluate agents on *intervention timing*, not just intervention content.

---

## How It Works

The environment simulates a human working on a task (coding or writing content) across a finite number of time steps. An AI agent observes the human's state and decides what to do.

- **🧪 Environment** — Simulates a user working under time pressure. The user's `progress`, `stuck_level`, and `time_left` evolve each step based on the agent's actions.

- **🤖 Agent** — At every step, chooses one of three actions:
  - `continue` — let the user stay in flow.
  - `intervene` — step in and help.
  - `switch_task` — change the task entirely to reset frustration.

- **👁️ Observations** — The agent sees the user's current `task_type`, `progress`, `stuck_level`, `time_left`, and whether `intervention_available` is true.

- **🏆 Reward** — Dense, shaped feedback at every step:
  - Respecting flow when stuck is low → positive reward.
  - Letting the user grind while highly stuck → penalty.
  - Well‑timed intervention when stuck > 0.6 → large positive reward.
  - Premature intervention → penalty.
  - Task completion → bonus up to +0.95.

---

## Quickstart

**1. Clone & install**

```bash
git clone https://github.com/sanskar-mk2/cognitive-companion-openenv.git
cd cognitive-companion-openenv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Start the environment server**

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

**3. Hit an endpoint**

Reset an episode and take a step:

```bash
# Reset (start a new episode on "medium" difficulty)
curl -s http://localhost:7860/reset \
  -X POST -H "Content-Type: application/json" \
  -d '{"difficulty": "medium"}' | python3 -m json.tool
```

```json
{
  "task_type": "coding",
  "progress": 0.01,
  "stuck_level": 0.45,
  "time_left": 25,
  "intervention_available": true,
  "reward": null,
  "done": false
}
```

```bash
# Step (take an action)
curl -s http://localhost:7860/step \
  -X POST -H "Content-Type: application/json" \
  -d '{"action": "intervene"}' | python3 -m json.tool
```

```json
{
  "task_type": "coding",
  "progress": 0.32,
  "stuck_level": 0.12,
  "time_left": 24,
  "intervention_available": true,
  "reward": 0.55,
  "done": false
}
```

You should be up and running in under 2 minutes.

---

## Baseline Agent

This provides a reproducible, rule‑based baseline for evaluating intervention timing. It automatically intervenes after a set number of steps without progress or consecutive errors.

**Run it:**

```bash
python run_baseline.py
```

**What it prints:**

```json
=== Starting Baseline Episode ===

=== Baseline episode summary ===
Total steps:        16
Total reward:       2.560
Total interventions:2
Task completion:    0.950
{'total_steps': 16, 'total_reward': 2.56, 'interventions': 2, 'completion': 0.95}
```

There's also a LLM-based agent script available as `inference.py` and a local test script that compares a "always continue" strategy in `test_env.py`.

---

## Dashboard

A real-time visualization of the baseline agent's decision-making — built as a dark-mode single-page UI wired directly to the API.

**Open locally (requires API running on port 7860):**

```bash
open dashboard/index.html
```

**Or visit it on the deployed Space:**

```
http://localhost:7860/dashboard
```

The dashboard shows:
- **Last baseline run card** — reward, steps, interventions, completion.
- **Frustration meter** — live `stuck_level` readout from each step.
- **Episode log** — step-by-step timeline with STAY SILENT / INTERVENE chips.
- **How it thinks** — the two heuristic rules rendered as readable logic.
- **Narrative strip** — a one-sentence story of how the episode played out.

---

## Metrics & Logs

**Per‑step fields** (returned by `/step`):

| Field                    | Type    | Description                                    |
| ------------------------ | ------- | ---------------------------------------------- |
| `task_type`              | string  | `"coding"` or `"content"`                      |
| `progress`               | float   | Task completion, in (0, 1)                     |
| `stuck_level`            | float   | User frustration, in (0, 1)                    |
| `time_left`              | int     | Steps remaining                                |
| `intervention_available` | bool    | Whether intervention is allowed                |
| `reward`                 | float   | Shaped reward for the action, in [0.05, 0.95]  |
| `done`                   | bool    | Whether the episode ended                      |
| `metadata`               | object  | Difficulty, step index, Q‑values, state key    |

**Per‑episode summary** (printed by `inference.py`):

```
[END]   success=true steps=14 rewards=0.20,0.10,0.55,0.20,...,0.95 score=0.8742
```

- `success` — `true` if score ≥ 0.5 and no errors.
- `steps` — total steps taken.
- `rewards` — comma‑separated per‑step rewards.
- `score` — final progress clamped to [0.05, 0.95], graded by `ScoreGrader`.

All scores and rewards are **strictly inside (0, 1)** — never exactly 0 or 1.

---

## Project Status & Background

This project was originally built for the **Meta PyTorch OpenEnv Hackathon**. It implements a full OpenEnv‑spec environment — typed models, REST endpoints (`/reset`, `/step`, `/state`), YAML task definitions, graders, a Dockerized deployment, and a baseline inference script.

It's now a reusable environment for **RL research, agent evaluation, and side projects** around the question of optimal intervention timing in human‑AI collaboration.

---

## Tech Stack & Structure

**Stack:** Python · FastAPI · Pydantic · OpenEnv · OpenAI SDK · Docker · Hugging Face Spaces

```
cognitive-companion-openenv/
├── server/
│   ├── app.py              # FastAPI app — OpenEnv routes, /baseline/run-once, /dashboard
│   └── environment.py      # Core environment logic, Q-learning, reward shaping
├── dashboard/
│   ├── index.html          # Single-page UI served at /dashboard
│   ├── styles.css          # Dark glassmorphism design
│   └── app.js              # Fetches /baseline/run-once and animates results
├── models.py               # Pydantic models: Action, CognitiveObservation, EnvState
├── graders.py              # ScoreGrader — maps trajectory → clamped score in (0, 1)
├── client.py               # OpenEnv-compatible client for interacting with the env
├── inference.py            # LLM agent with structured [START]/[STEP]/[END] logging
├── baseline_agent.py       # Heuristic baseline agent (intervene on stuck/errors)
├── run_baseline.py         # CLI runner — prints episode summary as JSON
├── tests/
│   └── test_env_baseline.py  # pytest: reset/step smoke test + reward range check
├── test_env.py             # Legacy local heuristic comparison (no API key needed)
├── openenv.yaml            # Task definitions, action/observation schema, grader config
├── Dockerfile              # python:3.11-slim, exposes port 7860
├── requirements.txt        # fastapi, uvicorn, pydantic, openai, openenv-core, aiofiles
└── pyproject.toml          # Project metadata
```

---

## Future Work

- **Smarter agents** — Replace the heuristic baseline with a trained RL policy (PPO, DQN) or a fine-tuned LLM agent.
- **Richer scenarios** — Add more task types (debugging, research, writing) with different stuck/flow dynamics.
- **Multi-turn dialogue** — Let the agent *say something* when it intervenes, and grade the quality of that help too.