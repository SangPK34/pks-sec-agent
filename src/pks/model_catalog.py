"""Curated model catalog for OpenAI-compatible endpoints."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


def _context_tokens(value: str) -> int | None:
    normalized = value.rstrip("+").upper()
    if normalized == "—":
        return None
    if normalized.endswith("M"):
        return int(float(normalized[:-1]) * 1_000_000)
    if normalized.endswith("K"):
        return int(float(normalized[:-1]) * 1_000)
    return int(normalized)


@dataclass(frozen=True, slots=True)
class CatalogModel:
    model_id: str
    name: str
    provider: str
    context: str
    efforts: tuple[str, ...]
    best_for: str

    @property
    def context_tokens(self) -> int | None:
        return _context_tokens(self.context)


MODELS = tuple(
    CatalogModel(*row)
    for row in (
        ("openai/CAI", "CAI (local DeepSeek)", "Local Gateway", "1M", ("high", "max"), "local CTF agent"),
        ("deepseek/deepseek-v4-pro", "DeepSeek V4 Pro", "Open Source", "1M", ("high", "max"), "long-context reasoning"),
        ("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash", "Open Source", "1M", ("high", "max"), "fast reasoning"),
        ("moonshotai/Kimi-K3", "Kimi K3", "Open Source", "1M", (), "long-horizon coding"),
        ("moonshotai/Kimi-K2.7-Code", "Kimi K2.7 Code", "Open Source", "256K", (), "coding with vision"),
        ("moonshotai/Kimi-K2.7-Code-Highspeed", "Kimi K2.7 Code HighSpeed", "Open Source", "262K", (), "high-speed coding with vision"),
        ("moonshotai/Kimi-K2.6", "Kimi K2.6", "Open Source", "256K", (), "long-horizon coding with vision"),
        ("moonshotai/Kimi-K2.5", "Kimi K2.5", "Open Source", "256K", (), "multimodal frontend coding"),
        ("zai-org/GLM-5.2", "GLM-5.2", "Open Source", "1M", ("high", "max"), "long-horizon coding"),
        ("zai-org/GLM-5.2-Fast", "GLM-5.2 Fast", "Open Source", "1M", (), "high-throughput coding"),
        ("zai-org/GLM-5.1", "GLM-5.1", "Open Source", "—", (), "autonomous coding"),
        ("zai-org/GLM-5", "GLM-5", "Open Source", "200K", (), "planning"),
        ("MiniMaxAI/MiniMax-M3", "MiniMax M3", "Open Source", "1M", (), "coding and agents"),
        ("MiniMaxAI/MiniMax-M2.7", "MiniMax M2.7", "Open Source", "—", (), "software engineering"),
        ("MiniMaxAI/MiniMax-M2.5", "MiniMax M2.5", "Open Source", "200K", (), "full-stack coding"),
        ("xiaomi/mimo-v2.5-pro", "MiMo V2.5 Pro", "Open Source", "1M", (), "long-context agentic coding"),
        ("xiaomi/mimo-v2.5", "MiMo V2.5", "Open Source", "1M", (), "efficient agentic coding"),
        ("Qwen/Qwen3.6-Max-Preview", "Qwen 3.6 Max Preview", "Open Source", "—", (), "agent execution"),
        ("Qwen/Qwen3.6-Plus", "Qwen 3.6 Plus", "Open Source", "—", (), "coding and reasoning"),
        ("Qwen/Qwen3.7-Max", "Qwen 3.7 Max", "Open Source", "1M", (), "frontier coding"),
        ("Qwen/Qwen3.7-Plus", "Qwen 3.7 Plus", "Open Source", "1M", (), "agentic coding"),
        ("stepfun/Step-3.7-Flash", "Step 3.7 Flash", "Open Source", "256K", (), "multimodal reasoning"),
        ("stepfun/Step-3.5-Flash", "Step 3.5 Flash", "Open Source", "1M", (), "fast agentic reasoning"),
        ("tencent/hy3-paid", "Tencent Hy3", "Open Source", "262K", (), "agentic tool use"),
        ("nvidia/nemotron-3-ultra-550b-a55b", "Nemotron 3 Ultra", "Open Source", "1M", (), "autonomous agents"),
        ("thinkingmachines/inkling", "Inkling", "Open Source", "256K", (), "multimodal reasoning"),
        ("poolside/laguna-s-2.1-free", "Laguna S 2.1", "Open Source", "256K", (), "agentic coding"),
        ("inclusionai/ling-3.0-flash-free", "Ling 3.0 Flash", "Open Source", "256K", (), "fast coding"),
        ("claude-sonnet-5", "Claude Sonnet 5", "Anthropic", "1M", ("low", "medium", "high", "xhigh", "max"), "fast frontier work"),
        ("claude-sonnet-4-6", "Claude Sonnet 4.6", "Anthropic", "1M", ("low", "medium", "high", "xhigh", "max"), "coding and agents"),
        ("claude-fable-5", "Claude Fable 5", "Anthropic", "1M", ("low", "medium", "high", "xhigh", "max"), "demanding reasoning"),
        ("claude-opus-5", "Claude Opus 5", "Anthropic", "1M", ("low", "medium", "high", "xhigh", "max"), "complex agents"),
        ("claude-opus-4-8", "Claude Opus 4.8", "Anthropic", "1M", ("low", "medium", "high", "xhigh", "max"), "complex agents"),
        ("claude-opus-4-7", "Claude Opus 4.7", "Anthropic", "1M", ("low", "medium", "high", "xhigh", "max"), "complex agents"),
        ("claude-haiku-4-5-20251001", "Claude Haiku 4.5", "Anthropic", "200K", (), "fast tasks"),
        ("gpt-5.6-sol", "GPT-5.6 Sol", "OpenAI", "1.05M", ("low", "medium", "high", "xhigh", "max"), "complex professional work"),
        ("gpt-5.6-terra", "GPT-5.6 Terra", "OpenAI", "1.05M", ("low", "medium", "high", "xhigh", "max"), "balanced frontier work"),
        ("gpt-5.6-luna", "GPT-5.6 Luna", "OpenAI", "1.05M", ("low", "medium", "high", "xhigh", "max"), "fast general work"),
        ("gpt-5.5", "GPT-5.5", "OpenAI", "—", ("low", "medium", "high", "xhigh"), "complex general work"),
        ("gpt-5.4", "GPT-5.4", "OpenAI", "400K", ("low", "medium", "high", "xhigh"), "general complex work"),
        ("gpt-5.3-codex", "GPT-5.3 Codex", "OpenAI", "400K", ("low", "medium", "high", "xhigh"), "coding"),
        ("gpt-5.4-mini", "GPT-5.4 Mini", "OpenAI", "400K", ("low", "medium", "high"), "fast everyday work"),
        ("google/gemini-3.6-flash", "Gemini 3.6 Flash", "Google", "1M", ("low", "medium", "high"), "coding and agents"),
        ("google/gemini-3.5-flash", "Gemini 3.5 Flash", "Google", "1M", ("low", "medium", "high"), "parallel agent work"),
        ("google/gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite", "Google", "1M", ("low", "medium", "high"), "subagents"),
        ("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite", "Google", "1M", ("low", "medium", "high"), "high-volume work"),
        ("sakana/fugu-ultra", "Fugu Ultra", "Sakana", "1M", ("high", "xhigh"), "multi-agent orchestration"),
        ("meta/muse-spark-1.1", "Muse Spark 1.1", "Meta", "1.05M", (), "tool and computer use"),
        ("xai/grok-4.5", "Grok 4.5", "xAI", "500K", ("low", "medium", "high"), "coding and agents"),
    )
)


def models_by_provider() -> dict[str, tuple[CatalogModel, ...]]:
    grouped: dict[str, list[CatalogModel]] = defaultdict(list)
    for model in MODELS:
        grouped[model.provider].append(model)
    return {provider: tuple(models) for provider, models in grouped.items()}


def find_model(model_name: str) -> CatalogModel | None:
    needle = model_name.lower()
    return next((model for model in MODELS if model.model_id.lower() == needle), None)


def api_model_id(model_name: str) -> str:
    """Return the endpoint-facing ID while preserving user-facing model aliases."""
    if model_name.lower() == "openai/cai":
        return "CAI"
    return model_name


def context_window_for_model(model_name: str) -> int | None:
    model = find_model(model_name)
    return model.context_tokens if model else None
