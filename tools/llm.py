"""
LLM factory — returns the right LangChain chat model based on model name prefix.

Supported providers (detected automatically from the model string):
  claude-*          → Anthropic   (ChatAnthropic)
  gpt-*, o1-*, o3-*, o4-*  → OpenAI      (ChatOpenAI)
  gemini-*          → Google      (ChatGoogleGenerativeAI)

Usage:
    from tools.llm import make_llm

    llm = make_llm("claude-opus-4-6", max_tokens=8_000)
    llm = make_llm("gpt-4o", max_tokens=4_000)
    llm = make_llm("gemini-2.0-flash")
"""
from __future__ import annotations

from config import ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY

_OPENAI_PREFIXES = ("gpt-", "o1-", "o3-", "o4-")


def make_llm(model: str, **kwargs):
    """
    Return a LangChain chat model for the given model string.

    Extra keyword arguments (e.g. max_tokens, temperature) are passed through
    to the underlying provider client so callers never need to import
    provider-specific classes directly.

    Raises ValueError for unrecognised model prefixes.
    """
    if model.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=ANTHROPIC_API_KEY, **kwargs)

    if model.startswith(_OPENAI_PREFIXES):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=OPENAI_API_KEY, **kwargs)

    if model.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=GOOGLE_API_KEY, **kwargs)

    raise ValueError(
        f"Cannot determine provider for model {model!r}. "
        "Expected prefix: claude-, gpt-, o1-, o3-, o4-, or gemini-."
    )
