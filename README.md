---
title: "Cognitive Companion OpenEnv"
emoji: "🧠"
colorFrom: "blue"
colorTo: "green"
sdk: "docker"
pinned: false
---

# 🧠 Cognitive Companion

**An environment for figuring out when your AI teammate should shut up — and when it should actually step in to save you.**

> **🚀 Live Demo** — [Open the Dashboard on Hugging Face Spaces](https://maybesomeone19-cognitive-companion-openenv.hf.space/dashboard/index.html)

![Cognitive Companion Dashboard](https://raw.githubusercontent.com/MaybeSomeone-arc18/cognitive-companion-openenv/main/dashboard/screenshot.png)

---

## The Problem

AI assistants have a timing problem. They either over-help — interrupting your flow with suggestions you didn't ask for — or sit idle while you're stuck on something you'll never solve alone. Everyone benchmarks *what* an LLM knows. Almost nobody measures *when* it should speak up.

I built this because poorly-timed interruptions destroy flow state. Cognitive Companion is an OpenEnv-compatible environment designed to train and evaluate agents on intervention timing, not just answer quality.

---

## How It Works

The environment simulates a human working on a task under time pressure. An AI agent watches the human's state and decides what to do.

- **🧪 Environment** — The user's `progress`, `stuck_level`, and `time_left` shift each step based on whether the agent helps or stays quiet.

- **🤖 Agent** — Every step, it picks one of three actions:
  - `continue` — stay silent, let the human work.
  - `intervene` — step in and help.
  - `switch_task` — change the task to reset frustration.

- **👁️ Telemetry** — The agent sees `task_type`, `progress`, `stuck_level`, `time_left`, and `intervention_available`.

- **🏆 Reward Shaping** — Dense feedback at every step:
  - Respecting flow when frustration is low → positive reward.
  - Watching the user spiral without helping → penalty.
  - Well-timed intervention when `stuck_level > 0.6` → large reward.
  - Premature intervention → penalty.
  - Task completion → up to +0.95 bonus.

---

## Quickstart

**1. Clone & install**

```bash
git clone https://github.com/MaybeSomeone-arc18/cognitive-companion-openenv.git
cd cognitive-companion-openenv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Start the server**

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

**3. Try it out**

Start a new episode:

```bash
curl -s http://localhost:7860/reset \
  -X POST -H "Content-Type: application/json" \
  -d '{"difficulty": "medium"}' | python3 -m json.tool
```

Take an action:

```bash
curl -s http://localhost:7860/step \
  -X POST -H "Content-Type: application/json" \
  -d '{"action": "intervene"}' | python3 -m json.tool
```

You should be up and running in under two minutes.

---

## Baseline Agent

Rather than jumping straight to an LLM, I wrote a simple deterministic baseline first. It watches for consecutive errors or stalled progress, and intervenes only when those thresholds are crossed.

**Run it:**

```bash
python run_baseline.py
```

Outputs a clean JSON summary:
`{"episode_id": "baseline-run", "total_steps": 16, "total_reward": 2.56, "interventions": 2, "completion": 0.95}`

*(If you want to try an LLM-based agent instead, `inference.py` handles that.)*

---

## Dashboard

Reading terminal output gets old fast. So I built a real-time dashboard — dark mode, glassmorphism, wired directly to the API.

**🔗 [Open live on Hugging Face Spaces](https://maybesomeone19-cognitive-companion-openenv.hf.space/dashboard/index.html)**

**Run locally instead:**

```bash
# 1. Start the API
uvicorn server.app:app --port 7860

# 2. Open the dashboard
open dashboard/index.html
```

It shows a live frustration meter, a step-by-step timeline of `STAY SILENT` vs `INTERVENE` decisions, and a short narrative of how the episode played out.

---

## Metrics & Telemetry

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

All scores and rewards are strictly inside `(0, 1)` — never exactly 0 or 1.

---

## Background

I originally built this for the **Meta PyTorch OpenEnv Hackathon**. It started as a quick prototype and grew into a full OpenEnv-spec environment with typed Pydantic models, YAML task definitions, automated grading, and a Dockerized deployment.

It's now a reusable arena for RL research, agent evaluation, or anyone who wants to explore optimal intervention timing in human-AI collaboration.

---

## Tech Stack & Structure

**Stack:** Python · FastAPI · Pydantic · OpenEnv · OpenAI SDK · Docker · Hugging Face Spaces

```
cognitive-companion-openenv/
├── server/
│   ├── app.py              # FastAPI app — routes, /baseline/run-once, /dashboard
│   └── environment.py      # Core env logic — Q-learning, reward shaping
├── dashboard/
│   ├── index.html          # Dashboard UI
│   ├── styles.css          # Dark mode + glassmorphism
│   └── app.js              # Fetches /baseline/run-once and animates results
├── models.py               # Pydantic models: Action, CognitiveObservation, EnvState
├── graders.py              # Score grader — trajectory → clamped score in (0, 1)
├── client.py               # OpenEnv-compatible client
├── inference.py            # LLM-based agent with structured logging
├── baseline_agent.py       # Heuristic baseline (intervene on stuck/errors)
├── run_baseline.py         # CLI runner — prints episode summary as JSON
├── tests/
│   └── test_env_baseline.py  # Smoke tests with server-up guard
├── openenv.yaml            # Task definitions, schema, grader config
├── Dockerfile              # python:3.11-slim, port 7860
└── requirements.txt        # Dependencies
```

---

## Future Work

- **RL Agents** — Benchmark trained policies (PPO, DQN) against the heuristic baseline.
- **More Task Types** — Add debugging, research, and long-form writing scenarios with different flow dynamics.
- **Multi-turn Dialogue** — Intervening is one thing; saying something useful is another. I want to grade the *quality* of the help, not just the timing.