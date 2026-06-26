import os
import sys
import asyncio
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import llm_manager
from utils.advanced_text_analyzer import _is_retryable_llm_provider_error


def _fake_llm(model_name: str, provider: str = "openai"):
    return SimpleNamespace(model_name=model_name, provider=provider)


def test_get_fallback_llm_uses_configured_global_fast():
    original_get_main_llm = llm_manager.get_main_llm
    original_get_fast_llm = llm_manager.get_fast_llm
    try:
        llm_manager.get_main_llm = lambda: _fake_llm("openrouter/main-model")
        llm_manager.get_fast_llm = lambda: _fake_llm("openrouter/fast-model")

        fallback = llm_manager.get_fallback_llm()

        assert fallback is not None
        assert fallback.model_name == "openrouter/fast-model"
    finally:
        llm_manager.get_main_llm = original_get_main_llm
        llm_manager.get_fast_llm = original_get_fast_llm


def test_get_fallback_llm_returns_none_when_no_alternative():
    original_get_main_llm = llm_manager.get_main_llm
    original_get_fast_llm = llm_manager.get_fast_llm
    try:
        shared_llm = _fake_llm("openrouter/shared-model")
        llm_manager.get_main_llm = lambda: shared_llm
        llm_manager.get_fast_llm = lambda: shared_llm

        fallback = llm_manager.get_fallback_llm()

        assert fallback is None
    finally:
        llm_manager.get_main_llm = original_get_main_llm
        llm_manager.get_fast_llm = original_get_fast_llm


def test_retryable_provider_error_excludes_authentication_failures():
    exc = Exception(
        "litellm.AuthenticationError: GeminiException - API key not valid. Please pass a valid API key."
    )

    assert _is_retryable_llm_provider_error(exc) is False


def test_get_configured_fallback_llm_prefers_user_main_for_fast_fail():
    original_get_llm_for_user = llm_manager.get_llm_for_user
    original_get_main_llm = llm_manager.get_main_llm
    original_get_fast_llm = llm_manager.get_fast_llm
    try:
        async def fake_get_llm_for_user(account_id: str, purpose: str = "main"):
            mapping = {
                "fast": _fake_llm("openrouter/user-fast"),
                "main": _fake_llm("openrouter/user-main"),
            }
            return mapping[purpose]

        llm_manager.get_llm_for_user = fake_get_llm_for_user
        llm_manager.get_main_llm = lambda: _fake_llm("openrouter/global-main")
        llm_manager.get_fast_llm = lambda: _fake_llm("openrouter/global-fast")

        fallback = asyncio.run(
            llm_manager.get_configured_fallback_llm(
                account_id="user-1",
                failed_purpose="fast",
            )
        )

        assert fallback is not None
        assert fallback.model_name == "openrouter/user-main"
    finally:
        llm_manager.get_llm_for_user = original_get_llm_for_user
        llm_manager.get_main_llm = original_get_main_llm
        llm_manager.get_fast_llm = original_get_fast_llm
