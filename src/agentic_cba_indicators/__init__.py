"""
Agentic CBA Indicators - A conversational AI chatbot with multi-provider support.

This package provides a CLI chatbot that queries weather, climate,
socio-economic data, and CBA ME Indicators using the Strands Agents SDK.
"""

from __future__ import annotations

__version__ = "0.2.0"
__all__ = [
    "__version__",
    "get_config_dir",
    "get_data_dir",
    "get_kb_path",
]

from agentic_cba_indicators.paths import get_config_dir, get_data_dir, get_kb_path
