---
title: "Cognitive Companion OpenEnv"
emoji: "🧠"
colorFrom: "blue"
colorTo: "green"
sdk: "docker"
pinned: false
---

# 🧠 Cognitive Companion

**A sandbox to figure out when your AI teammate should shut up, and when it should actually drop in to save you.**

> **🚀 Live Demo** — [Open the Dashboard on Hugging Face Spaces](https://maybesomeone19-cognitive-companion-openenv.hf.space/dashboard/index.html)

![Cognitive Companion Dashboard](https://raw.githubusercontent.com/MaybeSomeone-arc18/cognitive-companion-openenv/main/dashboard/screenshot.png)

---

## The Problem I Needed to Solve

Let's be candid: modern AI assistants have an egregious timing problem. They either over-help—interrupting your state of flow with unsolicited suggestions—or they atrophy, sitting idle while you languish on a bug you'll never decipher solo. The industry loves benchmarking *what* an LLM knows, but almost nobody is measuring the nuance of *when* it should intervene.

I built the Cognitive Companion environment because constant, poorly-timed interruptions annihilate flow state. This is an OpenEnv-compatible arena specifically designed to train and evaluate AI agents on their intervention cadence, not just their intelligence.

---

## How the Architecture Breathes

The environment mimics an anxious human working against the clock. An AI agent acts as the observer, carefully parsing the human's telemetry before making a move.

- **🧪 The Environment** — Simulates human toil. The user's `progress`, `stuck_level`, and `time_left` are volatile metrics that shift dynamically based on whether the agent helps or stays away.

- **🤖 The Agent** — Every tick, it makes a tri-fold decision:
  - `continue` — remain a silent spectator and let the human cook.
  - `intervene` — step into the fray to alleviate friction.
  - `switch_task` — pivot the objective to dissipate mounting frustration.

- **👁️ The Telemetry** — The agent is drip-fed the user's `task_type`, `progress`, `stuck_level`, `time_left`, and an `intervention_available` boolean.

- **🏆 The Shaping** — The reward mechanism is dense and unforgiving:
  - Preserving flow when `stuck_level` is negligible → positive reinforcement.
  - Idly watching the user spiral into frustration → steep penalties.
  - Surgical interventions precisely when `stuck_level > 0.6` → massive rewards.
  - Premature hand-holding → immediate penalty.
  - Pushing the task to completion → up to a +0.95 bonus.

---

## Getting Your Hands Dirty

**1. Clone & Bootstrap**

```bash
git clone https://github.com/MaybeSomeone-arc18/cognitive-companion-openenv.git
cd cognitive-companion-openenv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Ignite the Engine**

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

**3. Test the Plumbing**

Instantiate a pristine episode:

```bash
curl -s http://localhost:7860/reset \
  -X POST -H "Content-Type: application/json" \
  -d '{"difficulty": "medium"}' | python3 -m json.tool
```

Force the agent's hand:

```bash
curl -s http://localhost:7860/step \
  -X POST -H "Content-Type: application/json" \
  -d '{"action": "intervene"}' | python3 -m json.tool
```

You'll be up and running before your coffee gets cold.

---

## The Heuristic Baseline

Instead of immediately throwing a massive LLM at the problem, I wrote a reproducible, deterministic baseline. It tracks heuristics—specifically, intervening only after consecutive errors or stalled progress vectors.

**Run it:**

```bash
python run_baseline.py
```

It'll immediately output a clean, consolidated JSON digest of the run snippet:
`{"episode_id": "baseline-run", "total_steps": 16, "total_reward": 2.56, "interventions": 2, "completion": 0.95}`

*(If you do want to throw an LLM at it, I wrote `inference.py` to handle exactly that.)*

---

## The Dashboard: Visualizing the Agent's Brain

Watching text parse on a terminal gets tedious. So I built a real-time visualization of the baseline agent's decision-making—a dark-mode, glassmorphism UI wired directly to the local telemetry.

**🔗 [Open live on Hugging Face Spaces](https://maybesomeone19-cognitive-companion-openenv.hf.space/dashboard/index.html)**

**Run locally instead:**

```bash
# 1. Start the API
uvicorn server.app:app --port 7860

# 2. Open the dashboard
open dashboard/index.html
```

The dashboard surfaces the agent's internal monologue: it tracks the "frustration meter" in real-time, renders a live timeline mapping out `STAY SILENT` vs `INTERVENE` decisions, and translates the raw metrics into a readable, post-run narrative.

---

## Metrics & Granular Telemetry

**Per‑step fields** (returned via `/step`):

| Field                    | Type    | Description                                    |
| ------------------------ | ------- | ---------------------------------------------- |
| `task_type`              | string  | `"coding"` or `"content"`                      |
| `progress`               | float   | Task completion trajectory, in (0, 1)          |
| `stuck_level`            | float   | Quantified frustration, in (0, 1)              |
| `time_left`              | int     | Steps before hard failure                      |
| `intervention_available` | bool    | Constraints toggle                             |
| `reward`                 | float   | Shaped consequence, firmly in [0.05, 0.95]     |
| `done`                   | bool    | Terminal state indicator                       |

By design, all grades and rewards are strictly clamped inside `(0, 1)`. We don't do absolute bounding zeros or ones here.

---

## Origins and Ecosystem

I originally architected this for the **Meta PyTorch OpenEnv Hackathon**. What started as a conceptual MVP has fleshed out into a full OpenEnv-spec'd framework, complete with strictly validated Pydantic payloads, YAML task scaffolding, autonomous grading scripts, and a self-contained Docker orchestration.

It's evolved into a highly robust arena for researchers and devs exploring RL, fine-tuning scenarios, or frankly, just trying to teach machines basic situational awareness.

---

## Tech Stack & Architecture Topology

**The Arsenal:** Python · FastAPI · Pydantic · OpenEnv · OpenAI SDK · Docker · Hugging Face Spaces

```
cognitive-companion-openenv/
├── server/
│   ├── app.py              # Application core — routes, bindings, and /dashboard surfacing
│   └── environment.py      # The engine — Q-learning, state permutations, reward shaping
├── dashboard/
│   ├── index.html          # Semantic skeletal structure
│   ├── styles.css          # Glassmorphism aesthetics and keyframe kinematics
│   └── app.js              # Fetch layer binding the UI to /baseline/run-once
├── models.py               # Pydantic schemas validating our telemetry
├── graders.py              # Evaluator reducing temporal trajectories to a single score
├── client.py               # OpenEnv-compliant ingestion client
├── inference.py            # Baseline LLM agent orchestrator
├── baseline_agent.py       # Deterministic heuristic fallback
├── run_baseline.py         # CLI runner emitting clean telemetry blocks
├── tests/
│   └── test_env_baseline.py  # Self-contained smoke tests with server guards
├── openenv.yaml            # Environment schematics & grader bindings
├── Dockerfile              # Immutable, portable container configs
└── requirements.txt        # The dependency tree
```

---

## The Roadmap Ahead

- **Neuro-Symbolic Upgrades** — Benchmarking pure RL algorithms (PPO) against the heuristic foundations.
- **Task Expansion** — Integrating debugging topologies, research labyrinths, and long-form writing tasks to see how flow disruption changes per domain.
- **Multi-turn Dialogue** — It's one thing to intervene; it's another entirely to say something actually useful. I plan to fold in LLM dialogue extraction to grade the *quality* of the help alongside the timing.