"""
Centralized LLM Client - Supports multiple providers with automatic fallback.

Provider priority:
1. Azure AI (if configured)
2. Groq (free tier - llama/mixtral models)
3. Anthropic (if credits available)
4. OpenAI-compatible endpoints
5. Rule-based fallback (no API needed)

Configure via config/llm_config.json or environment variables.
"""
import os
import json
import requests
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger("llm_client")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "llm_config.json"

# Default config - users can override via config file or env vars
DEFAULT_CONFIG = {
    "provider": "auto",  # auto, azure, groq, anthropic, openai, local
    # Azure AI
    "azure_api_key": "",
    "azure_endpoint": "",
    "azure_deployment": "gpt-4o",
    "azure_api_version": "2024-02-15-preview",
    # Groq
    "groq_api_key": "",
    "groq_model": "llama-3.3-70b-versatile",
    # Anthropic
    "anthropic_api_key": "",
    "anthropic_model": "claude-sonnet-4-20250514",
    # OpenAI-compatible
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o-mini",
}


def _load_config() -> dict:
    """Load LLM config from file, env vars, or defaults."""
    config = DEFAULT_CONFIG.copy()

    # Load from config file if exists
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                file_config = json.load(f)
            config.update({k: v for k, v in file_config.items() if v})
        except Exception as e:
            logger.warning(f"Failed to load LLM config: {e}")

    # Environment variables override file config
    env_map = {
        "LLM_PROVIDER": "provider",
        "AZURE_API_KEY": "azure_api_key",
        "AZURE_ENDPOINT": "azure_endpoint",
        "AZURE_DEPLOYMENT": "azure_deployment",
        "GROQ_API_KEY": "groq_api_key",
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "OPENAI_API_KEY": "openai_api_key",
        "OPENAI_BASE_URL": "openai_base_url",
    }
    for env_var, config_key in env_map.items():
        val = os.environ.get(env_var)
        if val:
            config[config_key] = val

    return config


def _call_azure(prompt: str, system: str, max_tokens: int, config: dict) -> Optional[str]:
    """Call Azure AI API (supports both Azure OpenAI and Azure AI Services)."""
    api_key = config.get("azure_api_key")
    endpoint = config.get("azure_endpoint", "").rstrip("/")
    
    if not api_key or not endpoint:
        return None

    try:
        deployment = config.get("azure_deployment", "gpt-4o")
        api_version = config.get("azure_api_version", "2024-05-01-preview")
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Try Azure AI Services format (models endpoint) first
        if "/models" in endpoint:
            url = f"{endpoint}/chat/completions?api-version={api_version}"
            body = {
                "model": deployment,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        else:
            # Azure OpenAI format (deployments endpoint)
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            body = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json",
            }

        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.debug("Azure AI API call successful")
            return content
        else:
            error_detail = response.text[:500] if response.text else "No error details"
            logger.error(f"Azure AI API error: {response.status_code} - {error_detail}")
            return None
    except Exception as e:
        logger.error(f"Azure AI API exception: {e}")
        return None


def _call_groq(prompt: str, system: str, max_tokens: int, config: dict) -> Optional[str]:
    """Call Groq API (free tier)."""
    api_key = config.get("groq_api_key")
    if not api_key:
        return None

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.get("groq_model", "llama-3.3-70b-versatile"),
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug("Groq API call successful")
            return content
        else:
            logger.debug(f"Groq API error: {response.status_code}")
            return None
    except Exception as e:
        logger.debug(f"Groq API exception: {e}")
        return None


def _call_anthropic(prompt: str, system: str, max_tokens: int, config: dict) -> Optional[str]:
    """Call Anthropic API."""
    api_key = config.get("anthropic_api_key")
    if not api_key:
        return None

    try:
        body = {
            "model": config.get("anthropic_model", "claude-sonnet-4-20250514"),
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json=body,
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", [{}])[0].get("text", "")
            logger.debug("Anthropic API call successful")
            return content
        else:
            error_detail = response.text[:500] if response.text else "No error details"
            logger.error(f"Anthropic API error: {response.status_code} - {error_detail}")
            return None
    except Exception as e:
        logger.debug(f"Anthropic API exception: {e}")
        return None


def _call_openai_compatible(prompt: str, system: str, max_tokens: int, config: dict) -> Optional[str]:
    """Call OpenAI-compatible API."""
    api_key = config.get("openai_api_key")
    if not api_key:
        return None

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        base_url = config.get("openai_base_url", "https://api.openai.com/v1").rstrip("/")

        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.get("openai_model", "gpt-4o-mini"),
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug("OpenAI-compatible API call successful")
            return content
        else:
            logger.debug(f"OpenAI-compatible API error: {response.status_code}")
            return None
    except Exception as e:
        logger.debug(f"OpenAI-compatible API exception: {e}")
        return None


# Provider dispatch order for "auto" mode
_PROVIDERS = [
    ("azure", _call_azure),
    ("groq", _call_groq),
    ("anthropic", _call_anthropic),
    ("openai", _call_openai_compatible),
]


def call_llm(prompt: str, system: str = None, max_tokens: int = 2000) -> str:
    """
    Call LLM with automatic provider selection and fallback.

    Returns the response text, or empty string if all providers fail.
    The caller should handle empty string as "no LLM available" and use
    rule-based fallback logic.
    """
    config = _load_config()
    provider = config.get("provider", "auto")

    if provider == "local":
        return ""

    if provider == "auto":
        # Try all providers in order
        for name, fn in _PROVIDERS:
            result = fn(prompt, system, max_tokens, config)
            if result:
                logger.info(f"LLM response from {name}")
                return result
        logger.info("All LLM providers unavailable, using local fallback")
        return ""
    else:
        # Try specific provider
        provider_map = {name: fn for name, fn in _PROVIDERS}
        fn = provider_map.get(provider)
        if fn:
            result = fn(prompt, system, max_tokens, config)
            if result:
                return result
        logger.info(f"Provider '{provider}' unavailable, using local fallback")
        return ""


def is_llm_available() -> bool:
    """Quick check if any LLM provider is configured."""
    config = _load_config()
    if config.get("provider") == "local":
        return False
    return bool(
        config.get("azure_api_key")
        or config.get("groq_api_key")
        or config.get("anthropic_api_key")
        or config.get("openai_api_key")
    )
