"""
Settings page for managing AI provider API keys and configuration.
"""
import streamlit as st
from pathlib import Path
from collections import OrderedDict

from src.config import ENV_PATH
from src.utils.logging import logger

PROVIDER_MODELS = {
    "openai": [
        ("gpt-4o", "Most capable OpenAI model — best accuracy, higher cost"),
        ("gpt-4o-mini", "Compact and fast — good balance of cost and quality"),
        ("gpt-4.1", "Latest GPT-4.1 — strong coding and instruction following"),
        ("gpt-4.1-mini", "Smaller GPT-4.1 — fast and affordable"),
        ("gpt-4.1-nano", "Smallest GPT-4.1 — lowest cost, fastest responses"),
        ("o3-mini", "Reasoning model — best for complex analytical tasks"),
    ],
    "anthropic": [
        ("claude-sonnet-4-6", "Latest Sonnet — best balance of speed and intelligence"),
        ("claude-opus-4-8", "Most capable Claude — highest accuracy, slower"),
        ("claude-haiku-4-5-20251001", "Fastest Claude — lowest cost, good for simple tasks"),
    ],
    "ollama": [
        ("llama3.1", "Meta Llama 3.1 — strong general-purpose open model"),
        ("llama3.2", "Meta Llama 3.2 — newer, improved reasoning"),
        ("mistral", "Mistral 7B — fast and efficient for structured tasks"),
        ("codellama", "Code Llama — optimized for code and structured data"),
        ("gemma2", "Google Gemma 2 — compact and capable"),
        ("phi3", "Microsoft Phi-3 — small model, strong reasoning"),
        ("deepseek-r1", "DeepSeek-R1 — strong reasoning and analysis"),
    ],
}

PROVIDER_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
    "ollama": "llama3.1",
}


def _read_env() -> OrderedDict:
    """Read .env file into an ordered dict, preserving comments and blank lines."""
    entries = OrderedDict()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                entries[key.strip()] = value.strip()
    return entries


def _write_env(entries: OrderedDict):
    """Write dict back to .env file."""
    lines = [f"{k}={v}" for k, v in entries.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "*" * len(key) if key else ""
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def render_settings_page():
    """Render the AI provider settings page."""
    st.header("Settings")

    env = _read_env()

    # --- AI Provider selector ---
    st.subheader("AI Provider")

    providers = ["openai", "anthropic", "ollama"]
    current_provider = env.get("AI_PROVIDER", "openai")
    if current_provider not in providers:
        current_provider = "openai"

    provider = st.radio(
        "Active AI Provider",
        providers,
        index=providers.index(current_provider),
        format_func=lambda p: {"openai": "OpenAI", "anthropic": "Claude (Anthropic)", "ollama": "Ollama (Local)"}[p],
        horizontal=True,
    )

    st.divider()

    # --- Provider-specific settings ---
    tab_openai, tab_anthropic, tab_ollama = st.tabs(["OpenAI", "Claude (Anthropic)", "Ollama"])

    with tab_openai:
        _render_openai_tab(env)

    with tab_anthropic:
        _render_anthropic_tab(env)

    with tab_ollama:
        _render_ollama_tab(env)

    st.divider()

    # --- Model selection ---
    st.subheader("Model Selection")

    models = PROVIDER_MODELS.get(provider, [])
    model_ids = [m[0] for m in models]
    model_descriptions = {m[0]: m[1] for m in models}

    default_model = PROVIDER_DEFAULTS.get(provider, "gpt-4o-mini")
    current_model = env.get("AI_MODEL", default_model)

    # If the saved model doesn't belong to the selected provider, use the provider's default
    if current_model not in model_ids:
        current_model = default_model

    selected_index = model_ids.index(current_model) if current_model in model_ids else 0

    ai_model = st.selectbox(
        "Model",
        options=model_ids,
        index=selected_index,
        format_func=lambda m: f"{m}  —  {model_descriptions.get(m, '')}",
    )

    if ai_model and ai_model in model_descriptions:
        st.caption(model_descriptions[ai_model])

    ai_timeout = st.number_input(
        "Request Timeout (seconds)",
        min_value=5,
        max_value=300,
        value=int(env.get("AI_TIMEOUT", "30")),
    )

    st.divider()

    # --- Save button ---
    if st.button("Save Settings", type="primary", use_container_width=True):
        env["AI_PROVIDER"] = provider
        env["AI_MODEL"] = ai_model
        env["AI_TIMEOUT"] = str(int(ai_timeout))
        _write_env(env)

        from src.config import reload_env
        reload_env()

        logger.info(f"Settings saved: provider={provider}, model={ai_model}")
        st.success("Settings saved. Changes take effect on the next analysis run.")
        st.rerun()


def _render_openai_tab(env: OrderedDict):
    existing = env.get("OPENAI_API_KEY", "")
    if existing:
        st.success(f"API key configured: {_mask_key(existing)}")
    else:
        st.warning("No API key configured")

    with st.form("openai_form"):
        new_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Leave blank to keep the existing key",
        )
        if st.form_submit_button("Update OpenAI Key"):
            if new_key:
                env["OPENAI_API_KEY"] = new_key
                _write_env(env)
                from src.config import reload_env
                reload_env()
                logger.info("OpenAI API key updated")
                st.success("OpenAI API key saved.")
                st.rerun()
            else:
                st.info("No change — key field was empty.")


def _render_anthropic_tab(env: OrderedDict):
    existing = env.get("ANTHROPIC_API_KEY", "")
    if existing:
        st.success(f"API key configured: {_mask_key(existing)}")
    else:
        st.warning("No API key configured")

    with st.form("anthropic_form"):
        new_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Leave blank to keep the existing key",
        )
        if st.form_submit_button("Update Anthropic Key"):
            if new_key:
                env["ANTHROPIC_API_KEY"] = new_key
                _write_env(env)
                from src.config import reload_env
                reload_env()
                logger.info("Anthropic API key updated")
                st.success("Anthropic API key saved.")
                st.rerun()
            else:
                st.info("No change — key field was empty.")


def _render_ollama_tab(env: OrderedDict):
    st.info("Ollama runs locally and does not require an API key.")

    with st.form("ollama_form"):
        base_url = st.text_input(
            "Ollama Base URL",
            value=env.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            help="URL where your Ollama instance is running",
        )

        ollama_models = PROVIDER_MODELS["ollama"]
        ollama_ids = [m[0] for m in ollama_models]
        ollama_descs = {m[0]: m[1] for m in ollama_models}
        current_ollama = env.get("OLLAMA_MODEL", "llama3.1")
        if current_ollama not in ollama_ids:
            ollama_ids.append(current_ollama)
            ollama_descs[current_ollama] = "Custom model"
        idx = ollama_ids.index(current_ollama) if current_ollama in ollama_ids else 0

        model = st.selectbox(
            "Ollama Model",
            options=ollama_ids,
            index=idx,
            format_func=lambda m: f"{m}  —  {ollama_descs.get(m, '')}",
            help="Select a model or set OLLAMA_MODEL in .env for unlisted models",
        )

        if st.form_submit_button("Update Ollama Settings"):
            env["OLLAMA_BASE_URL"] = base_url
            env["OLLAMA_MODEL"] = model
            _write_env(env)
            from src.config import reload_env
            reload_env()
            logger.info(f"Ollama settings updated: url={base_url}, model={model}")
            st.success("Ollama settings saved.")
            st.rerun()
