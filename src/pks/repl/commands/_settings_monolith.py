"""REPL ``/settings`` command: questionary UI for ``.env``, FAQ, validation, and language."""

# Standard library imports
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Third party imports
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.markdown import Markdown

# Local imports
from pks.agents import get_available_agents
from pks.repl.commands.base import Command, register_command
from pks.repl.commands.env_catalog import ENV_VARS
from pks.repl.commands.model import load_all_available_models
from pks.repl.ui.banner import _PKS_GREEN as _PKS_ACCENT

# Import i18n (required for /settings UI); validation is optional
try:
    from pks.repl.commands.settings_i18n import (
        get_string,
        get_faq,
        get_available_languages,
        SUPPORTED_LANGUAGES,
        DEFAULT_LANGUAGE,
        FAQ_CONTENT,
    )
except ImportError:  # pragma: no cover — defensive

    def get_string(key: str, lang: str = "en") -> str:  # type: ignore[misc]
        return key

    def get_faq(*_a, **_k):  # type: ignore[misc]
        return {}

    def get_available_languages():  # type: ignore[misc]
        return {"en": "English"}

    SUPPORTED_LANGUAGES = {"en": "English"}
    DEFAULT_LANGUAGE = "en"
    FAQ_CONTENT = {}

try:
    from pks.repl.commands.settings_validation import (
        validate_openai_key,
        validate_anthropic_key,
        validate_openrouter_key,
        validate_google_key,
        check_ollama_running,
        list_ollama_models,
        check_network_connectivity,
        validate_all_api_keys,
        get_configuration_status,
        ValidationStatus,
    )

    HAS_VALIDATION = True
except ImportError:
    HAS_VALIDATION = False

console = Console()

# Minimal ASCII prefixes for /settings (no emoji)
ICON_CAT = "[>] "
ICON_FAQ = "[?] "
ICON_LANG = "[*] "
ICON_ADD = "[+] "
ICON_TOPIC = "[-] "

# Distinct accent for Ollama FAQ sections (cyan vs CLI green accent)
_OLLAMA_FAQ_STYLE = "cyan"


# Current language setting (can be changed at runtime)
_current_language = os.getenv('PKS_SETTINGS_LANGUAGE', DEFAULT_LANGUAGE)

# Comprehensive list of ALL variables organized by category
SETTINGS_VARIABLES = {
    # =====================
    # CTF & Challenge Settings
    # =====================
    'CTF Variables': [
        'CTF_NAME',
        'CTF_CHALLENGE',
        'CTF_IP',
        'CTF_SUBNET',
        'CTF_INSIDE',
        'CTF_MODEL',
        'CTF_CONTAINER_NAME',
        'CTF_INSTANCE_ID',
    ],

    # =====================
    # Core Agent & Model Settings
    # =====================
    'Core PKS Settings': [
        'PKS_MODEL',
        'PKS_AGENT_TYPE',
        'PKS_TEMPERATURE',
        'PKS_TOP_P',
        'PKS_DEBUG',
        'PKS_BRIEF',
        'PKS_STATE',
    ],

    # =====================
    # API Keys (dynamically populated)
    # =====================
    'API Keys': [
        'ALIAS_API_KEY',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'GOOGLE_API_KEY',
        'OPENROUTER_API_KEY',
        'OLLAMA_API_KEY',
    ],

    # =====================
    # Streaming & Output Control
    # =====================
    'Streaming & Output': [
        'PKS_STREAM',
        'PKS_TOOL_STREAM',
        'PKS_SHOW_CACHE',
        'PKS_COMPACT_REPL',
        'PKS_DEBUG_TOOLS_VIZ',
        'PKS_DEBUG_STREAMING',
    ],

    # =====================
    # Parallelization & Execution
    # =====================
    'Parallelization': [
        'PKS_PARALLEL',
        'PKS_PARALLEL_AGENTS',
        'PKS_PARALLEL_EXTERNAL_TIMEOUT',
        'PKS_MERGE_SUMMARIZE_PER_WORKER',
        'PKS_MERGE_SUMMARIZE_MIN_MESSAGES',
        'PKS_AUTO_RUN_PARALLEL',
        'PKS_AUTO_RUN_QUEUE',
        'PKS_QUEUE_FILE',
    ],

    # =====================
    # Execution Limits
    # =====================
    'Execution Limits': [
        'PKS_MAX_TURNS',
        'PKS_MAX_INTERACTIONS',
        'PKS_PRICE_LIMIT',
        'PKS_TOOL_TIMEOUT',
        'PKS_IDLE_TIMEOUT',
        'PKS_CODE_TIMEOUT',
    ],

    # =====================
    # Compacted memory & context
    # =====================
    'Memory & Context': [
        'PKS_COMPACTED_MEMORY',
        'PKS_ENV_CONTEXT',
        'PKS_CTX_TRUNC',
        'PKS_DISPLAY_MAX_OUTPUT',
    ],

    # =====================
    # Workspace
    # =====================
    'Workspace': [
        'PKS_WORKSPACE',
        'PKS_WORKSPACE_DIR',
        'PKS_ACTIVE_CONTAINER',
        'PKS_ACTIVE_CONTAINER_DEFAULT',
    ],

    # =====================
    # Support & Meta Agent
    # =====================
    'Support Agent': [
        'PKS_SUPPORT_MODEL',
        'PKS_SUPPORT_INTERVAL',
        'PKS_META_AGENT',
        'PKS_META_MODEL',
        'PKS_META_AUTOCLOSE_GRACE',
    ],

    # =====================
    # CTR (Cut The Rope)
    # =====================
    'CTR Settings': [
        'PKS_CTR_DIGEST_MODE',
        'PKS_CTR_DIGEST_MODEL',
        'PKS_CTR_OUTPUT_DIR',
        'PKS_CTR_DEFAULT_OUTPUT_DIR',
        'PKS_CTR_DEFAULT_RUN',
        'PKS_CTR_IS_CTF',
        'PKS_CTR_DISTANCE_HEURISTIC',
        'PKS_GCTR_NITERATIONS',
    ],

    # =====================
    # Tracing & Telemetry
    # =====================
    'Tracing & Telemetry': [
        'PKS_TRACING',
        'PKS_TELEMETRY',
        'PKS_DISABLE_SESSION_RECORDING',
        'PKS_DISABLE_USAGE_TRACKING',
    ],

    # =====================
    # Security & Guardrails
    # =====================
    'Security': [
        'PKS_GUARDRAILS',
        'PKS_PLAN',
    ],

    # =====================
    # Pricing & Cost Control
    # =====================
    'Pricing': [
        'PKS_COST_DISPLAYED',
        'PKS_ENABLE_PRICING_FETCH',
        'PKS_DEBUG_PRICING',
        'PKS_PRICING_FILE',
        'PKS_PRICINGS_DIR',
    ],

    # =====================
    # Reporting
    # =====================
    'Reporting': [
        'PKS_REPORT',
        'PKS_CONTINUATION_FALLBACK_MODEL',
    ],

    # =====================
    # API Server
    # =====================
    'API Server': [
        'PKS_API_HOST',
        'PKS_API_PORT',
        'PKS_API_CORS',
        'PKS_API_KEY_HEADER',
        'PKS_API_LOG_AUTH',
        'PKS_API_LOG_REQUESTS',
        'PKS_API_LOG_LEVEL',
        'PKS_API_RELOAD',
        'PKS_API_WORKERS',
    ],

    # =====================
    # Authentication
    # =====================
    'Authentication': [
        'PKS_AUTH_BASE_URL',
        'PKS_AUTH_DEVICE_PORT',
        'PKS_AUTH_PUBLIC_HOST',
        'PKS_AUTH_PUBLIC_PORT',
        'PKS_AUTH_SESSION_TTL_SECONDS',
    ],

    # =====================
    # MCP (Model Context Protocol)
    # =====================
    'MCP Settings': [
        'PKS_MCP_TOKEN',
        'PKS_MCP_AUTH_TOKEN',
        'PKS_MCP_SSE_TIMEOUT',
        'PKS_MCP_SSE_READ_TIMEOUT',
    ],

    # =====================
    # OpenRouter Provider Settings
    # =====================
    'OpenRouter': [
        'OPENROUTER_API_KEY',
        'OPENROUTER_API_BASE',
        'OPENROUTER_PROVIDER',
        'OPENROUTER_PROVIDER_ONLY',
        'OPENROUTER_PROVIDER_IGNORE',
        'OPENROUTER_ALLOW_FALLBACKS',
        'OPENROUTER_QUANTIZATION',
    ],

    # =====================
    # Ollama Settings
    # =====================
    'Ollama': [
        'OLLAMA',
        'OLLAMA_API_KEY',
        'OLLAMA_API_BASE',
    ],

    # =====================
    # LiteLLM Settings
    # =====================
    'LiteLLM': [
        'LITELLM_API_KEY',
        'LITELLM_BASE_URL',
    ],

    # =====================
    # OpenAI Direct Settings
    # =====================
    'OpenAI': [
        'OPENAI_API_KEY',
        'OPENAI_API_BASE',
        'CSI_CUSTOM_ENDPOINT',
        'ALIAS_API_URL',
        'OPENAI_BASE_URL',
        'OPENAI_ORG_ID',
        'OPENAI_PROJECT_ID',
    ],

    # =====================
    # Google Settings
    # =====================
    'Google': [
        'GOOGLE_API_KEY',
        'GOOGLE_SEARCH_API_KEY',
        'GOOGLE_SEARCH_CX',
    ],

    # =====================
    # TUI Mode Settings
    # =====================
    'TUI Mode': [
        'PKS_TUI_MODE',
        'PKS_TUI_STARTUP_YAML',
        'PKS_TUI_SHARED_PROMPT',
        'PKS_TUI_MAX_LINES',
        'PKS_TUI_MAX_RERENDERS_PER_SEC',
    ],

    # =====================
    # Advanced/Internal
    # =====================
    'Advanced': [
        'PKS_VERSION',
        'PKS_THEME',
        'PKS_SKIP_NETWORK_CHECK',
        'PKS_AUTO_COMPACT',
        'PKS_AUTO_COMPACT_THRESHOLD',
        'PKS_WARN_UNATTRIBUTED',
        'PKS_UNATTRIBUTED_LOG',
        'PKS_PATTERN_DESCRIPTION',
        'PKS_DEFAULT_AGENT',
        'PKS_MODEL_LIST',
        'PKS_CONTEXT_USAGE',
        'PKS_SESSION_INPUT_WAIT',
        'PKS_BROADCAST_MODE',
    ],
}

# Internal category keys stay English; labels use ``cat_*`` strings from settings_i18n.
SETTINGS_CATEGORY_TO_I18N_KEY: Dict[str, str] = {
    'CTF Variables': 'cat_ctf',
    'Core PKS Settings': 'cat_core',
    'API Keys': 'cat_api_keys',
    'Streaming & Output': 'cat_streaming',
    'Parallelization': 'cat_parallel',
    'Execution Limits': 'cat_limits',
    'Memory & Context': 'cat_memory',
    'Workspace': 'cat_workspace',
    'Support Agent': 'cat_support',
    'CTR Settings': 'cat_ctr',
    'Tracing & Telemetry': 'cat_tracing',
    'Security': 'cat_security',
    'Pricing': 'cat_pricing',
    'Reporting': 'cat_reporting',
    'API Server': 'cat_api_server',
    'Authentication': 'cat_auth',
    'MCP Settings': 'cat_mcp',
    'OpenRouter': 'cat_openrouter',
    'Ollama': 'cat_ollama',
    'LiteLLM': 'cat_litellm',
    'OpenAI': 'cat_openai',
    'Google': 'cat_google',
    'TUI Mode': 'cat_tui',
    'Advanced': 'cat_advanced',
}

# Comprehensive variable definitions for ALL settings
ADDITIONAL_VARS = {
    # =====================
    # API Keys
    # =====================
    'ALIAS_API_KEY': {
        'name': 'ALIAS_API_KEY',
        'description': 'Alias Robotics API key for alias1 model access',
        'default': None,
    },
    'OPENAI_API_KEY': {
        'name': 'OPENAI_API_KEY',
        'description': 'OpenAI API key for GPT models (gpt-4, gpt-4o, etc.)',
        'default': None,
    },
    'ANTHROPIC_API_KEY': {
        'name': 'ANTHROPIC_API_KEY',
        'description': 'Anthropic API key for Claude models (claude-3.5-sonnet, etc.)',
        'default': None,
    },
    'OPENROUTER_API_KEY': {
        'name': 'OPENROUTER_API_KEY',
        'description': 'OpenRouter API key for unified access to multiple LLM providers',
        'default': None,
    },
    'GOOGLE_API_KEY': {
        'name': 'GOOGLE_API_KEY',
        'description': 'Google API key for Gemini models',
        'default': None,
    },
    'OLLAMA_API_KEY': {
        'name': 'OLLAMA_API_KEY',
        'description': 'Ollama API key for authentication (optional for local)',
        'default': None,
    },
    'LITELLM_API_KEY': {
        'name': 'LITELLM_API_KEY',
        'description': 'LiteLLM proxy API key',
        'default': None,
    },

    # =====================
    # CTF Variables
    # =====================
    'CTF_MODEL': {
        'name': 'CTF_MODEL',
        'description': 'Model override for CTF challenges',
        'default': None,
    },
    'CTF_CONTAINER_NAME': {
        'name': 'CTF_CONTAINER_NAME',
        'description': 'Docker container name for CTF execution',
        'default': None,
    },
    'CTF_INSTANCE_ID': {
        'name': 'CTF_INSTANCE_ID',
        'description': 'Instance ID for CTF challenge tracking',
        'default': '',
    },

    # =====================
    # Core Settings
    # =====================
    'PKS_PARALLEL': {
        'name': 'PKS_PARALLEL',
        'description': 'Number of parallel agents to run simultaneously (1-20)',
        'default': '1',
    },
    'PKS_PARALLEL_AGENTS': {
        'name': 'PKS_PARALLEL_AGENTS',
        'description': 'Comma-separated list of agent names for parallel execution',
        'default': None,
    },
    'PKS_PARALLEL_EXTERNAL_TIMEOUT': {
        'name': 'PKS_PARALLEL_EXTERNAL_TIMEOUT',
        'description': (
            'Seconds the main CLI waits for each external parallel worker result file '
            '(workers may continue in their own terminals after timeout)'
        ),
        'default': '1800',
    },
    'PKS_MERGE_SUMMARIZE_PER_WORKER': {
        'name': 'PKS_MERGE_SUMMARIZE_PER_WORKER',
        'description': (
            'Before /merge, run an AI digest per parallel worker over the message threshold '
            '(reduces main context blow-up; set 0 to disable)'
        ),
        'default': '1',
    },
    'PKS_MERGE_SUMMARIZE_MIN_MESSAGES': {
        'name': 'PKS_MERGE_SUMMARIZE_MIN_MESSAGES',
        'description': 'Minimum messages in a worker history to trigger per-worker merge digest',
        'default': '20',
    },
    'PKS_TEMPERATURE': {
        'name': 'PKS_TEMPERATURE',
        'description': 'Model temperature (0.0=deterministic, 2.0=creative)',
        'default': '0.7',
    },
    'PKS_TOP_P': {
        'name': 'PKS_TOP_P',
        'description': 'Nucleus sampling top_p (0.0-1.0, controls token diversity)',
        'default': '1.0',
    },
    'PKS_AUTO_RUN_PARALLEL': {
        'name': 'PKS_AUTO_RUN_PARALLEL',
        'description': 'Auto-run parallel agents on startup',
        'default': 'false',
    },
    'PKS_AUTO_RUN_QUEUE': {
        'name': 'PKS_AUTO_RUN_QUEUE',
        'description': 'Auto-run queued commands',
        'default': 'false',
    },
    'PKS_QUEUE_FILE': {
        'name': 'PKS_QUEUE_FILE',
        'description': 'Path to command queue file',
        'default': None,
    },

    # =====================
    # Execution Limits
    # =====================
    'PKS_MAX_INTERACTIONS': {
        'name': 'PKS_MAX_INTERACTIONS',
        'description': 'Maximum interactions allowed in session',
        'default': 'inf',
    },
    'PKS_TOOL_TIMEOUT': {
        'name': 'PKS_TOOL_TIMEOUT',
        'description': 'Tool execution timeout in seconds (overrides defaults)',
        'default': None,
    },
    'PKS_IDLE_TIMEOUT': {
        'name': 'PKS_IDLE_TIMEOUT',
        'description': 'Idle timeout before session cleanup (seconds)',
        'default': '100',
    },
    'PKS_CODE_TIMEOUT': {
        'name': 'PKS_CODE_TIMEOUT',
        'description': 'Code execution timeout in seconds',
        'default': '30',
    },

    # =====================
    # Memory & Context
    # =====================
    'PKS_COMPACTED_MEMORY': {
        'name': 'PKS_COMPACTED_MEMORY',
        'description': 'Inject /compact conversation summaries into agent system prompts (true/false)',
        'default': 'false',
    },
    'PKS_CTX_TRUNC': {
        'name': 'PKS_CTX_TRUNC',
        'description': 'Enable context truncation for large outputs',
        'default': 'false',
    },
    'PKS_DISPLAY_MAX_OUTPUT': {
        'name': 'PKS_DISPLAY_MAX_OUTPUT',
        'description': 'Show full tool output without truncation (default truncates at 10000 chars)',
        'default': 'false',
    },
    'PKS_DEBUG_STREAMING': {
        'name': 'PKS_DEBUG_STREAMING',
        'description': 'Debug streaming output',
        'default': 'false',
    },

    # =====================
    # Workspace & Container
    # =====================
    'PKS_ACTIVE_CONTAINER': {
        'name': 'PKS_ACTIVE_CONTAINER',
        'description': 'Docker container ID for command execution',
        'default': '',
    },
    'PKS_ACTIVE_CONTAINER_DEFAULT': {
        'name': 'PKS_ACTIVE_CONTAINER_DEFAULT',
        'description': 'Default container when none specified',
        'default': '',
    },

    # =====================
    # Support & Meta Agent
    # =====================
    'PKS_META_AGENT': {
        'name': 'PKS_META_AGENT',
        'description': 'Enable meta agent for orchestration',
        'default': 'false',
    },
    'PKS_META_MODEL': {
        'name': 'PKS_META_MODEL',
        'description': 'Model for meta agent (defaults to PKS_MODEL)',
        'default': None,
    },
    'PKS_META_AUTOCLOSE_GRACE': {
        'name': 'PKS_META_AUTOCLOSE_GRACE',
        'description': 'Grace period for meta agent auto-close (seconds)',
        'default': '1.5',
    },

    # =====================
    # CTR (Cut The Rope)
    # =====================
    'PKS_CTR_DIGEST_MODE': {
        'name': 'PKS_CTR_DIGEST_MODE',
        'description': 'CTR interpretation: "llm" or "algorithmic"',
        'default': 'llm',
    },
    'PKS_CTR_DIGEST_MODEL': {
        'name': 'PKS_CTR_DIGEST_MODEL',
        'description': 'Model for LLM-based CTR digest',
        'default': 'alias1',
    },
    'PKS_CTR_OUTPUT_DIR': {
        'name': 'PKS_CTR_OUTPUT_DIR',
        'description': 'Directory for CTR output files',
        'default': None,
    },
    'PKS_CTR_DEFAULT_OUTPUT_DIR': {
        'name': 'PKS_CTR_DEFAULT_OUTPUT_DIR',
        'description': 'Default CTR output directory',
        'default': None,
    },
    'PKS_CTR_DEFAULT_RUN': {
        'name': 'PKS_CTR_DEFAULT_RUN',
        'description': 'Default CTR run identifier',
        'default': None,
    },
    'PKS_CTR_IS_CTF': {
        'name': 'PKS_CTR_IS_CTF',
        'description': 'CTR is in CTF mode',
        'default': 'false',
    },
    'PKS_CTR_DISTANCE_HEURISTIC': {
        'name': 'PKS_CTR_DISTANCE_HEURISTIC',
        'description': 'Distance heuristic for CTR graph',
        'default': None,
    },
    'PKS_GCTR_NITERATIONS': {
        'name': 'PKS_GCTR_NITERATIONS',
        'description': 'Tool interactions before GCTR analysis',
        'default': '5',
    },

    # =====================
    # Tracing & Telemetry
    # =====================
    'PKS_TELEMETRY': {
        'name': 'PKS_TELEMETRY',
        'description': 'Enable/disable telemetry collection',
        'default': 'true',
    },
    'PKS_DISABLE_SESSION_RECORDING': {
        'name': 'PKS_DISABLE_SESSION_RECORDING',
        'description': 'Disable session recording to JSONL',
        'default': 'false',
    },
    'PKS_DISABLE_USAGE_TRACKING': {
        'name': 'PKS_DISABLE_USAGE_TRACKING',
        'description': 'Disable usage/cost tracking',
        'default': 'false',
    },

    # =====================
    # Security
    # =====================
    'PKS_PLAN': {
        'name': 'PKS_PLAN',
        'description': 'Enable planning mode for agents',
        'default': 'false',
    },

    # =====================
    # Pricing
    # =====================
    'PKS_COST_DISPLAYED': {
        'name': 'PKS_COST_DISPLAYED',
        'description': 'Show cost display in output',
        'default': 'false',
    },
    'PKS_ENABLE_PRICING_FETCH': {
        'name': 'PKS_ENABLE_PRICING_FETCH',
        'description': 'Enable async pricing data fetch',
        'default': 'false',
    },
    'PKS_DEBUG_PRICING': {
        'name': 'PKS_DEBUG_PRICING',
        'description': 'Debug pricing calculations to file',
        'default': 'false',
    },
    'PKS_PRICING_FILE': {
        'name': 'PKS_PRICING_FILE',
        'description': 'Custom pricing data file path',
        'default': None,
    },
    'PKS_PRICINGS_DIR': {
        'name': 'PKS_PRICINGS_DIR',
        'description': 'Directory for pricing data files',
        'default': None,
    },

    # =====================
    # Reporting
    # =====================
    'PKS_CONTINUATION_FALLBACK_MODEL': {
        'name': 'PKS_CONTINUATION_FALLBACK_MODEL',
        'description': 'Fallback model when alias1 unavailable for continuation',
        'default': None,
    },

    # =====================
    # API Server
    # =====================
    'PKS_API_HOST': {
        'name': 'PKS_API_HOST',
        'description': 'API server host address',
        'default': '127.0.0.1',
    },
    'PKS_API_PORT': {
        'name': 'PKS_API_PORT',
        'description': 'API server port number',
        'default': '8000',
    },
    'PKS_API_CORS': {
        'name': 'PKS_API_CORS',
        'description': 'CORS allowed origins (* for all)',
        'default': '*',
    },
    'PKS_API_KEY_HEADER': {
        'name': 'PKS_API_KEY_HEADER',
        'description': 'Header name for API key authentication',
        'default': 'X-PKS-API-Key',
    },
    'PKS_API_LOG_AUTH': {
        'name': 'PKS_API_LOG_AUTH',
        'description': 'Log authentication attempts',
        'default': 'false',
    },
    'PKS_API_LOG_REQUESTS': {
        'name': 'PKS_API_LOG_REQUESTS',
        'description': 'Log all API requests',
        'default': 'false',
    },
    'PKS_API_LOG_LEVEL': {
        'name': 'PKS_API_LOG_LEVEL',
        'description': 'API logging level (debug, info, warning, error)',
        'default': 'info',
    },
    'PKS_API_RELOAD': {
        'name': 'PKS_API_RELOAD',
        'description': 'Enable API hot-reload mode',
        'default': 'false',
    },
    'PKS_API_WORKERS': {
        'name': 'PKS_API_WORKERS',
        'description': 'Number of API worker processes',
        'default': '1',
    },

    # =====================
    # Authentication
    # =====================
    'PKS_AUTH_BASE_URL': {
        'name': 'PKS_AUTH_BASE_URL',
        'description': 'Base URL for authentication service',
        'default': None,
    },
    'PKS_AUTH_DEVICE_PORT': {
        'name': 'PKS_AUTH_DEVICE_PORT',
        'description': 'Port for device authentication',
        'default': '10101',
    },
    'PKS_AUTH_PUBLIC_HOST': {
        'name': 'PKS_AUTH_PUBLIC_HOST',
        'description': 'Public hostname for authentication',
        'default': None,
    },
    'PKS_AUTH_PUBLIC_PORT': {
        'name': 'PKS_AUTH_PUBLIC_PORT',
        'description': 'Public port for authentication',
        'default': None,
    },
    'PKS_AUTH_SESSION_TTL_SECONDS': {
        'name': 'PKS_AUTH_SESSION_TTL_SECONDS',
        'description': 'Session time-to-live in seconds',
        'default': None,
    },

    # =====================
    # MCP Settings
    # =====================
    'PKS_MCP_TOKEN': {
        'name': 'PKS_MCP_TOKEN',
        'description': 'MCP authentication token',
        'default': None,
    },
    'PKS_MCP_AUTH_TOKEN': {
        'name': 'PKS_MCP_AUTH_TOKEN',
        'description': 'MCP auth token (alternative)',
        'default': None,
    },
    'PKS_MCP_SSE_TIMEOUT': {
        'name': 'PKS_MCP_SSE_TIMEOUT',
        'description': 'MCP SSE connection timeout (seconds)',
        'default': '5',
    },
    'PKS_MCP_SSE_READ_TIMEOUT': {
        'name': 'PKS_MCP_SSE_READ_TIMEOUT',
        'description': 'MCP SSE read timeout (seconds)',
        'default': '300',
    },

    # =====================
    # OpenRouter Settings
    # =====================
    'OPENROUTER_API_BASE': {
        'name': 'OPENROUTER_API_BASE',
        'description': 'OpenRouter API base URL',
        'default': 'https://openrouter.ai/api/v1',
    },
    'OPENROUTER_PROVIDER': {
        'name': 'OPENROUTER_PROVIDER',
        'description': 'Preferred provider order (comma-separated)',
        'default': None,
    },
    'OPENROUTER_PROVIDER_ONLY': {
        'name': 'OPENROUTER_PROVIDER_ONLY',
        'description': 'Restrict to only these providers',
        'default': None,
    },
    'OPENROUTER_PROVIDER_IGNORE': {
        'name': 'OPENROUTER_PROVIDER_IGNORE',
        'description': 'Ignore these providers (comma-separated)',
        'default': None,
    },
    'OPENROUTER_ALLOW_FALLBACKS': {
        'name': 'OPENROUTER_ALLOW_FALLBACKS',
        'description': 'Allow fallback to other providers',
        'default': 'true',
    },
    'OPENROUTER_QUANTIZATION': {
        'name': 'OPENROUTER_QUANTIZATION',
        'description': 'Quantization filter (fp8, int4, etc.)',
        'default': None,
    },

    # =====================
    # Ollama Settings
    # =====================
    'OLLAMA': {
        'name': 'OLLAMA',
        'description': 'Enable Ollama mode (true/false)',
        'default': '',
    },
    'OLLAMA_API_BASE': {
        'name': 'OLLAMA_API_BASE',
        'description': 'Ollama API base URL (e.g., http://localhost:11434/v1)',
        'default': 'https://ollama.com',
    },

    # =====================
    # LiteLLM Settings
    # =====================
    'LITELLM_BASE_URL': {
        'name': 'LITELLM_BASE_URL',
        'description': 'LiteLLM proxy base URL',
        'default': 'http://localhost:4000',
    },

    # =====================
    # OpenAI Settings
    # =====================
    'OPENAI_API_BASE': {
        'name': 'OPENAI_API_BASE',
        'description': 'Custom OpenAI API base URL',
        'default': None,
    },
    'CSI_CUSTOM_ENDPOINT': {
        'name': 'CSI_CUSTOM_ENDPOINT',
        'description': 'OpenAI-compatible URL from CSI (over ALIAS_API_URL) for pks/alias/csi-prefixed models',
        'default': None,
    },
    'ALIAS_API_URL': {
        'name': 'ALIAS_API_URL',
        'description': 'OpenAI-compatible URL after CSI_CUSTOM_ENDPOINT for qualifying models; else OPENAI_API_BASE',
        'default': None,
    },
    'OPENAI_BASE_URL': {
        'name': 'OPENAI_BASE_URL',
        'description': 'OpenAI base URL override',
        'default': None,
    },
    'OPENAI_ORG_ID': {
        'name': 'OPENAI_ORG_ID',
        'description': 'OpenAI organization ID',
        'default': None,
    },
    'OPENAI_PROJECT_ID': {
        'name': 'OPENAI_PROJECT_ID',
        'description': 'OpenAI project ID',
        'default': None,
    },

    # =====================
    # Google Settings
    # =====================
    'GOOGLE_SEARCH_API_KEY': {
        'name': 'GOOGLE_SEARCH_API_KEY',
        'description': 'Google Custom Search API key',
        'default': None,
    },
    'GOOGLE_SEARCH_CX': {
        'name': 'GOOGLE_SEARCH_CX',
        'description': 'Google Custom Search engine ID',
        'default': None,
    },

    # =====================
    # TUI Mode Settings
    # =====================
    'PKS_TUI_MODE': {
        'name': 'PKS_TUI_MODE',
        'description': 'Enable TUI (Terminal UI) mode',
        'default': 'false',
    },
    'PKS_TUI_STARTUP_YAML': {
        'name': 'PKS_TUI_STARTUP_YAML',
        'description': 'YAML file for TUI startup configuration',
        'default': None,
    },
    'PKS_TUI_SHARED_PROMPT': {
        'name': 'PKS_TUI_SHARED_PROMPT',
        'description': 'Shared prompt across TUI terminals',
        'default': None,
    },
    'PKS_TUI_MAX_LINES': {
        'name': 'PKS_TUI_MAX_LINES',
        'description': 'Maximum lines in TUI output',
        'default': None,
    },
    'PKS_TUI_MAX_RERENDERS_PER_SEC': {
        'name': 'PKS_TUI_MAX_RERENDERS_PER_SEC',
        'description': 'Max TUI re-renders per second',
        'default': None,
    },

    # =====================
    # Advanced/Internal
    # =====================
    'PKS_VERSION': {
        'name': 'PKS_VERSION',
        'description': 'PKS version string',
        'default': 'dev',
    },
    'PKS_THEME': {
        'name': 'PKS_THEME',
        'description': 'UI color theme',
        'default': None,
    },
    'PKS_SKIP_NETWORK_CHECK': {
        'name': 'PKS_SKIP_NETWORK_CHECK',
        'description': 'Skip network availability checks',
        'default': 'false',
    },
    'PKS_AUTO_COMPACT': {
        'name': 'PKS_AUTO_COMPACT',
        'description': 'Enable auto-compaction of context',
        'default': None,
    },
    'PKS_AUTO_COMPACT_THRESHOLD': {
        'name': 'PKS_AUTO_COMPACT_THRESHOLD',
        'description': 'Fraction of context window before auto-compact (e.g. 0.8); values above 0.8 are capped at 0.8',
        'default': None,
    },
    'PKS_WARN_UNATTRIBUTED': {
        'name': 'PKS_WARN_UNATTRIBUTED',
        'description': 'Warn about unattributed content',
        'default': 'false',
    },
    'PKS_UNATTRIBUTED_LOG': {
        'name': 'PKS_UNATTRIBUTED_LOG',
        'description': 'Log path for unattributed content',
        'default': '~/.cai_unattributed.log',
    },
    'PKS_PATTERN_DESCRIPTION': {
        'name': 'PKS_PATTERN_DESCRIPTION',
        'description': 'Description of current agent pattern',
        'default': '',
    },
    'PKS_DEFAULT_AGENT': {
        'name': 'PKS_DEFAULT_AGENT',
        'description': 'Default agent type',
        'default': 'redteam_agent',
    },
    'PKS_MODEL_LIST': {
        'name': 'PKS_MODEL_LIST',
        'description': 'Custom model list (comma-separated)',
        'default': None,
    },
    'PKS_CONTEXT_USAGE': {
        'name': 'PKS_CONTEXT_USAGE',
        'description': 'Enable context usage tracking',
        'default': None,
    },
    'PKS_SESSION_INPUT_WAIT': {
        'name': 'PKS_SESSION_INPUT_WAIT',
        'description': 'Wait time for session input (seconds)',
        'default': '5.0',
    },
    'PKS_BROADCAST_MODE': {
        'name': 'PKS_BROADCAST_MODE',
        'description': 'Enable broadcast mode for parallel agents',
        'default': None,
    },
}

# =============================================================================
# TUI/CLI Mode Detection
# =============================================================================

# [J] Extracted to settings/general.py — import from there as single source of truth
from pks.repl.commands.settings.general import (  # noqa: E402, F811
    is_tui_mode,
    get_current_terminal_id,
)


# =============================================================================
# Language Functions
# =============================================================================

def get_current_language() -> str:
    """Get the current language setting."""
    global _current_language
    return _current_language


def set_current_language(lang: str) -> None:
    """Set the current language."""
    global _current_language
    if lang in SUPPORTED_LANGUAGES:
        _current_language = lang
        os.environ['PKS_SETTINGS_LANGUAGE'] = lang


def tr(key: str) -> str:
    """Translate a key to the current language (shorthand for get_string)."""
    return get_string(key, get_current_language())


def _questionary_current_hint(var_name: str, current_value: str) -> str:
    """Plain suffix for questionary prompts/choices (no Rich — questionary prints markup literally)."""
    lang = get_current_language()
    if "API_KEY" in var_name or var_name.endswith("_KEY"):
        if not current_value:
            return get_string("hint_not_set_suffix", lang)
        cv = current_value
        if len(cv) > 12:
            masked = cv[:8] + "*" * max(0, len(cv) - 12) + cv[-4:]
        else:
            masked = "*" * len(cv)
        return get_string("hint_current_masked", lang).replace("{masked}", masked)
    if current_value:
        return get_string("hint_current_plain", lang).replace("{value}", current_value)
    return get_string("hint_not_set_suffix", lang)


def _questionary_choice_value_display(var_name: str, current_value: str) -> str:
    """Plain value fragment for ``VAR: value`` in questionary lists (no Rich)."""
    lang = get_current_language()
    if "API_KEY" in var_name or var_name.endswith("_KEY"):
        if current_value:
            masked = "***" + current_value[-4:] if len(current_value) > 4 else "***"
            return get_string("choice_value_masked", lang).replace("{masked}", masked)
        return get_string("choice_value_not_set", lang)
    if current_value:
        text = current_value
        if len(text) > 50:
            text = text[:47] + "..."
        return text
    return get_string("choice_value_not_set", lang)


def category_menu_choice_text(category_key_en: str, var_count: int) -> str:
    """Visible label for a settings category (translated); internal key stays English."""
    i18n_key = SETTINGS_CATEGORY_TO_I18N_KEY.get(category_key_en)
    label = tr(i18n_key) if i18n_key else category_key_en
    return f"{ICON_CAT}{label} ({var_count})"


def select_language() -> Optional[str]:
    """Show language selection dialog.

    Returns:
        Selected language code, or None if cancelled
    """
    choices = [
        questionary.Choice(f"{name} ({code})", code)
        for code, name in SUPPORTED_LANGUAGES.items()
    ]

    result = questionary.select(
        tr("select_language") + ":",
        choices=choices,
        default=get_current_language(),
        style=custom_style,
    ).ask()

    if result:
        set_current_language(result)

    return result


# =============================================================================
# FAQ and Troubleshooting Functions
# =============================================================================

def show_faq_menu() -> bool:
    """Show the FAQ and troubleshooting menu.

    Returns:
        True if user wants to continue, False to exit
    """
    if not HAS_VALIDATION:
        console.print(f"[yellow]{tr('faq_module_unavailable')}[/yellow]")
        return True

    while True:
        console.clear()
        console.print("\n")

        # Header
        console.print(Panel(
            f"[bold {_PKS_ACCENT}]{tr('faq_title')}[/bold {_PKS_ACCENT}]\n\n"
            f"[dim]{tr('faq_panel_subtitle')}[/dim]",
            border_style=_PKS_ACCENT,
            padding=(1, 2)
        ))
        console.print()

        # FAQ topics
        faq_topics = [
            questionary.Choice(ICON_TOPIC + tr('faq_api_keys'), "api_keys"),
            questionary.Choice(ICON_TOPIC + tr('faq_ollama'), "ollama"),
            questionary.Choice(ICON_TOPIC + tr('faq_streaming'), "streaming"),
            questionary.Choice(ICON_TOPIC + tr('faq_parallel'), "parallel"),
            questionary.Choice(ICON_TOPIC + tr('faq_memory'), "memory"),
            questionary.Choice(ICON_TOPIC + tr('faq_tui'), "tui"),
            questionary.Choice(ICON_TOPIC + tr('faq_connection'), "connection"),
            questionary.Choice(ICON_TOPIC + tr('faq_action_validate_all'), "validate_all"),
            questionary.Choice(ICON_TOPIC + tr('faq_action_system_status'), "system_status"),
            questionary.Choice("[" + tr('back') + "]", "__back__"),
        ]

        selected = questionary.select(
            tr('faq_select'),
            choices=faq_topics,
            style=custom_style
        ).ask()

        if not selected or selected == "__back__":
            return True

        if selected == "validate_all":
            show_api_key_validation()
        elif selected == "system_status":
            show_system_status()
        elif selected == "api_keys":
            show_api_keys_faq()
        elif selected == "ollama":
            show_ollama_faq()
        else:
            show_generic_faq(selected)

        # Wait for user to press enter
        console.print(f"\n[dim]{tr('press_enter_continue')}[/dim]")
        input()


def show_api_key_validation() -> None:
    """Validate all API keys and show results."""
    console.print("\n")
    console.print(Panel(
        f"[bold {_PKS_ACCENT}]{tr('validating_api_keys_panel')}[/bold {_PKS_ACCENT}]",
        border_style=_PKS_ACCENT
    ))
    console.print()

    results = validate_all_api_keys()

    table = Table(title=tr("api_key_validation_table_title"), show_header=True)
    table.add_column(tr("table_col_api_key"), style=_PKS_ACCENT)
    table.add_column(tr("table_col_status"), style="bold")
    table.add_column(tr("table_col_message"))

    for key_name, result in results.items():
        if result.status == ValidationStatus.VALID:
            status = f"[bold {_PKS_ACCENT}]{tr('status_valid')}[/bold {_PKS_ACCENT}]"
        elif result.status == ValidationStatus.INVALID:
            status = f"[red]{tr('status_invalid')}[/red]"
        elif result.status == ValidationStatus.NOT_SET:
            status = f"[yellow]{tr('status_not_set')}[/yellow]"
        else:
            status = f"[orange1]{tr('status_error')}[/orange1]"

        table.add_row(key_name, status, result.message)

    console.print(table)


def show_system_status() -> None:
    """Show comprehensive system status."""
    console.print("\n")
    console.print(Panel(
        f"[bold {_PKS_ACCENT}]{tr('checking_system_status')}[/bold {_PKS_ACCENT}]",
        border_style=_PKS_ACCENT
    ))
    console.print()

    status = get_configuration_status()

    # Network status
    network = status.get('network')
    if network:
        if network.status == ValidationStatus.VALID:
            console.print(f"[bold {_PKS_ACCENT}]{tr('network_ok')}[/bold {_PKS_ACCENT}]")
        else:
            console.print(f"[red]{tr('network_issues').replace('{message}', network.message)}[/red]")

    console.print()

    # Ollama status
    ollama = status.get('ollama')
    if ollama:
        if ollama.status == ValidationStatus.VALID:
            console.print(f"[bold {_PKS_ACCENT}]{ollama.message}[/bold {_PKS_ACCENT}]")
            models = status.get('ollama_models', [])
            if models:
                console.print(f"   {tr('available_models_label')}: {', '.join(models[:5])}")
                if len(models) > 5:
                    console.print(f"   {tr('and_n_more').replace('{n}', str(len(models) - 5))}")
        else:
            console.print(
                f"[yellow]{tr('ollama_status_prefix').replace('{message}', ollama.message)}[/yellow]"
            )

    console.print()

    # API Keys summary
    api_keys = status.get('api_keys', {})
    valid_count = sum(1 for r in api_keys.values() if r.status == ValidationStatus.VALID)
    set_count = sum(1 for r in api_keys.values() if r.status != ValidationStatus.NOT_SET)

    console.print(
        f"[bold {_PKS_ACCENT}]"
        f"{tr('api_keys_summary').format(valid_count=valid_count, set_count=set_count, not_cfg=len(api_keys) - set_count)}"
        f"[/bold {_PKS_ACCENT}]"
    )


def show_api_keys_faq() -> None:
    """Show API keys troubleshooting guide."""
    console.print("\n")

    faq = get_faq('api_keys', get_current_language())
    if not faq:
        console.print(f"[yellow]{tr('faq_content_unavailable')}[/yellow]")
        return

    console.print(Panel(
        f"[bold {_PKS_ACCENT}]{faq.get('title', 'API Key Troubleshooting')}[/bold {_PKS_ACCENT}]\n\n"
        f"{faq.get('description', '')}",
        border_style=_PKS_ACCENT
    ))
    console.print()

    for check in faq.get('checks', []):
        name = check.get('name', '')
        env_var = check.get('env_var', '')
        current_value = os.getenv(env_var, '')

        # Status indicator
        if current_value:
            status = f"[bold {_PKS_ACCENT}]*[/bold {_PKS_ACCENT}]"
            masked = '***' + current_value[-4:] if len(current_value) > 4 else '***'
            value_display = tr("value_set_masked").replace("{masked}", masked)
        else:
            status = "[red]-[/red]"
            value_display = tr("not_set")

        console.print(f"{status} [bold]{name}[/bold] ({env_var})")
        console.print(f"   {tr('label_status')}: {value_display}")

        if not current_value:
            solutions = check.get('solutions', [])
            if solutions:
                console.print(
                    f"   [dim]{tr('fix_prefix').replace('{text}', solutions[0])}[/dim]"
                )

        console.print()


def show_ollama_faq() -> None:
    """Show Ollama troubleshooting guide with live checks."""
    console.print("\n")

    faq = get_faq('ollama', get_current_language())
    if not faq:
        faq = {}

    console.print(Panel(
        f"[bold {_OLLAMA_FAQ_STYLE}]{faq.get('title', 'Ollama / Local Models Troubleshooting')}[/bold {_OLLAMA_FAQ_STYLE}]\n\n"
        f"[dim]{faq.get('description', 'How to set up and troubleshoot Ollama for local model inference')}[/dim]",
        border_style=_OLLAMA_FAQ_STYLE,
        padding=(1, 2),
    ))
    console.print()

    # Live check
    console.print(f"[bold {_OLLAMA_FAQ_STYLE}]{tr('live_status_check')}:[/bold {_OLLAMA_FAQ_STYLE}]")
    ollama_result = check_ollama_running()

    if ollama_result.status == ValidationStatus.VALID:
        console.print(f"[bold {_OLLAMA_FAQ_STYLE}]{ollama_result.message}[/bold {_OLLAMA_FAQ_STYLE}]")

        # List models
        success, models = list_ollama_models()
        if success and models:
            console.print(
                f"\n[bold {_OLLAMA_FAQ_STYLE}]"
                f"{tr('available_models_label')} ({len(models)}):[/bold {_OLLAMA_FAQ_STYLE}]"
            )
            for model in models[:10]:
                console.print(f"  [dim]•[/dim] [cyan]{model}[/cyan]")
            if len(models) > 10:
                console.print(f"  [dim]{tr('and_n_more').replace('{n}', str(len(models) - 10))}[/dim]")
    else:
        console.print(f"[red]{ollama_result.message}[/red]")

        details = ollama_result.details or {}
        sugg_keys = details.get("suggestion_keys") or []
        legacy = details.get("suggestions") or []
        if sugg_keys:
            console.print(f"\n[bold {_OLLAMA_FAQ_STYLE}]{tr('suggestions_header')}:[/bold {_OLLAMA_FAQ_STYLE}]")
            for sk in sugg_keys:
                console.print(f"  [dim]•[/dim] {tr(sk)}")
        elif legacy:
            console.print(f"\n[bold {_OLLAMA_FAQ_STYLE}]{tr('suggestions_header')}:[/bold {_OLLAMA_FAQ_STYLE}]")
            for suggestion in legacy:
                console.print(f"  [dim]•[/dim] {suggestion}")

    console.print()

    # Configuration steps
    console.print(f"[bold {_OLLAMA_FAQ_STYLE}]{tr('setup_steps_header')}:[/bold {_OLLAMA_FAQ_STYLE}]")
    steps = faq.get('steps', [
        {'step': 1, 'title': 'Install Ollama', 'command': 'Download from https://ollama.com/download'},
        {'step': 2, 'title': 'Start server', 'command': 'ollama serve'},
        {'step': 3, 'title': 'Pull a model', 'command': 'ollama pull llama3.2'},
    ])

    for step_info in steps:
        step_num = step_info.get('step', '?')
        title = step_info.get('title', '')
        command = step_info.get('command', '')
        console.print(f"  [cyan]{step_num}.[/cyan] {title}")
        if command:
            console.print(f"     [dim cyan]$ {command}[/dim cyan]")

    console.print()

    # Current configuration
    console.print(f"[bold {_OLLAMA_FAQ_STYLE}]{tr('current_configuration_header')}:[/bold {_OLLAMA_FAQ_STYLE}]")
    ns = tr("choice_value_not_set")
    ollama_vars = {
        'OLLAMA': os.getenv('OLLAMA', ns),
        'OLLAMA_API_BASE': os.getenv('OLLAMA_API_BASE', ns),
        'OLLAMA_API_KEY': '***' if os.getenv('OLLAMA_API_KEY') else ns,
    }

    for var, value in ollama_vars.items():
        console.print(f"  [cyan]{var}[/cyan] = [dim]{value}[/dim]")


def show_generic_faq(topic: str) -> None:
    """Show FAQ for a generic topic."""
    console.print("\n")

    faq = get_faq(topic, get_current_language())
    if not faq:
        console.print(f"[yellow]{tr('no_faq_for_topic').replace('{topic}', topic)}[/yellow]")
        return

    console.print(Panel(
        f"[bold {_PKS_ACCENT}]{faq.get('title', topic.title())}[/bold {_PKS_ACCENT}]\n\n"
        f"{faq.get('description', '')}",
        border_style=_PKS_ACCENT
    ))
    console.print()

    # Show related commands if present
    related_commands = faq.get('related_commands', [])
    if related_commands:
        console.print(f"[bold {_PKS_ACCENT}]{tr('related_commands_header')}:[/bold {_PKS_ACCENT}]")
        for cmd in related_commands:
            if isinstance(cmd, dict):
                c = cmd.get("command", "")
                console.print(f"  [bold {_PKS_ACCENT}]{c}[/bold {_PKS_ACCENT}]")
                console.print(f"    [dim]{cmd.get('description', '')}[/dim]")
            else:
                console.print(f"  [bold {_PKS_ACCENT}]{cmd}[/bold {_PKS_ACCENT}]")
        console.print()

    # Show variables if present
    variables = faq.get('variables', {})
    if variables:
        console.print(f"[bold]{tr('environment_variables_header')}:[/bold]")
        for var_name, description in variables.items():
            current = os.getenv(var_name, tr("choice_value_not_set"))
            if isinstance(description, dict):
                desc_text = description.get('description', '')
            else:
                desc_text = description
            console.print(f"  • {var_name}: {desc_text}")
            console.print(
                f"    {tr('var_current_line').replace('{value}', f'[bold {_PKS_ACCENT}]{current}[/bold {_PKS_ACCENT}]')}"
            )
        console.print()

    # Show common issues if present
    common_issues = faq.get('common_issues', [])
    if common_issues:
        console.print(f"[bold]{tr('common_issues_header')}:[/bold]")
        for issue in common_issues:
            if isinstance(issue, dict):
                console.print(f"  • {issue.get('issue', '')}")
                if 'fix' in issue:
                    console.print(
                        f"    [dim]{tr('fix_prefix').replace('{text}', issue['fix'])}[/dim]"
                    )
            else:
                console.print(f"  • {issue}")
        console.print()


# =============================================================================
# TUI/CLI Variable Separation
# =============================================================================

# [J] Extracted to settings/general.py — import from there as single source of truth
from pks.repl.commands.settings.general import (  # noqa: E402
    CLI_ONLY_VARIABLES,
    TUI_ONLY_VARIABLES,
    custom_style,
    filter_variables_for_mode,
)


# [J] Extracted to settings/general.py — import from there as single source of truth
from pks.repl.commands.settings.general import (  # noqa: E402, F811
    get_env_file_path,
    read_env_file,
    write_env_file,
)


def get_all_vars() -> Dict[str, Dict]:
    """Get all available variables (from ENV_VARS + ADDITIONAL_VARS).
    Automatically generates definitions for API keys found in .env but not yet defined.
    Only considers API keys from .env file, not from os.environ.
    
    Returns:
        Dictionary mapping variable names to their info dicts
    """
    all_vars = {}
    
    # Add from ENV_VARS
    for var_info in ENV_VARS.values():
        all_vars[var_info['name']] = var_info
    
    # Add additional vars not in ENV_VARS
    all_vars.update(ADDITIONAL_VARS)
    
    # Auto-generate definitions ONLY for API keys in .env file (not os.environ)
    env_file = read_env_file()
    for key in env_file.keys():
        if (key.endswith('_API_KEY') or (key.endswith('_KEY') and 'API' in key.upper())) and key not in all_vars:
            # Generate a friendly description based on the key name
            provider_name = key.replace('_API_KEY', '').replace('_KEY', '').replace('_', ' ').title()
            all_vars[key] = {
                'name': key,
                'description': f'{provider_name} API key',
                'default': None,
            }
    
    return all_vars


def get_variables_by_category() -> Dict[str, List[str]]:
    """Get curated list of variables organized by category.
    Dynamically adds all API keys found in .env file to the 'API Keys' category.
    Only shows API keys that exist in the .env file, not in os.environ.
    Categories are returned in alphabetical order.
    
    Returns:
        Dictionary mapping category names to lists of variable names (alphabetically sorted)
    """
    categories = SETTINGS_VARIABLES.copy()
    
    # Detect all API keys ONLY from .env file (not from os.environ)
    env_file = read_env_file()
    detected_api_keys = set()
    
    for key in env_file.keys():
        # Detect variables ending in _API_KEY or _KEY (but exclude non-API keys)
        if key.endswith('_API_KEY') or (key.endswith('_KEY') and 'API' in key.upper()):
            detected_api_keys.add(key)
    
    # Update the API Keys category with detected keys from .env
    if detected_api_keys:
        # Start with hardcoded important ones (if they exist in .env)
        api_keys = []
        for key in ['ALIAS_API_KEY', 'OPENAI_API_KEY']:
            if key in detected_api_keys:
                api_keys.append(key)
                detected_api_keys.remove(key)
        
        # Add remaining detected keys alphabetically
        for key in sorted(detected_api_keys):
            api_keys.append(key)
        
        categories['API Keys'] = api_keys
    
    # Return categories sorted alphabetically by category name
    return dict(sorted(categories.items()))


# [J] Extracted to settings/general.py — import from there as single source of truth
from pks.repl.commands.settings.general import (  # noqa: E402, F811
    get_current_value,
    is_boolean_variable,
    update_env_file,
    delete_env_variable,
)


def add_new_api_key() -> Optional[Tuple[str, str]]:
    """Interactive prompt to add a new API key.
    
    Returns:
        Tuple of (key_name, key_value) if successful, None if cancelled
    """
    import re
    
    console.print("\n")
    console.print(Panel(
        f"[bold {_PKS_ACCENT}]{ICON_ADD}{tr('add_new_api_key_title')}[/bold {_PKS_ACCENT}]\n\n"
        f"{tr('add_new_api_key_intro')}",
        border_style=_PKS_ACCENT,
        padding=(1, 2)
    ))
    console.print()
    
    # Validator for API key name format
    def validate_api_key_name(text):
        # Must match pattern: PROVIDER_API_KEY (uppercase, ends with _API_KEY)
        pattern = r'^[A-Z][A-Z0-9_]*_API_KEY$'
        if not text:
            return tr("err_api_key_name_empty")
        if not re.match(pattern, text):
            return tr("err_api_key_name_format")
        # Check if already exists
        env_file = read_env_file()
        if text in env_file:
            return tr("err_api_key_exists").replace("{name}", text)
        return True
    
    # Ask for the API key name
    key_name = questionary.text(
        tr("enter_api_key_name"),
        validate=validate_api_key_name,
        style=custom_style
    ).ask()
    
    if not key_name:
        return None
    
    # Ask for the API key value
    key_value = questionary.password(
        tr("enter_api_key_value").replace("{name}", key_name),
        validate=lambda x: True if x else tr("err_api_key_value_empty"),
        style=custom_style
    ).ask()
    
    if not key_value:
        return None
    
    return (key_name, key_value)


def delete_api_key_interactive(api_key_name: str, current_value: str) -> bool:
    """Interactive confirmation to delete an API key.
    
    Args:
        api_key_name: Name of the API key to delete
        current_value: Current value (for display)
        
    Returns:
        True if deleted, False if cancelled
    """
    console.print("\n")
    
    # Mask the value for display
    masked = '***' + current_value[-4:] if len(current_value) > 4 else '***'
    
    console.print(Panel(
        f"[bold red]{ICON_WARN}{tr('delete_api_key_title')}[/bold red]\n\n"
        f"Key: [bold {_PKS_ACCENT}]{api_key_name}[/bold {_PKS_ACCENT}]\n"
        f"Value: [dim]{masked}[/dim]\n\n"
        f"[yellow]{tr('delete_api_key_irreversible')}[/yellow]",
        border_style="red",
        padding=(1, 2)
    ))
    console.print()
    
    # Ask for confirmation
    confirm = questionary.confirm(
        tr("delete_api_key_confirm").replace("{name}", api_key_name),
        default=False,
        style=custom_style
    ).ask()
    
    if confirm:
        if delete_env_variable(api_key_name):
            console.print()
            console.print(Panel(
                f"[bold {_PKS_ACCENT}]{tr('api_key_deleted_title').replace('{name}', api_key_name)}[/bold {_PKS_ACCENT}]\n\n"
                f"[dim]{tr('api_key_deleted_body')}[/dim]",
                border_style=_PKS_ACCENT,
                padding=(1, 2)
            ))
            console.print()
            return True
        else:
            console.print(f"[red]{tr('failed_delete_api_key')}[/red]")
            return False
    
    return False


def prompt_for_variable(var_info: Dict, current_value: str) -> Optional[str]:
    """Prompt user for a single variable value using appropriate widget.
    
    Args:
        var_info: Variable information dictionary
        current_value: Current value of the variable
        
    Returns:
        New value or None if cancelled
    """
    var_name = var_info['name']
    description = var_info['description']
    default_value = var_info.get('default')

    # questionary does not render Rich markup — use plain text only
    display_current = _questionary_current_hint(var_name, current_value)
    
    # Determine appropriate input method
    if 'API_KEY' in var_name or var_name.endswith('_KEY'):
        # Password input for API keys
        result = questionary.password(
            f"{description}{display_current}",
            default=current_value if current_value else '',
            style=custom_style
        ).ask()
        
        return result
    
    elif is_boolean_variable(var_name, description):
        # Boolean toggle (true/false, yes/no, on/off, 0/1)
        current_bool = current_value.lower() in ['true', 'yes', '1', 'on'] if current_value else False
        
        result = questionary.confirm(
            f"{description}{display_current}",
            default=current_bool,
            style=custom_style
        ).ask()
        
        if result is None:
            return None
        
        return 'true' if result else 'false'
    
    elif var_name == 'PKS_DEBUG':
        # Special handling for debug level (0, 1, 2)
        result = questionary.select(
            f"{description}{display_current}",
            choices=[
                questionary.Choice("0 - Only tool outputs", "0"),
                questionary.Choice("1 - Verbose debug output", "1"),
                questionary.Choice("2 - CLI debug output", "2"),
            ],
            default=current_value if current_value in ['0', '1', '2'] else "1",
            style=custom_style
        ).ask()
        
        return result
    
    elif var_name == 'PKS_MODEL':
        # Model selection with autocomplete
        try:
            # Load all available models (predefined + LiteLLM + Ollama)
            all_models, _ = load_all_available_models()
            
            # Ensure alias1 is at the top of the list for easy access
            if 'alias1' in all_models:
                all_models.remove('alias1')
                all_models.insert(0, 'alias1')
            
            if not all_models:
                all_models = ['alias1']  # Fallback if loading fails
        except Exception:
            # Fallback to basic list if loading fails
            all_models = [
                'alias1',
                'gpt-4-turbo',
                'gpt-4o',
                'gpt-4o-mini',
                'claude-3.5-sonnet',
                'claude-3-7-sonnet',
                'o3-mini',
                'o1',
                'o1-mini',
                'o1-preview',
            ]
        
        # Create validator that checks if model is in list
        def validate_model(text):
            if text in all_models:
                return True
            return tr("err_model_not_found").replace("{name}", text)
        
        result = questionary.autocomplete(
            f"{description}{display_current}\n"
            f"{tr('prompt_type_to_search_accept')}",
            choices=all_models,
            default=current_value if current_value else 'alias1',
            style=custom_style,
            validate=validate_model
        ).ask()
        
        return result
    
    elif var_name == 'PKS_AGENT_TYPE':
        # Agent type selection with autocomplete
        try:
            # Get all available agents dynamically
            available_agents_dict = get_available_agents()
            agent_keys = list(available_agents_dict.keys())
            
            # Filter out parallel patterns (they have special handling)
            agent_keys = [
                key for key in agent_keys 
                if not (hasattr(available_agents_dict[key], '_pattern') and 
                       hasattr(available_agents_dict[key]._pattern, 'type') and
                       getattr(available_agents_dict[key]._pattern.type, 'value', None) == 'parallel')
            ]
            
            # Sort agents alphabetically, but put current value first if it exists
            agent_keys.sort()
            if current_value and current_value in agent_keys:
                agent_keys.remove(current_value)
                agent_keys.insert(0, current_value)
            
            if not agent_keys:
                agent_keys = ['redteam_agent']  # Fallback
        except Exception:
            # Fallback to basic list if loading fails
            agent_keys = [
                'redteam_agent',
                'one_tool',
                'boot2root',
                'blue_teamer',
                'bug_bounty',
                'reporter',
                'web_pentester',
            ]
        
        # Create validator that checks if agent is in list
        def validate_agent(text):
            if text in agent_keys:
                return True
            return tr("err_agent_not_found").replace("{name}", text)
        
        result = questionary.autocomplete(
            f"{description}{display_current}\n"
            f"{tr('prompt_type_to_search_accept')}",
            choices=agent_keys,
            default=current_value if current_value else 'redteam_agent',
            style=custom_style,
            validate=validate_agent
        ).ask()
        
        return result
    
    elif var_name == 'PKS_TEMPERATURE':
        # Temperature selection (numeric but with guidance)
        temps = [
            questionary.Choice("0.0 - Deterministic (most consistent)", "0.0"),
            questionary.Choice("0.5 - Balanced (slight variation)", "0.5"),
            questionary.Choice("0.7 - Default (balanced creativity)", "0.7"),
            questionary.Choice("1.0 - Creative (more variation)", "1.0"),
            questionary.Choice("1.5 - Very creative (high variation)", "1.5"),
            questionary.Choice("2.0 - Maximum creativity", "2.0"),
            questionary.Choice(tr("choice_custom_value"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=temps,
            default="0.7" if not current_value else current_value,
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_temperature"),
                default=current_value if current_value else "0.7",
                style=custom_style,
                validate=lambda x: x.replace('.', '').isdigit() and 0 <= float(x) <= 2.0
            ).ask()

        return result

    elif var_name == 'PKS_TOP_P':
        # Top-p selection (nucleus sampling)
        top_p_choices = [
            questionary.Choice("0.5 - More focused (fewer tokens considered)", "0.5"),
            questionary.Choice("0.7 - Balanced focus", "0.7"),
            questionary.Choice("0.9 - Broader sampling", "0.9"),
            questionary.Choice("1.0 - Default (all tokens considered)", "1.0"),
            questionary.Choice(tr("choice_custom_value"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=top_p_choices,
            default="1.0" if not current_value else current_value,
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_top_p"),
                default=current_value if current_value else "1.0",
                style=custom_style,
                validate=lambda x: x.replace('.', '').isdigit() and 0 <= float(x) <= 1.0
            ).ask()

        return result
    
    elif var_name == 'PKS_PARALLEL':
        # Number input with validation
        result = questionary.text(
            f"{description}{display_current}",
            default=current_value if current_value else "1",
            style=custom_style,
            validate=lambda x: x.isdigit() and int(x) >= 1 and int(x) <= 20
        ).ask()

        return result

    elif var_name == 'PKS_COMPACTED_MEMORY':
        compacted_choices = [
            questionary.Choice("false - Do not inject /compact summaries", "false"),
            questionary.Choice("true - Inject /compact summaries into prompts", "true"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=compacted_choices,
            default=current_value if current_value in ('false', 'true') else "false",
            style=custom_style,
        ).ask()

        return result

    elif var_name == 'PKS_REPORT':
        # Report mode selection
        report_choices = [
            questionary.Choice("ctf - CTF challenge reports", "ctf"),
            questionary.Choice("pentesting - Pentest reports", "pentesting"),
            questionary.Choice("nis2 - NIS2 compliance reports", "nis2"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=report_choices,
            default=current_value if current_value in ['ctf', 'pentesting', 'nis2'] else "ctf",
            style=custom_style
        ).ask()

        return result

    elif var_name == 'PKS_CTR_DIGEST_MODE':
        # CTR digest mode selection
        ctr_choices = [
            questionary.Choice("llm - LLM-powered interpretation (flexible)", "llm"),
            questionary.Choice("algorithmic - Rule-based interpretation (fast)", "algorithmic"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=ctr_choices,
            default=current_value if current_value in ['llm', 'algorithmic'] else "llm",
            style=custom_style
        ).ask()

        return result

    elif var_name == 'PKS_API_LOG_LEVEL':
        # Log level selection
        log_choices = [
            questionary.Choice("debug - Detailed debugging info", "debug"),
            questionary.Choice("info - General information (default)", "info"),
            questionary.Choice("warning - Warning messages only", "warning"),
            questionary.Choice("error - Error messages only", "error"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=log_choices,
            default=current_value if current_value in ['debug', 'info', 'warning', 'error'] else "info",
            style=custom_style
        ).ask()

        return result

    elif var_name in ['PKS_MAX_TURNS', 'PKS_MAX_INTERACTIONS']:
        # Numeric with infinity option
        limit_choices = [
            questionary.Choice("inf - Unlimited", "inf"),
            questionary.Choice("10 turns", "10"),
            questionary.Choice("25 turns", "25"),
            questionary.Choice("50 turns", "50"),
            questionary.Choice("100 turns", "100"),
            questionary.Choice(tr("choice_custom_value"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=limit_choices,
            default=current_value if current_value else "inf",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_max_turns"),
                default=current_value if current_value else "inf",
                style=custom_style,
                validate=lambda x: x == 'inf' or (x.isdigit() and int(x) >= 1)
            ).ask()

        return result

    elif var_name == 'PKS_PRICE_LIMIT':
        # Price limit with common values
        price_choices = [
            questionary.Choice("$0.50", "0.5"),
            questionary.Choice("$1.00 (default)", "1"),
            questionary.Choice("$2.00", "2"),
            questionary.Choice("$5.00", "5"),
            questionary.Choice("$10.00", "10"),
            questionary.Choice("$50.00", "50"),
            questionary.Choice("inf - No limit", "inf"),
            questionary.Choice(tr("choice_custom_amount"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=price_choices,
            default=current_value if current_value else "1",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_price_limit"),
                default=current_value if current_value else "1",
                style=custom_style,
                validate=lambda x: x == 'inf' or (x.replace('.', '').isdigit() and float(x) >= 0)
            ).ask()

        return result

    elif var_name in ['PKS_TOOL_TIMEOUT', 'PKS_IDLE_TIMEOUT', 'PKS_CODE_TIMEOUT']:
        # Timeout in seconds
        timeout_choices = [
            questionary.Choice("10 seconds", "10"),
            questionary.Choice("30 seconds", "30"),
            questionary.Choice("60 seconds (1 min)", "60"),
            questionary.Choice("100 seconds (default)", "100"),
            questionary.Choice("300 seconds (5 min)", "300"),
            questionary.Choice("600 seconds (10 min)", "600"),
            questionary.Choice(tr("choice_custom_value"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=timeout_choices,
            default=current_value if current_value else "100",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_timeout_seconds"),
                default=current_value if current_value else "100",
                style=custom_style,
                validate=lambda x: x.isdigit() and int(x) >= 1
            ).ask()

        return result

    elif var_name in ['PKS_SUPPORT_INTERVAL', 'PKS_GCTR_NITERATIONS']:
        # Interval in turns
        interval_choices = [
            questionary.Choice("1 - Every turn", "1"),
            questionary.Choice("3 turns", "3"),
            questionary.Choice("5 turns (default)", "5"),
            questionary.Choice("10 turns", "10"),
            questionary.Choice(tr("choice_custom_value"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=interval_choices,
            default=current_value if current_value else "5",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_interval_turns"),
                default=current_value if current_value else "5",
                style=custom_style,
                validate=lambda x: x.isdigit() and int(x) >= 1
            ).ask()

        return result

    elif var_name == 'PKS_API_PORT':
        # Port number
        port_choices = [
            questionary.Choice("8000 (default)", "8000"),
            questionary.Choice("8080", "8080"),
            questionary.Choice("3000", "3000"),
            questionary.Choice("5000", "5000"),
            questionary.Choice(tr("choice_custom_port"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=port_choices,
            default=current_value if current_value else "8000",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_port"),
                default=current_value if current_value else "8000",
                style=custom_style,
                validate=lambda x: x.isdigit() and 1 <= int(x) <= 65535
            ).ask()

        return result

    elif var_name == 'PKS_API_WORKERS':
        # Number of workers
        worker_choices = [
            questionary.Choice("1 (default)", "1"),
            questionary.Choice("2", "2"),
            questionary.Choice("4", "4"),
            questionary.Choice("8", "8"),
            questionary.Choice(tr("choice_custom_value"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=worker_choices,
            default=current_value if current_value else "1",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_workers"),
                default=current_value if current_value else "1",
                style=custom_style,
                validate=lambda x: x.isdigit() and int(x) >= 1
            ).ask()

        return result

    elif var_name in ['PKS_SUPPORT_MODEL', 'PKS_META_MODEL', 'PKS_CTR_DIGEST_MODEL',
                       'CTF_MODEL', 'PKS_CONTINUATION_FALLBACK_MODEL']:
        # Model selection for support/meta/etc
        try:
            all_models, _ = load_all_available_models()
            if 'alias1' in all_models:
                all_models.remove('alias1')
                all_models.insert(0, 'alias1')
            if not all_models:
                all_models = ['alias1', 'o3-mini', 'gpt-4o', 'gpt-4o-mini']
        except Exception:
            all_models = ['alias1', 'o3-mini', 'gpt-4o', 'gpt-4o-mini', 'claude-3.5-sonnet']

        def validate_model(text):
            if text in all_models or text == '':
                return True
            return tr("err_model_not_found").replace("{name}", text)

        result = questionary.autocomplete(
            f"{description}{display_current}\n"
            f"{tr('prompt_type_to_search_empty_default')}",
            choices=all_models,
            default=current_value if current_value else '',
            style=custom_style,
            validate=validate_model
        ).ask()

        return result

    elif var_name == 'OLLAMA_API_BASE':
        # Ollama API base URL
        ollama_choices = [
            questionary.Choice("http://localhost:11434/v1 (local)", "http://localhost:11434/v1"),
            questionary.Choice("http://127.0.0.1:11434/v1 (local)", "http://127.0.0.1:11434/v1"),
            questionary.Choice("https://ollama.com (cloud)", "https://ollama.com"),
            questionary.Choice(tr("choice_custom_url"), "custom"),
        ]

        result = questionary.select(
            f"{description}{display_current}",
            choices=ollama_choices,
            default=current_value if current_value else "http://localhost:11434/v1",
            style=custom_style
        ).ask()

        if result == "custom":
            result = questionary.text(
                tr("prompt_enter_ollama_base"),
                default=current_value if current_value else "http://localhost:11434/v1",
                style=custom_style
            ).ask()

        return result

    else:
        # Text input for other variables
        result = questionary.text(
            f"{description}{display_current}",
            default=current_value if current_value else (default_value or ''),
            style=custom_style
        ).ask()
        
        return result


class SettingsCommand(Command):
    """Interactive ``/settings`` (see module docstring)."""

    def __init__(self):
        super().__init__(
            name="/settings",
            description="Interactive .env editor, FAQ, API checks, and language",
            aliases=["/set"],
        )
        self._show_language_selector = True  # Show language selector on first run

    def handle_no_args(self) -> bool:
        """Handle the settings command with interactive interface.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear screen for full-screen mode
            console.clear()

            # Show language selector on first run
            if self._show_language_selector and len(SUPPORTED_LANGUAGES) > 1:
                console.print("\n")
                console.print(Panel(
                    f"[bold {_PKS_ACCENT}]{ICON_LANG}{tr('lang_selection_title')}[/bold {_PKS_ACCENT}]\n\n"
                    f"{tr('lang_selection_subtitle')}",
                    border_style=_PKS_ACCENT,
                    padding=(1, 2)
                ))
                console.print()

                lang = select_language()
                if lang is None:
                    console.print(f"[yellow]{tr('configuration_cancelled')}[/yellow]")
                    return True

                self._show_language_selector = False
                console.clear()

            # Get all available variables and categories
            all_vars = get_all_vars()
            categories_vars = get_variables_by_category()

            # Filter categories based on TUI/CLI mode
            if is_tui_mode():
                # Remove API Server category in TUI mode
                if 'API Server' in categories_vars:
                    del categories_vars['API Server']
            else:
                # Remove TUI Mode category in CLI mode
                if 'TUI Mode' in categories_vars:
                    del categories_vars['TUI Mode']

            # Flag to track if we need to redraw the header
            first_iteration = True

            # Main configuration loop
            while True:
                # Clear and redraw header for clean interface
                if first_iteration:
                    console.print("\n")
                else:
                    console.clear()
                    console.print("\n")

                # Detect mode for display
                mode_indicator = f"[{tr('mode_tui')}]" if is_tui_mode() else f"[{tr('mode_cli')}]"
                lang_indicator = f"[{get_current_language().upper()}]"

                n_vars = sum(len(v) for v in categories_vars.values())
                n_cats = len(categories_vars)
                footer = tr("settings_footer_hint").format(n_vars=n_vars, n_cats=n_cats)

                # Show header panel with mode and language indicators
                console.print(Panel(
                    f"[bold {_PKS_ACCENT}]{tr('title')}[/bold {_PKS_ACCENT}] {mode_indicator} {lang_indicator}\n\n"
                    f"{tr('subtitle')}\n\n"
                    f"[dim]{footer}[/dim]",
                    border_style=_PKS_ACCENT,
                    padding=(1, 2)
                ))
                console.print()

                first_iteration = False

                category_choices = []
                for cat in categories_vars.keys():
                    var_count = len(categories_vars[cat])
                    category_choices.append(
                        questionary.Choice(category_menu_choice_text(cat, var_count), cat)
                    )

                # Add FAQ & Troubleshooting option
                category_choices.append(questionary.Choice(ICON_FAQ + tr('cat_faq'), "__faq__"))

                # Add language change option
                category_choices.append(questionary.Choice(ICON_LANG + tr('change_language'), "__language__"))

                # Add exit option
                category_choices.append(questionary.Choice("[" + tr('exit') + "]", "__exit__"))
                
                category = questionary.select(
                    tr('select_category') + ":",
                    choices=category_choices,
                    style=custom_style
                ).ask()

                # Handle special options
                if not category or category == "__exit__":
                    console.print(f"[yellow]{tr('exit')}[/yellow]")
                    return True

                if category == "__faq__":
                    show_faq_menu()
                    continue

                if category == "__language__":
                    console.clear()
                    console.print("\n")
                    select_language()
                    continue
                
                # Inner loop for variables within a category
                while True:
                    # Refresh variables list to pick up any new additions
                    all_vars = get_all_vars()
                    categories_vars = get_variables_by_category()
                    
                    # Get variables in selected category
                    var_names = categories_vars.get(category, [])
                    
                    # Create choices with current values
                    var_choices = []
                    
                    for var_name in var_names:
                        if var_name not in all_vars:
                            continue  # Skip if variable definition not found
                        
                        var_info = all_vars[var_name]
                        current_value = os.getenv(var_name, var_info.get('default') or '')
                        
                        # Format display
                        display_value = _questionary_choice_value_display(var_name, current_value)
                        
                        choice_text = f"{var_name}: {display_value}"
                        var_choices.append(questionary.Choice(choice_text, var_name))
                    
                    if not var_choices and category != 'API Keys':
                        cat_label = (
                            tr(SETTINGS_CATEGORY_TO_I18N_KEY[category])
                            if category in SETTINGS_CATEGORY_TO_I18N_KEY
                            else category
                        )
                        console.print(
                            f"[yellow]{tr('no_vars_in_category').replace('{category}', cat_label)}[/yellow]"
                        )
                        break  # Go back to category selection
                    
                    # Add special options for API Keys category
                    if category == 'API Keys':
                        var_choices.append(questionary.Choice(tr("add_new_api_key_choice"), "__add__"))
                    
                    var_choices.append(questionary.Choice(tr("back_to_categories"), "__back__"))
                    
                    cat_label = (
                        tr(SETTINGS_CATEGORY_TO_I18N_KEY[category])
                        if category in SETTINGS_CATEGORY_TO_I18N_KEY
                        else category
                    )
                    # Let user select a variable to configure
                    selected_var = questionary.select(
                        tr("select_variable_from_category").replace("{category}", cat_label),
                        choices=var_choices,
                        style=custom_style
                    ).ask()
                    
                    # Handle cancellation (Ctrl+C or Esc)
                    if selected_var is None:
                        console.print(f"[yellow]{tr('configuration_cancelled')}[/yellow]")
                        return True
                    
                    # Handle back to categories
                    if selected_var == "__back__":
                        break  # Exit inner loop, go back to category selection
                    
                    # Handle add new API key
                    if selected_var == "__add__":
                        result = add_new_api_key()
                        if result:
                            key_name, key_value = result
                            # Add to .env file
                            update_env_file(key_name, key_value)
                            os.environ[key_name] = key_value
                            
                            console.print()
                            masked = '***' + key_value[-4:] if len(key_value) > 4 else '***'
                            console.print(Panel(
                                f"[bold {_PKS_ACCENT}]"
                                f"{tr('api_key_added_title').replace('{name}', key_name)}"
                                f"[/bold {_PKS_ACCENT}]\n\n"
                                f"{tr('api_key_added_body').replace('{masked}', f'[yellow]{masked}[/yellow]')}",
                                border_style=_PKS_ACCENT,
                                padding=(1, 2)
                            ))
                            console.print()
                        continue  # Refresh the menu
                    
                    # For API Keys, ask if user wants to edit or delete
                    if category == 'API Keys':
                        action = questionary.select(
                            tr("what_to_do_with_var").replace("{var}", selected_var),
                            choices=[
                                questionary.Choice(tr("action_edit_value"), "edit"),
                                questionary.Choice(tr("action_delete_key"), "delete"),
                                questionary.Choice(tr("cancel"), "cancel"),
                            ],
                            style=custom_style
                        ).ask()
                        
                        if action == "cancel" or action is None:
                            continue
                        
                        if action == "delete":
                            var_info = all_vars[selected_var]
                            current_value = os.getenv(selected_var, '')
                            if delete_api_key_interactive(selected_var, current_value):
                                continue  # Refresh the menu after deletion
                            else:
                                continue  # Deletion cancelled, go back to menu
                        
                        # If action == "edit", continue with normal flow below
                    
                    # Get variable info and prompt for new value
                    var_info = all_vars[selected_var]
                    current_value = os.getenv(selected_var, var_info.get('default') or '')
                    
                    new_value = prompt_for_variable(var_info, current_value)
                    
                    if new_value is None:
                        console.print(f"[yellow]{tr('configuration_cancelled')}[/yellow]")
                        continue  # Go back to menu instead of exiting
                    
                    # Update .env file and environment
                    update_env_file(selected_var, new_value)
                    os.environ[selected_var] = new_value
                    
                    console.print()
                    
                    # Masked display for sensitive values
                    if 'API_KEY' in selected_var or selected_var.endswith('_KEY'):
                        display_new = '***' + new_value[-4:] if len(new_value) > 4 else '***'
                    else:
                        display_new = new_value
                    
                    console.print(Panel(
                        f"[bold {_PKS_ACCENT}]"
                        f"{tr('variable_updated_title').replace('{name}', selected_var)}"
                        f"[/bold {_PKS_ACCENT}]\n\n"
                        f"{tr('variable_updated_body').replace('{value}', f'[yellow]{display_new}[/yellow]')}",
                        border_style=_PKS_ACCENT,
                        padding=(1, 2)
                    ))
                    console.print()
                    
                    # Ask if user wants to configure more variables in this category
                    cat_label2 = (
                        tr(SETTINGS_CATEGORY_TO_I18N_KEY[category])
                        if category in SETTINGS_CATEGORY_TO_I18N_KEY
                        else category
                    )
                    continue_config = questionary.confirm(
                        tr("configure_another_in_category").replace("{category}", cat_label2),
                        default=True,
                        style=custom_style
                    ).ask()
                    
                    if not continue_config:
                        break  # Exit inner loop, go back to category selection
            
        except KeyboardInterrupt:
            console.print(f"\n[yellow]{tr('configuration_cancelled')}[/yellow]")
        except Exception as e:
            console.print(f"\n[red]{tr('generic_error').replace('{message}', str(e))}[/red]")

        return True

    async def async_handle_no_args(self) -> bool:
        """Async version of handle_no_args for TUI mode compatibility.

        This method wraps the synchronous handler to work with async TUI event loops.
        For TUI mode, we need to handle the blocking questionary calls differently.

        Returns:
            True if successful, False otherwise
        """
        # In TUI mode, we need to run questionary in a thread pool
        # to avoid blocking the event loop
        if is_tui_mode():
            import concurrent.futures

            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, self.handle_no_args)
                return result
        else:
            # In CLI mode, just call the sync version
            return self.handle_no_args()

    def handle_tui_mode(self, args: Optional[List[str]] = None) -> bool:
        """Handle settings in TUI mode with non-blocking interface.

        Shows configuration status and instructions without using questionary.

        Args:
            args: Optional subcommand arguments

        Returns:
            True if successful
        """
        # Handle subcommands that don't need questionary
        if args:
            subcommand = args[0].lower()
            if subcommand in ['status', 'info']:
                if HAS_VALIDATION:
                    show_system_status()
                return True
            if subcommand in ['validate', 'check']:
                if HAS_VALIDATION:
                    show_api_key_validation()
                return True

        # Show current configuration overview
        console.print("\n")
        console.print(Panel(
            f"[bold {_PKS_ACCENT}]{tr('tui_settings_title')}[/bold {_PKS_ACCENT}] "
            f"[dim]({tr('mode_tui')})[/dim]\n\n"
            f"[yellow]{tr('tui_interactive_unavailable')}[/yellow]\n"
            f"{tr('tui_use_commands_below')}",
            border_style=_PKS_ACCENT,
            padding=(1, 2)
        ))
        console.print()

        # Show quick reference for common commands
        console.print(f"[bold]{tr('tui_quick_commands')}:[/bold]")
        console.print()

        commands = [
            ("/env list", tr("tui_cmd_list")),
            ("/env get <n>", tr("tui_cmd_get")),
            ("/env set <n> <VALUE>", tr("tui_cmd_set")),
            ("/model <name>", tr("tui_cmd_model")),
            ("/settings status", tr("tui_cmd_settings_status")),
            ("/settings validate", tr("tui_cmd_settings_validate")),
        ]

        for cmd, desc in commands:
            console.print(f"  [bold {_PKS_ACCENT}]{cmd:<30}[/bold {_PKS_ACCENT}] {desc}")

        console.print()

        # Show current key settings
        console.print(f"[bold]{tr('tui_current_configuration')}:[/bold]")
        console.print()

        key_vars = [
            ("PKS_MODEL", tr("tui_label_model")),
            ("PKS_AGENT_TYPE", tr("tui_label_agent_type")),
            ("PKS_DEBUG", tr("tui_label_debug")),
            ("PKS_STREAM", tr("tui_label_stream")),
            ("PKS_TOOL_STREAM", tr("tui_label_tool_stream")),
            ("PKS_COMPACTED_MEMORY", tr("tui_label_compacted_memory")),
            ("PKS_TRACING", tr("tui_label_tracing")),
        ]

        ns = tr("choice_value_not_set")
        for var, label in key_vars:
            value = os.getenv(var, ns)
            if len(value) > 40:
                value = value[:37] + "..."
            console.print(f"  {label:<20} [bold {_PKS_ACCENT}]{value}[/bold {_PKS_ACCENT}]")

        console.print()

        # Show API key status
        console.print(f"[bold]{tr('tui_api_keys_status')}:[/bold]")
        console.print()

        api_keys = [
            ("ALIAS_API_KEY", "Alias"),
            ("OPENAI_API_KEY", "OpenAI"),
            ("ANTHROPIC_API_KEY", "Anthropic"),
            ("OPENROUTER_API_KEY", "OpenRouter"),
            ("GOOGLE_API_KEY", "Google"),
        ]

        for var, label in api_keys:
            value = os.getenv(var, "")
            if value:
                masked = "***" + value[-4:] if len(value) > 4 else "***"
                console.print(
                    f"  {label:<20} [bold {_PKS_ACCENT}]{tr('tui_value_set')}[/bold {_PKS_ACCENT}] ({masked})"
                )
            else:
                console.print(f"  {label:<20} [red]{tr('tui_value_not_set')}[/red]")

        console.print()
        console.print(f"[dim]{tr('tui_tip_env')}[/dim]")
        console.print()

        return True

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the command with optional subcommands.

        Args:
            args: Optional list of arguments

        Returns:
            True if successful, False otherwise
        """
        # In TUI mode, use non-blocking interface
        if is_tui_mode():
            return self.handle_tui_mode(args)

        # CLI mode - use questionary-based interface
        if not args:
            return self.handle_no_args()

        # Handle subcommands
        subcommand = args[0].lower()

        if subcommand in ['faq', 'help', 'troubleshoot']:
            # Direct access to FAQ
            show_faq_menu()
            return True

        if subcommand in ['validate', 'check']:
            # Validate all API keys
            if HAS_VALIDATION:
                show_api_key_validation()
            else:
                console.print(f"[yellow]{tr('validation_module_unavailable')}[/yellow]")
            return True

        if subcommand in ['status', 'info']:
            # Show system status
            if HAS_VALIDATION:
                show_system_status()
            else:
                console.print(f"[yellow]{tr('status_module_unavailable')}[/yellow]")
            return True

        if subcommand in ['lang', 'language']:
            # Change language
            select_language()
            return True

        if subcommand in ['ollama', 'local']:
            # Ollama troubleshooting
            if HAS_VALIDATION:
                show_ollama_faq()
                console.print(f"\n[dim]{tr('press_enter_continue')}[/dim]")
                input()
            return True

        from pks.repl.commands.settings_cli_catalog import SETTINGS_CLI_SUBCOMMANDS

        console.print(f"[yellow]{tr('unknown_settings_subcommand').replace('{name}', subcommand)}[/yellow]")
        console.print(f"\n{tr('available_subcommands_header')}")
        for name, desc in SETTINGS_CLI_SUBCOMMANDS:
            console.print(f"  [bold {_PKS_ACCENT}]{name}[/bold {_PKS_ACCENT}] - {desc}")
        console.print(
            f"\nOr run [bold {_PKS_ACCENT}]/settings[/bold {_PKS_ACCENT}] "
            "without arguments for interactive mode."
        )
        return True


# =============================================================================
# Multi-terminal support for TUI
# =============================================================================

class TUISettingsState:
    """State management for settings across multiple TUI terminals.

    Each terminal can have its own language preference and configuration state.
    """

    def __init__(self):
        self._terminal_states: Dict[str, Dict[str, Any]] = {}

    def get_terminal_state(self, terminal_id: Optional[str] = None) -> Dict[str, Any]:
        """Get state for a specific terminal.

        Args:
            terminal_id: Terminal ID, or None for current terminal

        Returns:
            State dictionary for the terminal
        """
        tid = terminal_id or get_current_terminal_id() or "default"
        if tid not in self._terminal_states:
            self._terminal_states[tid] = {
                'language': get_current_language(),
                'show_language_selector': True,
                'last_category': None,
            }
        return self._terminal_states[tid]

    def set_terminal_language(self, language: str, terminal_id: Optional[str] = None):
        """Set language for a specific terminal.

        Args:
            language: Language code
            terminal_id: Terminal ID, or None for current terminal
        """
        state = self.get_terminal_state(terminal_id)
        state['language'] = language

    def get_terminal_language(self, terminal_id: Optional[str] = None) -> str:
        """Get language for a specific terminal.

        Args:
            terminal_id: Terminal ID, or None for current terminal

        Returns:
            Language code for the terminal
        """
        state = self.get_terminal_state(terminal_id)
        return state.get('language', DEFAULT_LANGUAGE)


# Global TUI state manager
_tui_state = TUISettingsState()


def get_tui_state() -> TUISettingsState:
    """Get the global TUI state manager."""
    return _tui_state


# Register the command
register_command(SettingsCommand())

