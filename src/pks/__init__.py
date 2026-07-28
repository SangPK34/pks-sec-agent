"""
A library to build Bug Bounty-level grade Cybersecurity AIs (PKSs).
"""


def is_pentestperf_available():
    """
    Check if pksbench (formerly pentestperf) is available
    """
    try:
        from pks.pksbench.ctf import CTF  # pylint: disable=import-error,import-outside-toplevel,unused-import  # noqa: E501,F401
    except ImportError:
        return False
    return True
