"""Tools for the shared cross-agent blackboard.

``note_finding`` and ``set_flag`` let an agent push a *conclusion* onto the shared board
(commands are auto-logged already). Everything on the board is injected into every agent's
system prompt as ``<shared_findings>``, so agents keep a unified memory across handoffs.
"""

from pks.sdk.agents import function_tool
from pks.util import blackboard as _bb


@function_tool
def note_finding(kind: str, content: str) -> str:
    """Record an important finding/conclusion on the SHARED cross-agent board.

    Use this whenever you learn something other PKS agents should know: a working
    credential, an extracted artifact path, a confirmed vulnerability, a ruled-out
    dead-end, the challenge category, a partial flag, etc. It survives handoffs and
    interrupts and is shown to every agent, so nobody repeats your work.

    Args:
        kind: short category tag, e.g. "finding", "hypothesis", "cred", "artifact", "dead-end".
        content: the concrete fact/conclusion, in one or two sentences.
    """
    content = (content or "").strip()
    if not content:
        return "Nothing to record (empty content)."
    _bb.add(kind or "finding", content, agent="")
    return f"Recorded on shared board: [{kind}] {content[:100]}"


@function_tool
def set_flag(flag: str) -> str:
    """Record a CONFIRMED flag on the shared board so every agent knows the challenge is solved.

    Args:
        flag: the exact, validated flag string (e.g. ``picoCTF{...}``).
    """
    flag = (flag or "").strip()
    if not flag:
        return "No flag provided."
    _bb.add("FLAG", flag, agent="")
    return f"FLAG recorded on shared board: {flag}"
