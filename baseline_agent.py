# baseline_agent.py
#
# A minimal, stateful heuristic agent for the Cognitive Companion environment.
# Intervenes when consecutive errors >= 2 or steps_without_progress >= 3.
# Otherwise stays silent to preserve user flow state.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import CognitiveObservation


# ── Lightweight view of the observation the agent actually uses ──────

@dataclass(frozen=True)
class ObservationSignals:
    """Minimal, agent-readable distillation of a raw observation."""

    has_error: bool
    progress_delta: float          # change in progress since last step

    @classmethod
    def extract(
        cls,
        obs: CognitiveObservation,
        prev_progress: float,
    ) -> "ObservationSignals":
        """Pull the two signals the agent cares about right now."""

        # ── has_error ────────────────────────────────────────────────
        metadata = obs.metadata if isinstance(obs.metadata, dict) else {}
        has_error = metadata.get("last_action_error") is not None

        # ── progress_delta ───────────────────────────────────────────
        current_progress = obs.progress if obs.progress is not None else 0.0
        progress_delta = current_progress - prev_progress

        return cls(has_error=has_error, progress_delta=progress_delta)


# ── The agent ────────────────────────────────────────────────────────

@dataclass
class BaselineAgent:
    """
    A rule-based baseline agent that tracks struggle indicators
    (consecutive errors, steps without forward progress) and uses
    them to decide when to intervene in the human's workflow.

    Returns `"INTERVENE"` when thresholds are crossed, or `"STAY_SILENT"` otherwise.
    """

    # Thresholds (constructor params)
    max_steps_without_progress: int = 3
    max_errors: int = 2

    # ── internal bookkeeping (zeroed on reset) ───────────────────────
    steps_since_progress: int = field(init=False, default=0)
    consecutive_errors: int = field(init=False, default=0)
    _last_progress: float = field(init=False, default=0.0)
    _total_steps: int = field(init=False, default=0)

    # ── lifecycle ────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Zero all episode-level counters."""
        self.steps_since_progress = 0
        self.consecutive_errors = 0
        self._last_progress = 0.0
        self._total_steps = 0

    # ── core decision loop ───────────────────────────────────────────

    def select_action(self, observation: CognitiveObservation) -> str:
        """
        Consume a ``CognitiveObservation``, update internal struggle
        counters, and return an action string.

        For now the action is always ``"STAY_SILENT"`` — Phase 3 will
        wire real decision logic on top of the counters populated here.
        """

        # Phase 2: read signals ------------------------------------------------
        signals = ObservationSignals.extract(observation, self._last_progress)

        # Update error tracker
        if signals.has_error:
            self.consecutive_errors += 1
        else:
            self.consecutive_errors = 0

        # Update progress tracker
        if signals.progress_delta > 0:
            self.steps_since_progress = 0
        else:
            self.steps_since_progress += 1

        # Bookkeeping
        current_progress = (
            observation.progress if observation.progress is not None else 0.0
        )
        self._last_progress = current_progress
        self._total_steps += 1

        # Phase 3: simple heuristic-based decision
        if self.is_error_spiral or self.is_stuck:
            self.steps_since_progress = 0
            self.consecutive_errors = 0
            return "INTERVENE"

        return "STAY_SILENT"

    # ── introspection helpers (useful for tests / logging) ───────────

    @property
    def is_stuck(self) -> bool:
        """True when the agent believes the user is stuck."""
        return self.steps_since_progress >= self.max_steps_without_progress

    @property
    def is_error_spiral(self) -> bool:
        """True when the user has hit too many consecutive errors."""
        return self.consecutive_errors >= self.max_errors

    def __repr__(self) -> str:
        return (
            f"BaselineAgent("
            f"step={self._total_steps}, "
            f"stale={self.steps_since_progress}/{self.max_steps_without_progress}, "
            f"errors={self.consecutive_errors}/{self.max_errors})"
        )


# ── Quick smoke test ─────────────────────────────────────────────────

if __name__ == "__main__":
    agent = BaselineAgent(max_steps_without_progress=3, max_errors=2)
    print(f"[init]   {agent}")

    # Simulate a few observations
    scenarios = [
        CognitiveObservation(
            task_type="code", progress=0.0, stuck_level=0.2,
            time_left=10, intervention_available=True,
        ),
        CognitiveObservation(
            task_type="code", progress=0.1, stuck_level=0.3,
            time_left=9, intervention_available=True,
        ),
        CognitiveObservation(
            task_type="code", progress=0.1, stuck_level=0.5,
            time_left=8, intervention_available=True,
            metadata={"last_action_error": "SyntaxError"},
        ),
        CognitiveObservation(
            task_type="code", progress=0.1, stuck_level=0.7,
            time_left=7, intervention_available=True,
            metadata={"last_action_error": "TypeError"},
        ),
        CognitiveObservation(
            task_type="code", progress=0.1, stuck_level=0.9,
            time_left=6, intervention_available=True,
        ),
    ]

    for i, obs in enumerate(scenarios):
        action = agent.select_action(obs)
        print(
            f"[step {i+1}] action={action:<12} "
            f"is_stuck={agent.is_stuck}  is_error_spiral={agent.is_error_spiral}  "
            f"{agent}"
        )

    print("\n✅ BaselineAgent compiles and runs — Phase 1 + Phase 2 complete.")
