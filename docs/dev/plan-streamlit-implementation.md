# Implementation Guide: Streamlit UI for Agentic CBA Indicators

> **Purpose:** This document contains all information needed for an AI agent to implement the Streamlit UI feature. It is self-contained and prescriptive.

---

## Overview

| Property | Value |
|----------|-------|
| Feature | Streamlit Web UI |
| New File | `src/agentic_cba_indicators/ui.py` |
| Modified File | `pyproject.toml` |
| Entry Point | `agentic-cba-ui` |
| Dependencies | `streamlit>=1.40.0` |

---

## Step 1: Modify `pyproject.toml`

**File:** `pyproject.toml`

**Action:** Add `streamlit>=1.40.0` to the `dependencies` array and add a new script entry point.

### 1.1 Add Dependency

Locate the `dependencies` array and add `"streamlit>=1.40.0"` to it:

```toml
dependencies = [
    "chromadb>=1.4.1",
    "httpx>=0.28.1",
    "openpyxl>=3.1.5",
    "pandas>=2.3.3",
    "platformdirs>=4.0.0",
    "pymupdf>=1.26.7",
    "pyyaml>=6.0.3",
    "strands-agents[ollama]>=1.22.0",
    "streamlit>=1.40.0",
]
```

### 1.2 Add Script Entry Point

Locate the `[project.scripts]` section and add the new entry point:

```toml
[project.scripts]
agentic-cba = "agentic_cba_indicators.cli:main"
agentic-cba-ui = "agentic_cba_indicators.ui:main"
```

---

## Step 2: Create `src/agentic_cba_indicators/ui.py`

**File:** `src/agentic_cba_indicators/ui.py`

**Action:** Create this new file with the complete implementation below.

### Complete Implementation

```python
"""
Streamlit UI for Agentic CBA Indicators.

Provides:
- Chat interface with streaming responses
- PDF upload for context extraction
- Provider and tool set selection
- Markdown report export

Entry point: agentic-cba-ui
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generator

import fitz  # pymupdf
import streamlit as st
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from agentic_cba_indicators.config import (
    AgentConfig,
    ProviderConfig,
    create_model,
    get_agent_config,
    get_provider_config,
    load_config,
)
from agentic_cba_indicators.prompts import get_system_prompt
from agentic_cba_indicators.tools import FULL_TOOLS, REDUCED_TOOLS
from agentic_cba_indicators.tools._help import set_active_tools

if TYPE_CHECKING:
    pass


# =============================================================================
# PDF Extraction
# =============================================================================


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from PDF bytes using pymupdf.

    Args:
        pdf_bytes: Raw PDF file bytes from st.file_uploader

    Returns:
        Extracted text with page markers (e.g., "--- Page 1 ---")
    """
    text_parts: list[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
    return "\n\n".join(text_parts)


# =============================================================================
# Agent Factory
# =============================================================================


def create_agent_for_ui(
    provider_name: str,
    tool_set: str,
    conversation_window: int = 5,
) -> tuple[Agent, ProviderConfig, AgentConfig]:
    """Create agent with specified provider and tool set for UI use.

    Args:
        provider_name: Provider key from providers.yaml (e.g., "ollama", "anthropic")
        tool_set: Either "reduced" or "full"
        conversation_window: Number of conversation turns to retain (default 5)

    Returns:
        Tuple of (Agent, ProviderConfig, AgentConfig)

    Raises:
        ValueError: If provider_name is not found in config
        ImportError: If provider dependencies are not installed
    """
    config = load_config(None)
    config["active_provider"] = provider_name

    provider_config = get_provider_config(config)
    agent_config = get_agent_config(config)
    agent_config.tool_set = tool_set
    agent_config.conversation_window = conversation_window

    model = create_model(provider_config)

    conversation_manager = SlidingWindowConversationManager(
        window_size=agent_config.conversation_window,
    )

    tools = FULL_TOOLS if tool_set == "full" else REDUCED_TOOLS
    set_active_tools(tools)

    agent = Agent(
        model=model,
        system_prompt=get_system_prompt(),
        conversation_manager=conversation_manager,
        tools=tools,
    )

    return agent, provider_config, agent_config


# =============================================================================
# Response Streaming
# =============================================================================


def stream_agent_response(agent: Agent, prompt: str) -> Generator[str, None, None]:
    """Stream agent response text.

    Note: This implementation collects the full response and yields it.
    True token-by-token streaming would require callback handler integration.

    Args:
        agent: Configured Strands Agent instance
        prompt: User prompt (may include PDF context prefix)

    Yields:
        Response text chunks (currently yields full message at once)
    """
    result = agent(prompt)

    # Extract message text from AgentResult
    if hasattr(result, "message") and result.message:
        yield result.message
    elif hasattr(result, "content"):
        # Fallback: iterate content blocks
        for block in result.content:
            if hasattr(block, "text"):
                yield block.text


# =============================================================================
# Configuration Helpers
# =============================================================================


def get_available_providers() -> list[str]:
    """Get list of available provider names from config.

    Returns:
        List of provider keys (e.g., ["ollama", "anthropic", "openai"])
        Falls back to ["ollama"] if config cannot be loaded.
    """
    try:
        config = load_config(None)
        providers = config.get("providers", {})
        return list(providers.keys())
    except Exception:
        return ["ollama"]


def detect_report_in_response(text: str) -> str | None:
    """Detect if response contains a CBA Indicator Selection Report.

    Looks for the markdown header "# CBA Indicator Selection Report" and
    extracts from that point to the end of the text.

    Args:
        text: Full assistant response text

    Returns:
        Report markdown if detected, None otherwise
    """
    marker = "# CBA Indicator Selection Report"
    if marker in text:
        start_idx = text.find(marker)
        return text[start_idx:].strip()
    return None


# =============================================================================
# Session State Management
# =============================================================================


def init_session_state() -> None:
    """Initialize Streamlit session state variables.

    Session state keys:
    - messages: List[dict] - Chat history for UI display
    - agent: Agent | None - Strands Agent instance
    - provider_config: ProviderConfig | None - Current provider settings
    - pdf_context: str | None - Extracted PDF text
    - pdf_filename: str | None - Name of uploaded PDF
    - last_report: str | None - Most recent detected report
    - agent_ready: bool - Whether agent is initialized
    - current_provider: str | None - Tracks provider for change detection
    - current_tool_set: str | None - Tracks tool set for change detection
    """
    defaults = {
        "messages": [],
        "agent": None,
        "provider_config": None,
        "pdf_context": None,
        "pdf_filename": None,
        "last_report": None,
        "agent_ready": False,
        "current_provider": None,
        "current_tool_set": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =============================================================================
# Sidebar UI
# =============================================================================


def render_sidebar() -> tuple[str, str]:
    """Render sidebar with configuration options.

    Sidebar sections:
    1. Provider selection dropdown
    2. Tool set radio buttons
    3. PDF upload and management
    4. Report export download button
    5. Clear chat button

    Returns:
        Tuple of (selected_provider, selected_tool_set)
    """
    st.sidebar.title("⚙️ Configuration")

    # --- Provider Selection ---
    available_providers = get_available_providers()
    provider = st.sidebar.selectbox(
        "AI Provider",
        options=available_providers,
        index=0,
        help="Select the AI model provider",
    )

    # --- Tool Set Selection ---
    tool_set = st.sidebar.radio(
        "Tool Set",
        options=["reduced", "full"],
        index=0,
        format_func=lambda x: f"Reduced ({len(REDUCED_TOOLS)} tools)"
        if x == "reduced"
        else f"Full ({len(FULL_TOOLS)} tools)",
        help="Reduced set is faster; Full set includes all data tools",
    )

    st.sidebar.divider()

    # --- PDF Upload ---
    st.sidebar.subheader("📄 PDF Context")
    uploaded_file = st.sidebar.file_uploader(
        "Upload a PDF for context",
        type=["pdf"],
        help="The PDF text will be provided as context to the agent",
    )

    if uploaded_file is not None:
        # Only extract if new file or first upload
        if (
            st.session_state.pdf_context is None
            or st.session_state.get("pdf_filename") != uploaded_file.name
        ):
            with st.sidebar.status("Extracting PDF text..."):
                pdf_bytes = uploaded_file.read()
                pdf_text = extract_text_from_pdf(pdf_bytes)
                st.session_state.pdf_context = pdf_text
                st.session_state.pdf_filename = uploaded_file.name

            st.sidebar.success(f"✅ Loaded: {uploaded_file.name}")
            st.sidebar.caption(f"{len(pdf_text):,} characters extracted")

    # Show clear button if PDF is loaded
    if st.session_state.pdf_context:
        if st.sidebar.button("🗑️ Clear PDF Context"):
            st.session_state.pdf_context = None
            st.session_state.pdf_filename = None
            st.rerun()

    st.sidebar.divider()

    # --- Report Export ---
    st.sidebar.subheader("📥 Export")
    if st.session_state.last_report:
        st.sidebar.download_button(
            label="📄 Download Last Report",
            data=st.session_state.last_report,
            file_name="cba_indicator_report.md",
            mime="text/markdown",
        )
    else:
        st.sidebar.caption("No report generated yet")

    st.sidebar.divider()

    # --- Clear Chat ---
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.last_report = None
        st.session_state.agent = None
        st.session_state.agent_ready = False
        st.rerun()

    return provider, tool_set


# =============================================================================
# Main Application
# =============================================================================


def main() -> None:
    """Main Streamlit application entry point.

    Application flow:
    1. Configure page settings
    2. Initialize session state
    3. Render sidebar (returns provider/tool_set selections)
    4. Create/recreate agent if settings changed
    5. Display chat history
    6. Handle new user input
    7. Generate and display assistant response
    """
    # --- Page Configuration ---
    st.set_page_config(
        page_title="CBA Indicators Assistant",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Initialize State ---
    init_session_state()

    # --- Render Sidebar ---
    provider, tool_set = render_sidebar()

    # --- Main Header ---
    st.title("🌍 CBA Indicators Assistant")
    st.caption("Sustainable Agriculture Data & Indicator Selection")

    # --- Agent Initialization ---
    needs_new_agent = (
        st.session_state.agent is None
        or st.session_state.get("current_provider") != provider
        or st.session_state.get("current_tool_set") != tool_set
    )

    if needs_new_agent:
        with st.status("Initializing agent...", expanded=True) as status:
            try:
                agent, provider_config, agent_config = create_agent_for_ui(
                    provider_name=provider,
                    tool_set=tool_set,
                )
                st.session_state.agent = agent
                st.session_state.provider_config = provider_config
                st.session_state.current_provider = provider
                st.session_state.current_tool_set = tool_set
                st.session_state.agent_ready = True

                status.update(
                    label=f"✅ Ready ({provider_config.model_id})", state="complete"
                )
            except Exception as e:
                status.update(label=f"❌ Error: {e}", state="error")
                st.error(f"Failed to initialize agent: {e}")
                st.stop()

    # --- Provider Info Bar ---
    if st.session_state.provider_config:
        pc = st.session_state.provider_config
        tool_count = len(FULL_TOOLS) if tool_set == "full" else len(REDUCED_TOOLS)
        st.info(
            f"**Provider:** {pc.name} | **Model:** {pc.model_id} | **Tools:** {tool_count}"
        )

    # --- PDF Context Indicator ---
    if st.session_state.pdf_context:
        st.success(
            f"📄 PDF context loaded: {st.session_state.get('pdf_filename', 'document.pdf')}"
        )

    # --- Chat History ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Chat Input ---
    if prompt := st.chat_input("Ask about indicators, methods, climate, soil..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare full prompt with PDF context if available
        full_prompt = prompt
        if st.session_state.pdf_context:
            full_prompt = (
                f"I have uploaded a PDF document. Here is the extracted text:\n\n"
                f"--- PDF CONTENT START ---\n"
                f"{st.session_state.pdf_context}\n"
                f"--- PDF CONTENT END ---\n\n"
                f"User question: {prompt}"
            )

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response_text = ""
                    for chunk in stream_agent_response(
                        st.session_state.agent, full_prompt
                    ):
                        response_text += chunk

                    st.markdown(response_text)

                    # Check for report and save for export
                    report = detect_report_in_response(response_text)
                    if report:
                        st.session_state.last_report = report
                        st.toast("📄 Report detected! Download available in sidebar.")

                    # Add assistant message to history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text}
                    )

                except Exception as e:
                    error_msg = f"Error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )


if __name__ == "__main__":
    main()
```

---

## Step 3: Verify Installation

After creating/modifying the files, run these commands:

```bash
# Sync dependencies (installs streamlit)
uv sync

# Verify entry point is registered
uv run agentic-cba-ui --help
# Expected: Streamlit help output or app launch

# Alternative: Run directly with streamlit
uv run streamlit run src/agentic_cba_indicators/ui.py
```

---

## Step 4: Verification Checklist

### 4.1 Startup Verification

| Check | Command | Expected |
|-------|---------|----------|
| Dependencies installed | `uv sync` | No errors, streamlit in .venv |
| Entry point works | `agentic-cba-ui` | Browser opens with UI |
| Direct run works | `streamlit run src/agentic_cba_indicators/ui.py` | Browser opens with UI |

### 4.2 UI Component Verification

| Component | Location | Expected Behavior |
|-----------|----------|-------------------|
| Title | Main area top | "🌍 CBA Indicators Assistant" |
| Subtitle | Below title | "Sustainable Agriculture Data & Indicator Selection" |
| Provider dropdown | Sidebar | Shows available providers from config |
| Tool set radio | Sidebar | "Reduced (N tools)" / "Full (N tools)" |
| PDF uploader | Sidebar | Accepts .pdf files only |
| Export button | Sidebar | Disabled until report generated |
| Clear chat button | Sidebar | Resets messages and agent |
| Chat input | Bottom of main | Placeholder text visible |
| Provider info bar | Main area | Shows provider, model, tool count |

### 4.3 Functional Verification

| Test | Steps | Expected |
|------|-------|----------|
| Basic chat | Type "Hello", press Enter | User message appears, assistant responds |
| PDF upload | Upload any PDF | "✅ Loaded: filename.pdf" + character count |
| PDF context | Upload PDF, ask about it | Agent references PDF content in response |
| Clear PDF | Click "Clear PDF Context" | PDF indicator disappears |
| Provider switch | Change dropdown | "Initializing agent..." status, then new provider info |
| Tool set switch | Toggle radio | Agent recreates with new tool count |
| Report export | Ask for indicator report | Toast notification, download button enabled |
| Clear chat | Click "Clear Chat History" | All messages removed, agent reset |

---

## File Structure After Implementation

```
src/agentic_cba_indicators/
├── __init__.py
├── cli.py              # Existing CLI entry point
├── ui.py               # NEW: Streamlit UI entry point
├── config/
│   └── ...
├── prompts/
│   └── ...
└── tools/
    └── ...
```

---

## Import Dependencies Map

The `ui.py` file imports from these existing modules:

| Import | Source | Purpose |
|--------|--------|---------|
| `Agent` | `strands` | Core agent class |
| `SlidingWindowConversationManager` | `strands.agent.conversation_manager` | Conversation memory |
| `AgentConfig` | `agentic_cba_indicators.config` | Agent configuration dataclass |
| `ProviderConfig` | `agentic_cba_indicators.config` | Provider configuration dataclass |
| `create_model` | `agentic_cba_indicators.config` | Model factory function |
| `get_agent_config` | `agentic_cba_indicators.config` | Config loader |
| `get_provider_config` | `agentic_cba_indicators.config` | Config loader |
| `load_config` | `agentic_cba_indicators.config` | YAML config loader |
| `get_system_prompt` | `agentic_cba_indicators.prompts` | System prompt loader |
| `FULL_TOOLS` | `agentic_cba_indicators.tools` | Full tool set list |
| `REDUCED_TOOLS` | `agentic_cba_indicators.tools` | Reduced tool set list |
| `set_active_tools` | `agentic_cba_indicators.tools._help` | Tool registry for help system |
| `fitz` | `pymupdf` | PDF text extraction |
| `streamlit` | `streamlit` | Web UI framework |

---

## Error Handling

The implementation handles these error cases:

| Error | Location | Handling |
|-------|----------|----------|
| Config not found | `create_agent_for_ui()` | Caught by `st.status()`, shows error state |
| Provider not available | `create_agent_for_ui()` | Shows "❌ Error: {message}" in status |
| Missing provider deps | `create_model()` | ImportError shown in status |
| PDF extraction fails | `extract_text_from_pdf()` | Exception propagates to sidebar status |
| Agent invocation fails | `stream_agent_response()` | Caught in chat handler, shown as error message |
| Network timeout | Agent call | Caught, shown as assistant error message |

---

## Session State Schema

```python
st.session_state = {
    # Chat display
    "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
    ],

    # Agent instance (persists across reruns)
    "agent": Agent | None,

    # Current configuration
    "provider_config": ProviderConfig | None,
    "current_provider": str | None,      # e.g., "ollama"
    "current_tool_set": str | None,      # "reduced" or "full"
    "agent_ready": bool,

    # PDF context
    "pdf_context": str | None,           # Extracted text
    "pdf_filename": str | None,          # Original filename

    # Report export
    "last_report": str | None,           # Markdown content
}
```

---

## Testing Commands

```bash
# Run with default provider (ollama)
agentic-cba-ui

# Run on specific port
streamlit run src/agentic_cba_indicators/ui.py --server.port 8502

# Run with browser auto-open disabled
streamlit run src/agentic_cba_indicators/ui.py --server.headless true

# Check for import errors without starting server
python -c "from agentic_cba_indicators.ui import main; print('OK')"
```

---

## Acceptance Criteria Checklist

- [ ] `pyproject.toml` has `streamlit>=1.40.0` in dependencies
- [ ] `pyproject.toml` has `agentic-cba-ui` script entry point
- [ ] `src/agentic_cba_indicators/ui.py` exists and is valid Python
- [ ] `uv sync` completes without errors
- [ ] `agentic-cba-ui` launches Streamlit app in browser
- [ ] Sidebar shows provider dropdown with available providers
- [ ] Sidebar shows tool set radio with correct tool counts
- [ ] PDF upload extracts text and shows character count
- [ ] Chat input accepts messages and displays them
- [ ] Agent responds to messages (requires Ollama or other provider running)
- [ ] Report detection triggers toast and enables download button
- [ ] Clear chat resets all state
- [ ] Provider/tool set changes recreate agent with status indicator
