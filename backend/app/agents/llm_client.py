"""
LLM client abstraction for the Capability Builder Agent.

One interface, several implementations, selected by LLM_PROVIDER in
Settings. The caller (capability_builder.py, tender_analyzer.py,
decision_engine.py) never needs to know or care which one it's using.

- OpenAIClient (BidOps_Final consolidation): calls the real OpenAI API via
  the `openai` SDK. The operational reference implementation -- the only
  provider with a verified, real, end-to-end Decision Engine run (OpenAI
  Build Week). Mirrors QwenClient's hand-rolled retry loop, since the
  underlying SDK is the same `openai` package.
- QwenClient: Qwen Cloud/DashScope's OpenAI-compatible endpoint via the
  `openai` SDK. Frozen per ADR-001 (99_DECISIONS_LOG.md) -- Alibaba
  Cloud/DashScope is unreachable for new accounts from this deployment's
  region, an external platform restriction, not an engineering defect.
  Kept exactly as implemented and verified in M11/D-140; not deleted,
  not modified.
- GeminiClient (M11.5, Vertex AI migration): the strategic long-term
  provider. Uses Google's native `google-genai` SDK, either in Developer
  API mode (a plain API key, local-dev default) or Vertex AI mode
  (Application Default Credentials, no API key -- see
  99_DECISIONS_LOG.md). Still pending real production verification of the
  Decision Engine specifically; not yet the operational default for that
  reason, not because of any known defect.
- MockLLMClient: sandbox-only stand-in, untouched by any provider work.

Every real client translates every provider-SDK exception it can
encounter into the shared, provider-agnostic types in llm_exceptions.py
before it leaves this module -- callers may catch those types without
ever importing `openai`, `google.genai`, or knowing which vendor is
behind them. Prompt content, extraction/schema validation, and business
logic are untouched by any provider's addition; that separation --
Provider Independence -- is a standing architectural invariant, not a
per-milestone convenience.
"""

import asyncio
import logging
import time
from functools import lru_cache
from typing import Protocol

from app.agents.llm_exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.core.config import get_settings
from app.core.telemetry import record_llm_call

settings = get_settings()
logger = logging.getLogger(__name__)

# Token counts are (input_tokens, output_tokens), either of which may be
# None when a provider doesn't report usage for a given call.
TokenUsage = tuple[int | None, int | None]


@lru_cache
def _get_openai_http_client():
    """
    Shared, process-lifetime AsyncOpenAI client, for the same reason
    _get_qwen_http_client() below is cached: decision_engine.py calls
    get_llm_client() once per requirement, so a per-call client would mean
    a fresh, never-closed HTTP client -- and its own connection pool -- on
    every single capability build, tender analysis chunk, and requirement
    match.

    No base_url override in normal use -- this client talks to OpenAI
    directly. settings.openai_base_url exists only as an escape hatch
    (e.g. pointing at a local proxy in tests) and is None by default.
    """
    from openai import AsyncOpenAI

    kwargs = {
        "api_key": settings.openai_api_key,
        "timeout": settings.openai_timeout_seconds,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return AsyncOpenAI(**kwargs)


@lru_cache
def _get_qwen_http_client():
    """
    Shared, process-lifetime AsyncOpenAI client (M11 fix -- see
    99_DECISIONS_LOG.md D-140).

    AsyncOpenAI wraps httpx.AsyncClient, whose own docstring states it
    "can be shared between tasks" -- it's a pooled resource meant to be
    instantiated once and reused, the same way `get_settings()` below it
    and `engine` in app/core/database.py are already cached/module-level
    singletons in this codebase. Constructing a new client per QwenClient()
    instantiation (the pre-M11-fix behavior) meant a fresh, never-closed
    HTTP client -- and its own connection pool -- on every single
    capability build, tender analysis chunk, and requirement match, since
    decision_engine.py calls get_llm_client() once per requirement. Under
    MockLLMClient this cost nothing; under a real network client it's a
    genuine resource leak. Caching this at module level, via the same
    `@lru_cache` idiom `get_settings()` already uses, means exactly one
    real HTTP client exists per process regardless of how many times
    QwenClient() is instantiated.
    """
    from openai import AsyncOpenAI

    return AsyncOpenAI(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
        timeout=settings.qwen_timeout_seconds,
    )


@lru_cache
def _get_gemini_http_client():
    """
    Shared, process-lifetime google.genai.Client, for the exact same
    reason _get_qwen_http_client() exists: the SDK wraps its own httpx
    client and connection pool, and decision_engine.py calls
    get_llm_client() once per requirement -- so a per-call client would
    mean a fresh, never-closed HTTP client on every single requirement
    match. Caching a single instance at module level, via the same
    `@lru_cache` idiom used for `_get_qwen_http_client()` and
    `get_settings()`, avoids that regardless of how many times
    GeminiClient() is instantiated.

    Construction branches on settings.gemini_auth_mode (Vertex AI
    migration -- see 99_DECISIONS_LOG.md):

    - "developer" (default, local-dev path): Gemini Developer API mode
      (`vertexai=False`, a plain API key from Google AI Studio). Unchanged
      from the original M11.5 implementation.
    - "vertex" (strategic production path): Vertex AI mode (`vertexai=True`,
      project + location). No API key is passed -- authentication comes
      entirely from Application Default Credentials (ADC), resolved by
      the google-auth library from the environment (developer-machine
      impersonated ADC locally, the attached service account identity in
      Cloud Run/Compute Engine in production). No JSON service-account
      key file is used in either environment.

    Both branches share identical HttpOptions/HttpRetryOptions -- the
    google-genai SDK's own retry mechanism is the same SDK code path
    regardless of auth mode; only the credential-acquisition step differs.
    This is why GeminiClient.complete() below only needs *additional*
    exception handling for the auth-acquisition step, not a parallel
    reimplementation of the existing ClientError/ServerError handling.

    Note for tests: since this is `@lru_cache`-d with no arguments, a test
    process that constructs a client under one auth mode and then flips
    settings.gemini_auth_mode must call `_get_gemini_http_client.cache_clear()`
    before constructing again, or it will silently receive the previously
    cached client. The existing `fast_settings` fixture in
    tests/agents/test_llm_client.py already does this before and after
    every test.
    """
    from google import genai
    from google.genai import types

    retry_options = types.HttpRetryOptions(
        attempts=settings.gemini_max_retries + 1,  # SDK's "attempts" includes the initial call
        initial_delay=settings.gemini_retry_backoff_seconds,
        max_delay=settings.gemini_max_retry_delay_seconds,
        exp_base=2,
        # http_status_codes intentionally left at the SDK default (408,
        # 429, 500, 502, 503, 504) -- it already excludes 401/403, so
        # authentication failures are never retried without any extra
        # configuration here.
    )
    http_options = types.HttpOptions(
        timeout=int(settings.gemini_timeout_seconds * 1000),  # SDK expects milliseconds
        retry_options=retry_options,
    )

    if settings.gemini_auth_mode == "vertex":
        return genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            http_options=http_options,
        )

    return genai.Client(
        vertexai=False,
        api_key=settings.gemini_api_key,
        http_options=http_options,
    )


class LLMClient(Protocol):
    async def complete(self, system_prompt: str, user_prompt: str, purpose: str = "unspecified") -> str:
        """Returns the raw text completion for a given system/user prompt pair.

        `purpose` is a free-text tag (e.g. "decision_matching",
        "capability_extraction") recorded against this call in
        LLMCallEvent telemetry -- Phase A instrumentation, see
        docs/CORE_ARCHITECTURE.md. Optional and defaulted so existing
        call sites keep working unchanged; new/updated call sites
        should pass a real value so cost/latency can be broken down by
        pipeline stage later."""
        ...


async def _timed(
    provider: str, model: str, purpose: str, impl,
) -> str:
    """Shared telemetry wrapper: times `impl()` (an async callable returning
    (text, (input_tokens, output_tokens))), records exactly one
    LLMCallEvent regardless of success or failure, and never lets a
    telemetry failure mask or replace the real outcome -- record_llm_call
    itself already swallows its own errors (see app/core/telemetry.py)."""
    start = time.monotonic()
    try:
        text, (input_tokens, output_tokens) = await impl()
    except Exception as exc:
        record_llm_call(
            purpose=purpose, provider=provider, model=model,
            input_tokens=None, output_tokens=None,
            latency_ms=int((time.monotonic() - start) * 1000),
            success=False, error_type=type(exc).__name__,
        )
        raise
    record_llm_call(
        purpose=purpose, provider=provider, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        latency_ms=int((time.monotonic() - start) * 1000),
        success=True,
    )
    return text


class OpenAIClient:
    """
    Real implementation (BidOps_Final consolidation) -- the operational
    reference implementation. Calls the real OpenAI API's chat completions
    endpoint via the `openai` SDK.

    Robustness: a request timeout is set on the underlying SDK client.
    Transient failures -- timeouts, connection errors, and rate limits --
    are retried a bounded number of times with exponential backoff.
    Authentication failures are never retried (a bad key doesn't become
    a good one on attempt two), and malformed-response handling is
    deliberately NOT this module's job -- that's
    json_utils.parse_json_response / schema validation, downstream of
    here.
    """

    def __init__(self) -> None:
        self._client = _get_openai_http_client()

    async def complete(self, system_prompt: str, user_prompt: str, purpose: str = "unspecified") -> str:
        return await _timed(
            "openai", settings.openai_model, purpose,
            lambda: self._complete_impl(system_prompt, user_prompt),
        )

    async def _complete_impl(self, system_prompt: str, user_prompt: str) -> tuple[str, TokenUsage]:
        import openai

        max_attempts = settings.openai_max_retries + 1
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                # No `temperature` override -- GPT-5-series models reject
                # any non-default temperature outright ("Unsupported
                # value: 'temperature' does not support N with this
                # model. Only the default (1) value is supported"),
                # confirmed against real API responses during OpenAI
                # Build Week. Determinism for extraction/matching is
                # achieved structurally (schema-constrained prompts), not
                # via temperature, so omitting it entirely is correct
                # here, not just a workaround.
                response = await self._client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                usage = getattr(response, "usage", None)
                token_usage: TokenUsage = (
                    getattr(usage, "prompt_tokens", None),
                    getattr(usage, "completion_tokens", None),
                )
                return response.choices[0].message.content or "", token_usage

            except openai.AuthenticationError as exc:
                # Never retried -- a bad key doesn't become a good one on
                # attempt two.
                raise LLMAuthenticationError(
                    "OpenAI rejected the provided API key. Check OPENAI_API_KEY."
                ) from exc

            except openai.RateLimitError as exc:
                last_exception = exc
                if attempt == max_attempts:
                    raise LLMRateLimitError(
                        f"OpenAI rate limit exceeded after {attempt} attempt(s)."
                    ) from exc
                await self._backoff(attempt)

            except openai.APITimeoutError as exc:
                last_exception = exc
                if attempt == max_attempts:
                    raise LLMTimeoutError(
                        f"OpenAI did not respond within "
                        f"{settings.openai_timeout_seconds}s after {attempt} attempt(s)."
                    ) from exc
                await self._backoff(attempt)

            except openai.APIConnectionError as exc:
                last_exception = exc
                if attempt == max_attempts:
                    raise LLMConnectionError(
                        f"Could not reach OpenAI after {attempt} attempt(s) "
                        f"(network/DNS/TLS failure)."
                    ) from exc
                await self._backoff(attempt)

            except openai.APIStatusError as exc:
                # Any other non-2xx response (e.g. 5xx, or a 4xx that isn't
                # auth/rate-limiting). Treated as non-retryable -- retrying
                # a request the provider has already rejected is not
                # "reasonable timeout handling."
                raise LLMProviderResponseError(
                    f"OpenAI returned an error response (status {exc.status_code})."
                ) from exc

            except openai.OpenAIError as exc:
                # Catch-all for any other `openai` SDK exception not
                # individually enumerated above -- guarantees every
                # failure the SDK can raise is translated before it
                # leaves this module, per this module's documented
                # guarantee. Not retried: an exception type we don't
                # specifically recognize is not one we can safely assume
                # is transient.
                raise LLMProviderResponseError(
                    f"OpenAI call failed with an unexpected provider error: {exc}"
                ) from exc

        # Unreachable in practice (the loop always returns or raises), but
        # keeps type-checkers honest and avoids an implicit None return.
        raise LLMProviderResponseError(
            f"OpenAI call failed after {max_attempts} attempt(s)."
        ) from last_exception

    async def _backoff(self, attempt: int) -> None:
        """
        Exponential backoff: openai_retry_backoff_seconds * 2^(attempt-1),
        so attempt 1's failure waits one base interval, attempt 2's waits
        two, attempt 3's waits four, etc. Same reasoning as QwenClient's
        _backoff() -- retrying transient failures immediately makes the
        underlying problem worse, not better. Bounded by
        openai_max_retries, so this can never become an infinite loop.
        """
        delay = settings.openai_retry_backoff_seconds * (2 ** (attempt - 1))
        logger.warning(
            "OpenAI call failed on attempt %d, retrying in %.1fs", attempt, delay
        )
        await asyncio.sleep(delay)


class QwenClient:
    """
    Real implementation. Calls Qwen Cloud/DashScope's OpenAI-compatible
    chat completions endpoint via the `openai` SDK pointed at Qwen's
    base_url.

    Robustness (M11): a request timeout is set on the underlying SDK
    client. Transient failures -- timeouts, connection errors, and rate
    limits -- are retried a bounded number of times with exponential
    backoff. Authentication failures are never retried (a bad key
    doesn't become a good one on attempt two), and malformed-response
    handling is deliberately NOT this module's job -- that's
    json_utils.parse_json_response / schema validation, downstream of
    here, and out of scope for M11.
    """

    def __init__(self) -> None:
        self._client = _get_qwen_http_client()

    async def complete(self, system_prompt: str, user_prompt: str, purpose: str = "unspecified") -> str:
        return await _timed(
            "qwen", settings.qwen_model, purpose,
            lambda: self._complete_impl(system_prompt, user_prompt),
        )

    async def _complete_impl(self, system_prompt: str, user_prompt: str) -> tuple[str, TokenUsage]:
        import openai

        max_attempts = settings.qwen_max_retries + 1
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=settings.qwen_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                )
                usage = getattr(response, "usage", None)
                token_usage: TokenUsage = (
                    getattr(usage, "prompt_tokens", None),
                    getattr(usage, "completion_tokens", None),
                )
                return response.choices[0].message.content or "", token_usage

            except openai.AuthenticationError as exc:
                # Never retried -- see class docstring above.
                raise LLMAuthenticationError(
                    "Qwen/DashScope rejected the provided API key. Check QWEN_API_KEY."
                ) from exc

            except openai.RateLimitError as exc:
                last_exception = exc
                if attempt == max_attempts:
                    raise LLMRateLimitError(
                        f"Qwen/DashScope rate limit exceeded after {attempt} attempt(s)."
                    ) from exc
                await self._backoff(attempt)

            except openai.APITimeoutError as exc:
                last_exception = exc
                if attempt == max_attempts:
                    raise LLMTimeoutError(
                        f"Qwen/DashScope did not respond within "
                        f"{settings.qwen_timeout_seconds}s after {attempt} attempt(s)."
                    ) from exc
                await self._backoff(attempt)

            except openai.APIConnectionError as exc:
                last_exception = exc
                if attempt == max_attempts:
                    raise LLMConnectionError(
                        f"Could not reach Qwen/DashScope after {attempt} attempt(s) "
                        f"(network/DNS/TLS failure)."
                    ) from exc
                await self._backoff(attempt)

            except openai.APIStatusError as exc:
                # Any other non-2xx response (e.g. 5xx, or a 4xx that isn't
                # auth/rate-limiting). 5xx is arguably transient, but without
                # a documented DashScope retry contract for arbitrary status
                # codes, treating all of these as non-retryable is the
                # conservative choice -- retrying a request the provider has
                # already rejected is not "reasonable timeout handling."
                raise LLMProviderResponseError(
                    f"Qwen/DashScope returned an error response "
                    f"(status {exc.status_code})."
                ) from exc

            except openai.OpenAIError as exc:
                # Catch-all for any other `openai` SDK exception not
                # individually enumerated above (M11 fix -- see
                # 99_DECISIONS_LOG.md D-140) -- e.g. APIResponseValidationError,
                # raised when the SDK receives a response that fails its own
                # internal shape validation, which is a real risk against a
                # third-party "OpenAI-compatible" endpoint like DashScope
                # rather than OpenAI's own service. OpenAIError is the root
                # of the entire SDK exception hierarchy, so this guarantees
                # every failure the SDK can raise -- not just the specific
                # types anticipated above -- is translated before it leaves
                # this module, per this module's own documented guarantee.
                # Not retried: an exception type we don't specifically
                # recognize is not one we can safely assume is transient.
                raise LLMProviderResponseError(
                    f"Qwen/DashScope call failed with an unexpected provider "
                    f"error: {exc}"
                ) from exc

        # Unreachable in practice (the loop always returns or raises), but
        # keeps type-checkers honest and avoids an implicit None return.
        raise LLMProviderResponseError(
            f"Qwen/DashScope call failed after {max_attempts} attempt(s)."
        ) from last_exception

    async def _backoff(self, attempt: int) -> None:
        """
        Exponential backoff: qwen_retry_backoff_seconds * 2^(attempt-1),
        so attempt 1's failure waits one base interval, attempt 2's waits
        two, attempt 3's waits four, etc. Chosen over fixed-interval
        retry because the failures worth retrying here (rate limits,
        transient network issues, momentary timeouts) are exactly the
        cases where hammering the provider again immediately makes things
        worse, not better -- giving the provider increasing room to
        recover is the standard, documented pattern for this class of
        failure (and is what DashScope/OpenAI-compatible clients expect
        callers to do). Bounded by qwen_max_retries, so this can never
        become an infinite loop.
        """
        delay = settings.qwen_retry_backoff_seconds * (2 ** (attempt - 1))
        logger.warning(
            "Qwen/DashScope call failed on attempt %d, retrying in %.1fs", attempt, delay
        )
        await asyncio.sleep(delay)


class GeminiClient:
    """
    Real implementation (M11.5) -- the strategic long-term provider.
    Calls the Gemini Developer API via Google's native `google-genai`
    SDK, in API-key mode.

    Robustness: unlike `openai`, the `google-genai` SDK has its own
    built-in retry mechanism (tenacity-based, exponential backoff with
    jitter), configured once at client construction in
    _get_gemini_http_client() rather than hand-rolled here -- there is no
    separate retry loop in complete() the way QwenClient/OpenAIClient
    have one, because reimplementing a second retry loop around an SDK
    that already retries internally would risk compounding retries
    rather than adding safety. complete() calls the SDK once; if it
    still raises after the SDK's own retries are exhausted (or
    immediately, for failures the SDK doesn't retry -- e.g.
    authentication), this method's job is purely to translate whatever
    surfaces into the shared provider-agnostic types.

    Exception shape differs genuinely from `openai`'s, not just
    cosmetically: `google-genai` raises exactly two HTTP-status-carrying
    types -- ClientError for any 4xx (401, 403, 404, 429, 400 all raise
    the *same* class, distinguished only by inspecting `.code`) and
    ServerError for any 5xx -- rather than one distinct exception class
    per failure category. Network-level failures (timeout, connection
    refused) surface as raw `httpx` exceptions, not an SDK-specific
    wrapper. There is also no single root exception class analogous to
    `openai.OpenAIError` that covers both the SDK's own errors and the
    underlying httpx-level ones together -- so unlike QwenClient/
    OpenAIClient, this class does not have one all-encompassing final
    `except` clause; it enumerates every failure mode `google-genai` and
    `httpx` are documented to raise for this call path instead. This was
    confirmed by reading the installed SDK's actual errors.py, not
    assumed from similarity to `openai`.

    Vertex AI auth-exception addendum (Vertex AI migration): everything
    above was verified against Developer-API-mode (API-key) failures,
    which surface as the SDK's own ClientError(401/403) once a request
    reaches Google's servers. Vertex AI mode (Application Default
    Credentials) introduces one genuinely new failure surface that
    happens *before* any request reaches the server at all: credential
    acquisition/refresh, raised by the `google-auth` library itself
    (`google.auth.exceptions`), not by `google-genai`. This is the only
    part of the exception surface re-audited for this migration --
    ClientError/ServerError/UnknownApiResponseError/httpx handling below
    is unchanged and was deliberately not re-reviewed, per the approved
    migration scope.
    """

    def __init__(self) -> None:
        self._client = _get_gemini_http_client()

    async def complete(self, system_prompt: str, user_prompt: str, purpose: str = "unspecified") -> str:
        return await _timed(
            "gemini", settings.gemini_model, purpose,
            lambda: self._complete_impl(system_prompt, user_prompt),
        )

    async def _complete_impl(self, system_prompt: str, user_prompt: str) -> tuple[str, TokenUsage]:
        import httpx
        from google.auth import exceptions as google_auth_exceptions
        from google.genai import errors, types

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,
                ),
            )
            usage = getattr(response, "usage_metadata", None)
            token_usage: TokenUsage = (
                getattr(usage, "prompt_token_count", None),
                getattr(usage, "candidates_token_count", None),
            )
            return response.text or "", token_usage

        except google_auth_exceptions.DefaultCredentialsError as exc:
            # Vertex AI mode only: no Application Default Credentials could
            # be found at all (e.g. `gcloud auth application-default login`
            # was never run on this machine, or the attached service account
            # is missing in production). Never retried -- identical policy
            # to the existing ClientError(401/403) case below: a missing
            # credential doesn't become present on retry.
            raise LLMAuthenticationError(
                "No Application Default Credentials found for Vertex AI. Run "
                "'gcloud auth application-default login "
                "--impersonate-service-account=<service-account-email>' "
                "for local development, or verify the attached service "
                "account in production."
            ) from exc

        except google_auth_exceptions.RefreshError as exc:
            # Vertex AI mode only: credentials were found but a token
            # refresh/impersonation call failed -- e.g. the impersonation
            # IAM grant (Service Account Token Creator) was revoked, or the
            # impersonated service account's own role was removed. Never
            # retried, for the same reason as above.
            raise LLMAuthenticationError(
                "Vertex AI credential refresh failed. Check that the "
                "impersonation IAM grant (roles/iam.serviceAccountTokenCreator) "
                "and the service account's own role (roles/aiplatform.user) "
                "are both still in place."
            ) from exc

        except errors.ClientError as exc:
            # Every 4xx raises this one class -- .code carries the real
            # HTTP status, which is what actually distinguishes auth
            # (401/403) from rate-limiting (429) from anything else,
            # since `google-genai` (unlike `openai`) doesn't give each of
            # these its own exception type.
            if exc.code in (401, 403):
                # Never retried -- a bad key doesn't become a good one on
                # retry, and the SDK's own retry mechanism already agrees
                # (401/403 aren't in its default retryable status codes).
                raise LLMAuthenticationError(
                    "Gemini rejected the provided API key. Check GEMINI_API_KEY."
                ) from exc
            if exc.code == 429:
                # Reaching here means the SDK's own internal retries against
                # 429 were already attempted and exhausted.
                raise LLMRateLimitError(
                    "Gemini rate limit exceeded after the SDK's internal retries."
                ) from exc
            raise LLMProviderResponseError(
                f"Gemini returned a client error response (status {exc.code})."
            ) from exc

        except errors.ServerError as exc:
            # Reaching here means the SDK's own internal retries against
            # 5xx were already attempted and exhausted -- a genuine
            # divergence from QwenClient's policy, where 5xx is treated as
            # non-retryable by deliberate choice. Here it's retried, then
            # this is what's left after retrying didn't help.
            raise LLMProviderResponseError(
                f"Gemini returned a server error response (status {exc.code}) "
                f"after retries were exhausted."
            ) from exc

        except errors.UnknownApiResponseError as exc:
            # The SDK received a response it could not parse as JSON at
            # all -- analogous to QwenClient's APIResponseValidationError
            # case: reached the provider, but the response itself is
            # unusable.
            raise LLMProviderResponseError(
                f"Gemini returned a response the SDK could not parse: {exc}"
            ) from exc

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            # Reaching here means the SDK's own internal retries against
            # these were already attempted and exhausted (both are in its
            # default retryable set).
            if isinstance(exc, httpx.TimeoutException):
                raise LLMTimeoutError(
                    f"Gemini did not respond within "
                    f"{settings.gemini_timeout_seconds}s after retries were exhausted."
                ) from exc
            raise LLMConnectionError(
                "Could not reach Gemini after retries were exhausted "
                "(network/DNS/TLS failure)."
            ) from exc

        except errors.APIError as exc:
            # Base class catch-all for anything raised via the SDK's
            # error-construction path not already handled above (e.g. a
            # status code outside both the 4xx and 5xx ranges).
            raise LLMProviderResponseError(
                f"Gemini call failed with an unexpected provider error "
                f"(status {getattr(exc, 'code', 'unknown')}): {exc}"
            ) from exc

        # Deliberately no `except Exception` here (M11.5 QA finding,
        # confirmed by direct inspection of the installed google-genai
        # package, not assumed): unlike `openai.OpenAIError`, there is no
        # common root exception spanning google.genai's own errors and the
        # httpx-level network exceptions handled above. `APIError` is the
        # root only for ClientError/ServerError; UnknownApiResponseError
        # subclasses ValueError, not APIError; httpx's exceptions belong to
        # an entirely separate hierarchy. The only thing that unifies all
        # of these is Python's own bare Exception, which is not a genuine
        # provider-error root -- it would also silently swallow a real bug
        # in this method (e.g. a typo referencing a response attribute
        # that doesn't exist) and mislabel it as a provider failure. Every
        # exception type google-genai and httpx are documented to raise
        # for this call path is enumerated above; anything outside that
        # set is intentionally left to propagate unmodified, so a genuine
        # programming error surfaces as itself rather than being masked as
        # "the provider failed."


class MockLLMClient:
    """
    Sandbox-only stand-in -- never used unless LLM_PROVIDER=mock. Reads
    the actual parsed document text out of the prompt and extracts
    plausible values via simple pattern matching (see mock_extraction.py)
    rather than returning fantasy data, so the surrounding pipeline is
    genuinely exercised against real (if synthetic) test documents.
    """

    async def complete(self, system_prompt: str, user_prompt: str, purpose: str = "unspecified") -> str:
        from app.agents.mock_extraction import generate_mock_response

        async def _impl() -> tuple[str, TokenUsage]:
            return generate_mock_response(system_prompt, user_prompt), (None, None)

        return await _timed("mock", "mock", purpose, _impl)


def get_llm_client(provider: str | None = None) -> LLMClient:
    """`provider` lets a caller override the process-wide LLM_PROVIDER
    setting for a single call (e.g. a user-selected "Analysis Engine" on
    a specific tender run) without touching global config. None (the
    default) preserves the original behavior exactly: fall back to
    settings.llm_provider. The API layer is responsible for restricting
    which provider values it actually lets a request choose (see
    ExecuteMissionRequest in missions.py) -- this factory itself accepts
    any of the three real providers, same as it always has via settings."""
    resolved = provider or settings.llm_provider
    if resolved == "openai":
        return OpenAIClient()
    if resolved == "qwen":
        return QwenClient()
    if resolved == "gemini":
        return GeminiClient()
    return MockLLMClient()
