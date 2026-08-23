"""SLR Swarm — kiến trúc multi-agent theo Phase2 Master Plan (LangGraph supervisor)."""

from src.agents.slr_swarm.graph import (
    build_data_graph,
    build_slr_graph,
    run_data_analysis,
    run_slr,
)
from src.agents.slr_swarm.ports import ModelRouter, SwarmDeps

__all__ = [
    "ModelRouter",
    "SwarmDeps",
    "build_data_graph",
    "build_slr_graph",
    "run_data_analysis",
    "run_slr",
]
