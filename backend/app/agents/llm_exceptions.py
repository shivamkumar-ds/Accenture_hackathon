"""
Provider-agnostic LLM exception surface (M11).

Per the Constitution's Provider Independence principle, nothing outside
app/agents/llm_client.py may depend on a specific provider's SDK or
exception hierarchy (e.g. the `openai` package's exception types, which
are an artifact of calling Qwen/DashScope through its OpenAI-compatible
endpoint -- not a BidOps concept). QwenClient translates every failure
it can encounter into one of these before it leaves the provider layer.
Callers (capability_builder.py, tender_analyzer.py, decision_engine.py)
may catch LLMProviderError (or a specific subclass) without ever
importing `openai` or knowing DashScope exists.

Subclasses split failures along the one axis that actually matters to
a caller: is this worth retrying, or not. QwenClient itself already
retries transient failures internally (bounded, see llm_client.py) --
these exception types are what's left after retries are exhausted, or
raised immediately for failures that are never worth retrying.
"""


class LLMProviderError(Exception):
    """Base class for all provider-layer failures. Catch this for a blanket handler."""


class LLMAuthenticationError(LLMProviderError):
    """Invalid or missing API credentials. Never retried -- retrying won't fix a bad key."""


class LLMTimeoutError(LLMProviderError):
    """The provider did not respond within the configured timeout, even after retries."""


class LLMConnectionError(LLMProviderError):
    """Network-level failure reaching the provider (DNS, TCP, TLS), even after retries."""


class LLMRateLimitError(LLMProviderError):
    """The provider rejected the request for rate-limiting reasons, even after retries."""


class LLMProviderResponseError(LLMProviderError):
    """
    The provider was reached and responded, but the response itself indicates
    a provider-side failure BidOps can't recover from (e.g. a 4xx that isn't
    auth or rate-limiting, a 5xx after retries are exhausted, an
    unexpected/empty response shape at the transport level, or any other
    `openai` SDK exception not individually recognized -- e.g.
    APIResponseValidationError, raised when the SDK's own response-shape
    validation fails, which is a real risk against a third-party
    "OpenAI-compatible" endpoint like DashScope. This is the catch-all
    provider-layer failure type: reached the provider, something about the
    interaction still failed, and it isn't worth retrying blindly.

    Note: this is distinct from a malformed *extraction* JSON payload -- that
    failure happens downstream, in json_utils.parse_json_response /
    Pydantic schema validation, and is explicitly out of scope for M11 (it's
    prompt/extraction-quality territory, i.e. M12).
    """
