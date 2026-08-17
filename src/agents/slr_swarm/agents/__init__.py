"""5 tác tử của SLR Swarm (§5 Master Plan)."""

from src.agents.slr_swarm.agents.code_copilot import run_code_copilot
from src.agents.slr_swarm.agents.gap_finder import run_gap_finder
from src.agents.slr_swarm.agents.peer_screener import run_peer_screener
from src.agents.slr_swarm.agents.prisma_drafter import run_prisma_drafter
from src.agents.slr_swarm.agents.snowball import run_snowball

__all__ = [
    "run_code_copilot",
    "run_gap_finder",
    "run_peer_screener",
    "run_prisma_drafter",
    "run_snowball",
]
