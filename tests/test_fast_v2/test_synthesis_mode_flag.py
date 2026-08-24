"""Test 19/20: Legacy stays default; fast_v2 only activates on explicit opt-in."""
from __future__ import annotations

import pytest

from src.config import Settings


def test_legacy_is_the_default_synthesis_mode():
    """Test 19: a Settings built with no SYNTHESIS_MODE resolves to legacy."""
    settings = Settings(_env_file=None)
    assert settings.synthesis_mode == "legacy"


def test_fast_v2_only_activates_when_explicitly_selected():
    """Test 20: fast_v2 is reachable only by naming it exactly."""
    default = Settings(_env_file=None)
    assert default.fast_v2_enabled is False

    explicit = Settings(_env_file=None, synthesis_mode="fast_v2_experimental")
    assert explicit.synthesis_mode == "fast_v2_experimental"
    assert explicit.fast_v2_enabled is True


def test_unknown_synthesis_mode_is_rejected_not_silently_downgraded():
    """A typo must fail loudly rather than silently running the wrong pipeline."""
    with pytest.raises(Exception):
        Settings(_env_file=None, synthesis_mode="fast_v2")
