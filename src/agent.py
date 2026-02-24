from dataclasses import dataclass
from typing import List, Optional, Literal

Metric = Literal["distance", "duration"]


@dataclass
class AgentDecision:
    optimize_for: Metric
    reason: str


class RouteAgent:
    """
    Minimal agent:
    - Chooses whether to optimize for distance (miles) or duration (minutes)
    - Uses simple heuristics based on your problem context
    """

    def choose_metric(
        self,
        students: List[int],
        capacities: List[int],
        prefer: Optional[Metric] = None,
        traffic_sensitive: bool = False,
        time_windows: bool = False,
    ) -> AgentDecision:
        # Hard override if you pass a preference (acts like a toggle)
        if prefer in ("distance", "duration"):
            return AgentDecision(optimize_for=prefer, reason=f"Manual override: {prefer}")

        # If time windows exist, duration is usually the right objective
        if time_windows:
            return AgentDecision(optimize_for="duration", reason="Time windows enabled -> optimize duration")

        # If traffic-sensitive, duration is usually more relevant
        if traffic_sensitive:
            return AgentDecision(optimize_for="duration", reason="Traffic-sensitive routing -> optimize duration")

        # Heuristic: if system utilization is high, optimizing duration can reduce bottlenecks
        total_students = sum(int(x) for x in students)
        total_capacity = sum(int(c) for c in capacities) if capacities else 0
        utilization = (total_students / total_capacity) if total_capacity else 0.0

        if utilization >= 0.85:
            return AgentDecision(
                optimize_for="duration",
                reason=f"High utilization ({utilization:.0%}) -> optimize duration",
            )

        return AgentDecision(optimize_for="distance", reason=f"Default choice (utilization {utilization:.0%}) -> optimize distance")