from .openai import OpenAIProvider


class LocalProvider(OpenAIProvider):
    """OpenAI-compatible local backend; transport is identical, ownership differs."""
