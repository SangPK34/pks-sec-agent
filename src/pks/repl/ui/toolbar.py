"""
Module for the PKS REPL toolbar functionality.
"""
import datetime
import os
import platform
import shutil
import socket
import subprocess
import threading
from functools import lru_cache

import requests  # pylint: disable=import-error
from prompt_toolkit.formatted_text import HTML  # pylint: disable=import-error

from pks.config import compacted_memory_env_enabled

# Variable to track when to refresh the toolbar
toolbar_last_refresh = [datetime.datetime.now()]

# Cache for toolbar data
toolbar_cache = {
    'html': "",
    'last_update': datetime.datetime.now(),
    'refresh_interval': 5,  # Refresh every 5 seconds
    'context_warning_shown': False,  # Track if we've shown context warning
    'context_env': None,
}

# Cache for system information that rarely changes
system_info = {
    'ip_address': None,
    'os_name': None,
    'os_version': None
}


@lru_cache(maxsize=1)
def get_system_info():
    """Get system information that rarely changes (cached)."""
    if not system_info['ip_address']:
        try:
            # Get local IP addresses
            hostname = socket.gethostname()
            system_info['ip_address'] = socket.gethostbyname(hostname)
            
            # Get OS information
            system_info['os_name'] = platform.system()
            system_info['os_version'] = platform.release()
        except Exception:  # pylint: disable=broad-except
            system_info['ip_address'] = "unknown"
            system_info['os_name'] = "unknown"
            system_info['os_version'] = "unknown"
    
    return system_info


def get_terminal_width():
    """Get the terminal width."""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80  # Default width


def _format_context_usage(raw_value: str) -> str:
    try:
        context_pct = max(0.0, float(raw_value or 0)) * 100
    except ValueError:
        context_pct = 0.0
    if 0 < context_pct < 0.1:
        return "<0.1%"
    return f"{context_pct:.1f}%"


def _refresh_cached_context(raw_value: str) -> None:
    """Update only the context field without rerunning slow environment probes."""
    html = toolbar_cache.get('html')
    value = getattr(html, 'value', '') if html else ''
    prefix = "<ansicyan>Context:</ansicyan> <ansigreen>"
    start = value.find(prefix)
    if start < 0:
        return
    value_start = start + len(prefix)
    value_end = value.find("</ansigreen>", value_start)
    if value_end < 0:
        return
    toolbar_cache['html'] = HTML(
        value[:value_start]
        + _format_context_usage(raw_value)
        + value[value_end:]
    )
    toolbar_cache['context_env'] = raw_value


def update_toolbar_in_background():
    """Update the toolbar cache in a background thread."""
    try:
        # Get system info (cached)
        sys_info = get_system_info()
        ip_address = sys_info['ip_address']
        os_name = sys_info['os_name']
        os_version = sys_info['os_version']
       
        # Get the current workspace and base directory
        workspace_name = os.getenv("PKS_WORKSPACE")
        base_dir = os.getenv("PKS_WORKSPACE_DIR", "workspaces")

        # Construct the workspace path 
        standard_path = os.path.join(base_dir, workspace_name) if workspace_name else ""
        workspace_path = ""
        if workspace_name:
            if os.path.isdir(standard_path):
                workspace_path = standard_path
            elif os.path.isdir(workspace_name):
                workspace_path = os.path.abspath(workspace_name)
            else:
                workspace_path = standard_path
        
        # Get current active container info
        container_id = os.getenv("PKS_ACTIVE_CONTAINER")
        if container_id:
            active_env_name, active_env_icon, active_env_color = get_container_info(container_id)
        else:
            active_env_name, active_env_icon, active_env_color = "Host System", "💻", "ansiblue"


        # Get Ollama information
        ollama_status = "unavailable"
        try:
            # Get Ollama models with a short timeout to prevent hanging
            from pks.util import get_ollama_api_base
            api_base = get_ollama_api_base()
            
            # Add authentication headers for Ollama Cloud if using OPENAI_BASE_URL
            headers = {}
            if "ollama.com" in api_base:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
            
            response = requests.get(
                f"{api_base.replace('/v1', '')}/api/tags",
                headers=headers,
                timeout=0.5)

            if response.status_code == 200:
                data = response.json()
                if 'models' in data:
                    ollama_models = len(data['models'])
                else:
                    # Fallback for older Ollama versions
                    ollama_models = len(data.get('items', []))
                ollama_status = f"{ollama_models} models"
        except Exception:  # pylint: disable=broad-except
            # Silently fail if Ollama is not available
            ollama_status = "unavailable"

        # Get current time for the toolbar refresh indicator
        current_time = datetime.datetime.now().strftime("%H:%M")

        # Add timezone information to show it's local time
        timezone_name = datetime.datetime.now().astimezone().tzname()
        current_time_with_tz = f"{current_time} {timezone_name}"

        # Auto-compact: prefer centralized config (matches auto_compactor / get_config)
        try:
            from pks.config import get_config

            auto_compact = bool(get_config().auto_compact)
        except Exception:  # pylint: disable=broad-except
            auto_compact = os.getenv("PKS_AUTO_COMPACT", "true").lower() == "true"
        
        try:
            context_usage = float(os.getenv("PKS_CONTEXT_USAGE", "0") or 0)
        except ValueError:
            context_usage = 0.0
            
        # Determine auto-compact display based on usage
        if auto_compact:
            if context_usage >= 0.8:  # Above 80%
                auto_compact_str = "⚠️"
                auto_compact_color = "ansired"  # Red for warning
                # Show warning if not already shown
                if not toolbar_cache.get('context_warning_shown', False) and context_usage > 0:
                    toolbar_cache['context_warning_shown'] = True
            elif context_usage >= 0.6:  # Above 60%
                auto_compact_str = "✓"
                auto_compact_color = "ansiyellow"  # Yellow for caution
            else:
                auto_compact_str = "✓"
                auto_compact_color = "ansigreen"
        else:
            if context_usage >= 0.8:  # Warning even when disabled
                auto_compact_str = "✗"
                auto_compact_color = "ansired"
            else:
                auto_compact_str = "✗"
                auto_compact_color = "ansired"

        # Get compacted-memory injection status (/compact summaries)
        memory_enabled = compacted_memory_env_enabled()
        memory_str = "✓" if memory_enabled else "✗"
        memory_color = "ansigreen" if memory_enabled else "ansigray"

        # Get streaming status
        streaming_enabled = os.getenv('PKS_STREAM', 'false').lower() == 'true'
        stream_str = "✓" if streaming_enabled else "✗"
        stream_color = "ansigreen" if streaming_enabled else "ansigray"

        # Get parallel agent count
        parallel_count = os.getenv('PKS_PARALLEL', '1')
        parallel_color = "ansigreen" if int(parallel_count) > 1 else "ansigray"

        # Get tracing status
        tracing_enabled = os.getenv('PKS_TRACING', 'false').lower() == 'true'
        trace_str = "✓" if tracing_enabled else "✗"
        trace_color = "ansigreen" if tracing_enabled else "ansigray"

        # Build context string
        context_raw = os.getenv("PKS_CONTEXT_USAGE", "0")
        context_str = _format_context_usage(context_raw)
        
        # Build toolbar (same for all sizes as user requested a specific format)
        toolbar_cache['html'] = HTML(
            f"<ansiyellow>Model:</ansiyellow> <ansigreen>{os.getenv('PKS_MODEL', 'default')}</ansigreen> | "
            f"<ansicyan>Agent:</ansicyan> <ansigreen>{os.getenv('PKS_AGENT_TYPE', 'root_agent')}</ansigreen> | "
            f"<ansicyan>Context:</ansicyan> <ansigreen>{context_str}</ansigreen> | "
            f"<ansicyan>AutoCompact:</ansicyan> <{auto_compact_color}>{auto_compact_str}</{auto_compact_color}> | "
            f"<ansicyan>Memory:</ansicyan> <{memory_color}>{memory_str}</{memory_color}> | "
            f"<ansicyan>Stream:</ansicyan> <{stream_color}>{stream_str}</{stream_color}> | "
            f"<ansicyan>Parallel:</ansicyan> <{parallel_color}>{parallel_count}</{parallel_color}> | "
            f"<ansicyan>Trace:</ansicyan> <{trace_color}>{trace_str}</{trace_color}> | "
            f"<ansiyellow>Turns:</ansiyellow> <ansiblue>{os.getenv('PKS_MAX_TURNS', 'inf')}</ansiblue>"
        )
        toolbar_cache['last_update'] = datetime.datetime.now()
        toolbar_cache['context_env'] = context_raw
    except Exception:  # pylint: disable=broad-except
        # If there's an error, set a simple toolbar
        toolbar_cache['html'] = HTML(
            f"<ansigray>{datetime.datetime.now().strftime('%H:%M')}</ansigray>"
        )


def get_bottom_toolbar():
    """Get the bottom toolbar with system information (cached)."""
    # If the toolbar is empty, initialize it
    if not toolbar_cache['html']:
        # Create a simple initial toolbar while the full one loads
        current_time = datetime.datetime.now().strftime("%H:%M")
        timezone_name = datetime.datetime.now().astimezone().tzname()
        toolbar_cache['html'] = HTML(
            f"<ansigray>Loading system information... {current_time} {timezone_name}</ansigray>"
        )
        # Start background update
        threading.Thread(
            target=update_toolbar_in_background,
            daemon=True
        ).start()
    
    # Return the cached toolbar HTML
    return toolbar_cache['html']


def get_toolbar_with_refresh():
    """Get toolbar with refresh control."""
    context_raw = os.getenv("PKS_CONTEXT_USAGE", "0")
    if toolbar_cache.get('context_env') != context_raw:
        _refresh_cached_context(context_raw)

    now = datetime.datetime.now()
    seconds_elapsed = (now - toolbar_cache['last_update']).total_seconds()
    
    # Check if we need to refresh the toolbar
    if seconds_elapsed >= toolbar_cache['refresh_interval']:
        # Start a background thread to update the toolbar
        threading.Thread(
            target=update_toolbar_in_background,
            daemon=True
        ).start()
    
    # Always return the cached version immediately
    return get_bottom_toolbar()


def set_context_usage(usage_percentage: float):
    """Set the current context usage percentage (called from openai_chatcompletions.py)."""
    os.environ['PKS_CONTEXT_USAGE'] = str(usage_percentage)
    # Reset warning flag if usage drops below threshold
    if usage_percentage < 0.8:
        toolbar_cache['context_warning_shown'] = False


# Initialize the toolbar on module import
threading.Thread(
    target=update_toolbar_in_background,
    daemon=True
).start()

def get_container_info(container_id):
    """
    Retrieves information about a Docker container by its ID.

    Args:
        container_id (str): The ID of the Docker container.

    Returns:
        tuple: A tuple containing:
            - container_name (str): The image name (with "(stopped)" suffix if not running).
            - icon (str): An emoji representing the container type or status.
            - color (str): A string representing the display color (e.g., for UI rendering).
    """
    try:
        # Get the container's image name.
        image = subprocess.run(
            ["docker", "inspect", "--format", "{{.Config.Image}}", container_id],
            capture_output=True, text=True
        ).stdout.strip()

        # Determine the appropriate icon and color based on the image type.
        icon = "🐳"
        color = "ansigreen"

        if "kali" in image.lower() or "parrot" in image.lower():
            icon = "🔒"
        elif "pks" in image.lower():
            icon = "⭐"

        # Check whether the container is currently running.
        running = subprocess.run(
            ["docker", "ps", "--filter", f"id={container_id}", "--format", "{{.Status}}"],
            capture_output=True, text=True
        ).stdout.strip()

        if not running:
            image += " (stopped)"
            color = "ansiyellow"

        return image, icon, color

    except Exception:
        return f"Container {container_id[:12]}", "🐳", "ansiyellow"
