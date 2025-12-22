#!/usr/bin/env python3
"""
AIN Provider Abstraction Layer
Supports: Anthropic, OpenAI, local models (Ollama)
Automatic failover when primary provider fails
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

# Try loading environment
try:
    from dotenv import load_dotenv
    env_paths = [
        Path.home() / "MAIA-SOVEREIGN" / ".env.local",
        Path.home() / "soullab-workspace" / ".env.local",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            break
except ImportError:
    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> str:
        """Generate text from prompt"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (has credentials, etc)"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def name(self) -> str:
        return "Anthropic Claude"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> str:
        if not self._client:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")

        try:
            message = await self._client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        except Exception as e:
            error_str = str(e)

            # Check for billing/credit errors
            if "credit balance" in error_str.lower() or "billing" in error_str.lower():
                raise ProviderUnavailableError(
                    f"Anthropic: Credit balance too low. Add credits at https://console.anthropic.com/settings/billing"
                )
            # Check for auth errors
            elif "401" in error_str or "authentication" in error_str.lower():
                raise ProviderUnavailableError(f"Anthropic: Invalid API key")
            # Other errors
            else:
                raise ProviderUnavailableError(f"Anthropic: {error_str}")


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def name(self) -> str:
        return "OpenAI GPT-4"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> str:
        if not self._client:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            if "insufficient_quota" in error_str.lower():
                raise ProviderUnavailableError(
                    f"OpenAI: Insufficient quota. Add credits at https://platform.openai.com/account/billing"
                )
            elif "invalid_api_key" in error_str.lower():
                raise ProviderUnavailableError(f"OpenAI: Invalid API key")
            else:
                raise ProviderUnavailableError(f"OpenAI: {error_str}")


class OllamaProvider(LLMProvider):
    """Local Ollama provider"""

    def __init__(self, model: str = "deepseek-r1:latest", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._client = None

    def is_available(self) -> bool:
        # TODO: Check if Ollama is running
        return True

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> str:
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp package not installed. Run: pip install aiohttp")

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": f"{system}\n\n{prompt}" if system else prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }

                async with session.post(f"{self.host}/api/generate", json=payload) as resp:
                    if resp.status != 200:
                        raise ProviderUnavailableError(f"Ollama: HTTP {resp.status}")

                    data = await resp.json()
                    return data.get("response", "")

        except Exception as e:
            raise ProviderUnavailableError(f"Ollama: {str(e)}")


class ProviderUnavailableError(Exception):
    """Raised when a provider cannot fulfill a request"""
    pass


class AINProviderRouter:
    """Routes AIN requests across multiple providers with failover"""

    def __init__(self, preference: Optional[str] = None, fallback_chain: Optional[str] = None):
        """
        Initialize provider router.

        Args:
            preference: Preferred provider ('anthropic', 'openai', 'local', or None for auto)
            fallback_chain: Custom fallback chain as comma-separated string (e.g., 'openai,local,anthropic')
                          Overrides default priority. Can also be set via AIN_FALLBACK_CHAIN env var.
        """
        self.preference = preference or os.environ.get("AIN_PROVIDER", "auto")

        # Initialize all providers
        self.providers = {
            "anthropic": AnthropicProvider(),
            "openai": OpenAIProvider(),
            "local": OllamaProvider(),
        }

        # Configurable priority order via env var or parameter
        fallback_chain = fallback_chain or os.environ.get("AIN_FALLBACK_CHAIN", "")
        if fallback_chain:
            # Parse comma-separated chain (e.g., "openai,local,anthropic")
            custom_priority = [p.strip() for p in fallback_chain.split(",")]
            # Validate all providers exist
            valid_providers = set(self.providers.keys())
            invalid = [p for p in custom_priority if p not in valid_providers]
            if invalid:
                raise ValueError(f"Invalid providers in fallback chain: {invalid}. Valid: {list(valid_providers)}")
            self.priority = custom_priority
        else:
            # Default priority order
            self.priority = ["anthropic", "openai", "local"]

    def get_available_providers(self) -> list:
        """Get list of available providers in priority order"""
        if self.preference != "auto":
            # If specific preference, try it first then fallbacks
            preferred = [self.preference]
            fallbacks = [p for p in self.priority if p != self.preference]
            order = preferred + fallbacks
        else:
            order = self.priority

        return [
            (name, self.providers[name])
            for name in order
            if self.providers[name].is_available()
        ]

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 1.0,
        verbose: bool = False
    ) -> tuple[str, str]:
        """
        Generate text with automatic failover.

        Returns:
            (response_text, provider_name)
        """
        available = self.get_available_providers()

        if not available:
            raise RuntimeError(
                "No LLM providers available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
                "or ensure Ollama is running."
            )

        last_error = None

        for provider_name, provider in available:
            try:
                if verbose:
                    print(f"Trying {provider.name}...")

                response = await provider.generate(
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                if verbose:
                    print(f"✅ Used {provider.name}")

                return (response, provider_name)

            except ProviderUnavailableError as e:
                last_error = e
                if verbose:
                    print(f"⚠️  {provider.name} unavailable: {e}")
                continue

            except Exception as e:
                last_error = e
                if verbose:
                    print(f"❌ {provider.name} error: {e}")
                continue

        # All providers failed
        raise RuntimeError(f"All providers failed. Last error: {last_error}")


# Convenience function
async def get_llm_response(
    prompt: str,
    system: str = "",
    max_tokens: int = 1024,
    temperature: float = 1.0,
    provider: Optional[str] = None,
    fallback_chain: Optional[str] = None,
    verbose: bool = False
) -> tuple[str, str]:
    """
    Get LLM response with automatic provider failover.

    Args:
        prompt: User prompt
        system: System prompt
        max_tokens: Max tokens to generate
        temperature: Sampling temperature
        provider: Preferred provider ('anthropic', 'openai', 'local', or None for auto)
        fallback_chain: Custom fallback chain (e.g., 'openai,local')
        verbose: Print provider routing info

    Returns:
        (response_text, provider_used)
    """
    router = AINProviderRouter(preference=provider, fallback_chain=fallback_chain)
    return await router.generate(
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        verbose=verbose
    )
