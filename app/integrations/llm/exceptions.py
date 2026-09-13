class LLMProviderError(Exception):
    """Expected failure while obtaining an optional LLM analysis."""


class LLMDisabledError(LLMProviderError):
    """Raised when analysis is requested while LLM support is disabled."""


class LLMConfigurationError(LLMProviderError):
    """Raised when an enabled provider lacks required configuration."""


class LLMUnavailableError(LLMProviderError):
    """Raised after transient provider failures exceed the retry budget."""


class LLMInvalidResponseError(LLMProviderError):
    """Raised when a provider response cannot become a valid analysis."""
