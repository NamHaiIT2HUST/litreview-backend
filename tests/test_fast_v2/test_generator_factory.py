"""Tests for the fast_v2 generator factory and its config defaults."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.synthesis.fast_v2.generator.factory import build_generator
from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator


def test_default_mode_is_fake():
    gen = build_generator("fake")
    assert isinstance(gen, FakeSynthesisGenerator)


def test_remote_openscholar_requires_base_url():
    with pytest.raises(ValueError):
        build_generator("remote_openscholar", base_url=None)


def test_remote_openscholar_builds_with_base_url():
    from src.synthesis.fast_v2.generator.remote_openscholar import RemoteOpenScholarGenerator

    gen = build_generator("remote_openscholar", base_url="http://gpu:8500")
    assert isinstance(gen, RemoteOpenScholarGenerator)
    assert gen.base_url == "http://gpu:8500"


def test_hosted_api_requires_base_url_key_and_model():
    with pytest.raises(ValueError):
        build_generator("hosted_api", hosted_api_base_url=None, hosted_api_key="k", hosted_api_model="m")
    with pytest.raises(ValueError):
        build_generator("hosted_api", hosted_api_base_url="https://x", hosted_api_key=None, hosted_api_model="m")
    with pytest.raises(ValueError):
        build_generator("hosted_api", hosted_api_base_url="https://x", hosted_api_key="k", hosted_api_model=None)


def test_hosted_api_builds_with_full_config():
    from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator

    gen = build_generator(
        "hosted_api", hosted_api_base_url="https://api.example.com/v1",
        hosted_api_key="sk-x", hosted_api_model="gpt-4o-mini",
    )
    assert isinstance(gen, HostedApiGenerator)
    assert gen.base_url == "https://api.example.com/v1"
    assert gen.model == "gpt-4o-mini"


def test_fast_v2_hosted_api_missing_config_fails_loud(monkeypatch):
    """Fast v2 + hosted_api + missing config -> FAIL LOUD, resolved from settings."""
    from src import config as config_module
    from src.config import Settings

    settings = Settings(
        synthesis_mode="fast_v2_experimental", fast_v2_generator="hosted_api",
        fast_v2_hosted_api_base_url="", fast_v2_hosted_api_key="", fast_v2_hosted_api_model="",
    )
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="FAST_V2_HOSTED_API"):
        build_generator()


def test_fast_v2_hosted_api_valid_config_builds_from_settings(monkeypatch):
    from src import config as config_module
    from src.config import Settings
    from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator

    settings = Settings(
        synthesis_mode="fast_v2_experimental", fast_v2_generator="hosted_api",
        fast_v2_hosted_api_base_url="https://api.example.com/v1",
        fast_v2_hosted_api_key="sk-x", fast_v2_hosted_api_model="gpt-4o-mini",
    )
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    gen = build_generator()
    assert isinstance(gen, HostedApiGenerator)


def test_unknown_mode_fails_loudly():
    with pytest.raises(ValueError):
        build_generator("not_a_real_mode")


def test_local_vllm_mode_resolves_to_openscholar_generator_without_loading_a_model():
    from src.synthesis.fast_v2.generator.openscholar import OpenScholarGenerator

    gen = build_generator("local_vllm")
    assert isinstance(gen, OpenScholarGenerator)
    assert gen.is_loaded is False  # construction must not load the 8B model


# --------------------------------------------------------------------------
# Settings defaults: Legacy stays default, Fast v2 opt-in only
# --------------------------------------------------------------------------

def test_synthesis_mode_default_is_legacy():
    from src.config import Settings

    assert Settings().synthesis_mode == "legacy"
    assert Settings().fast_v2_enabled is False


def test_fast_v2_generator_default_is_fake_not_remote_or_local():
    from src.config import Settings

    assert Settings().fast_v2_generator == "fake"


def test_fast_v2_openscholar_base_url_defaults_empty():
    from src.config import Settings

    assert Settings().fast_v2_openscholar_base_url == ""


# --------------------------------------------------------------------------
# CPU-safety: importing the generator factory/remote adapter must not
# require vllm/torch, and must not open a network connection.
# --------------------------------------------------------------------------

def _run_import_probe(module_name: str) -> str:
    code = (
        f"import {module_name}\n"
        "import sys\n"
        "heavy = [m for m in ('torch', 'vllm') if m in sys.modules]\n"
        "print(','.join(heavy))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_importing_generator_factory_does_not_load_vllm_or_torch():
    heavy = _run_import_probe("src.synthesis.fast_v2.generator.factory")
    assert heavy == ""


def test_importing_remote_openscholar_does_not_load_vllm_or_torch():
    heavy = _run_import_probe("src.synthesis.fast_v2.generator.remote_openscholar")
    assert heavy == ""


def test_importing_hosted_api_does_not_load_vllm_or_torch():
    heavy = _run_import_probe("src.synthesis.fast_v2.generator.hosted_api")
    assert heavy == ""


def _settings_with(**overrides):
    from src.config import Settings

    return Settings(**overrides)


def test_legacy_settings_construction_never_fails_on_missing_remote_url():
    """Settings() itself must never fail just because the remote OpenScholar
    URL is unset -- Legacy has to start up regardless of Fast v2 config."""
    from src.config import Settings

    settings = Settings(synthesis_mode="legacy", fast_v2_generator="remote_openscholar",
                        fast_v2_openscholar_base_url="")
    assert settings.synthesis_mode == "legacy"  # constructed without raising


def test_legacy_default_config_builds_without_error():
    """Legacy + default config -> PASS. Settings construction and generator
    resolution must both succeed with nothing configured."""
    settings = _settings_with()
    assert settings.synthesis_mode == "legacy"
    assert settings.fast_v2_generator == "fake"  # untouched default
    gen = build_generator(mode=settings.fast_v2_generator)
    assert isinstance(gen, FakeSynthesisGenerator)


def test_fast_v2_activated_with_default_fake_generator_fails_loud(monkeypatch):
    """Fast v2 + missing real generator -> FAIL LOUD.

    synthesis_mode=fast_v2_experimental with FAST_V2_GENERATOR left at its
    default 'fake' must never silently resolve to a fake generator -- that
    combination almost always means the operator forgot to also configure a
    real backend.
    """
    from src import config as config_module

    settings = _settings_with(synthesis_mode="fast_v2_experimental")
    assert settings.fast_v2_generator == "fake"  # forgotten, not explicitly set
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="FAST_V2_GENERATOR"):
        build_generator()  # mode=None -> resolves from (patched) settings


def test_fast_v2_remote_openscholar_missing_base_url_fails_loud(monkeypatch):
    """Fast v2 + remote_openscholar + missing base_url -> FAIL LOUD."""
    from src import config as config_module

    settings = _settings_with(
        synthesis_mode="fast_v2_experimental",
        fast_v2_generator="remote_openscholar",
        fast_v2_openscholar_base_url="",
    )
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="FAST_V2_OPENSCHOLAR_BASE_URL"):
        build_generator()


def test_fast_v2_valid_remote_openscholar_config_builds_successfully(monkeypatch):
    """Fast v2 + valid remote_openscholar -> PASS."""
    from src import config as config_module
    from src.synthesis.fast_v2.generator.remote_openscholar import RemoteOpenScholarGenerator

    settings = _settings_with(
        synthesis_mode="fast_v2_experimental",
        fast_v2_generator="remote_openscholar",
        fast_v2_openscholar_base_url="http://gpu:8500",
    )
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    gen = build_generator()
    assert isinstance(gen, RemoteOpenScholarGenerator)
    assert gen.base_url == "http://gpu:8500"


def test_fake_generator_still_usable_via_explicit_injection(monkeypatch):
    """FakeGenerator remains usable when a test/dev caller explicitly injects
    it -- even while synthesis_mode=fast_v2_experimental in settings. The
    guardrail only blocks the *silent settings-resolution* path."""
    from src import config as config_module

    settings = _settings_with(synthesis_mode="fast_v2_experimental")
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    # Explicit mode="fake" bypasses the guard entirely -- this must NOT raise.
    gen = build_generator(mode="fake")
    assert isinstance(gen, FakeSynthesisGenerator)


def test_legacy_mode_with_fast_v2_generator_still_fake_does_not_raise(monkeypatch):
    """Legacy stays unaffected by the guard regardless of FAST_V2_GENERATOR --
    Legacy must always start up normally."""
    from src import config as config_module

    settings = _settings_with(synthesis_mode="legacy", fast_v2_generator="fake")
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    gen = build_generator()  # must not raise: fast_v2 is not activated
    assert isinstance(gen, FakeSynthesisGenerator)


def test_constructing_remote_generator_does_not_open_a_connection():
    """Construction alone (no .generate() call) must never touch the network."""
    from src.synthesis.fast_v2.generator.remote_openscholar import RemoteOpenScholarGenerator

    # If this opened a real connection to a non-existent host, it would hang
    # or raise here. It must do neither -- construction is pure.
    gen = RemoteOpenScholarGenerator(base_url="http://this-host-does-not-exist.invalid:9999")
    assert gen.base_url == "http://this-host-does-not-exist.invalid:9999"
