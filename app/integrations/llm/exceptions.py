class LLMProviderError(Exception):
    """Expected failure while obtaining an optional LLM analysis."""


class LLMDisabledError(LLMProviderError):
    """Raised when analysis is requested while LLM support is disabled."""


class LLMConfigurationError(LLMProviderError):
    """Raised when an enabled provider lacks required configuration."""


class LLMUnavailableError(LLMProviderError):
    """Raised after transient provider failures exceed the retry budget."""


class LLMHTTPError(LLMUnavailableError):
    """Sanitized HTTP error returned by an LLM provider."""

    def __init__(
        self,
        *,
        status: int,
        error_type: str | None = None,
        code: str | None = None,
        param: str | None = None,
        message: str | None = None,
    ) -> None:
        self.status = status
        self.error_type = error_type
        self.code = code
        self.param = param
        self.message = message
        details = ", ".join(
            f"{key}: {value}"
            for key, value in {
                "type": error_type,
                "code": code,
                "param": param,
                "message": message,
            }.items()
            if value is not None
        )
        super().__init__(f"LLM provider returned HTTP {status}" + (f" ({details})" if details else "."))


class LLMInvalidResponseError(LLMProviderError):
    """Raised when a provider response cannot become a valid analysis."""
