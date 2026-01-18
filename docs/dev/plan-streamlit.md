## Executive Summary

Add a Streamlit web interface that provides:
- **PDF Upload** — Extract text from uploaded PDFs and inject as conversation context
- **Chat Interface** — Real-time streaming chat backed by the existing Strands agent
- **Report Export** — One-click download of generated CBA Indicator Selection Reports as Markdown

This enables non-technical users to interact with the CBA Indicators knowledge base through a browser-based UI, without requiring CLI familiarity.

---

## Problem Statement

The current CLI interface (`agentic-cba`) works well for developers but presents barriers for:

1. **Non-technical users** — Unfamiliar with terminal usage
2. **Document-based workflows** — Users who want to upload project PDFs and ask questions about them
3. **Report sharing** — No easy way to export and share generated indicator reports
4. **Visual feedback** — CLI streaming doesn't show tool invocations visually

---

## Proposed Solution

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Web Framework | [Streamlit](https://streamlit.io) | ≥1.40.0 | Rapid Python-based UI, built-in chat components |
| PDF Extraction | pymupdf (fitz) | ≥1.26.7 | Already a dependency, fast text extraction |
| AI Backend | Strands Agents SDK | ≥1.22.0 | Existing agent infrastructure |
| State Management | `st.session_state` | — | Streamlit's built-in persistence |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit UI (ui.py)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────────────────────────┐  │
│  │   Sidebar   │  │              Main Area                   │  │
│  │             │  │  ┌────────────────────────────────────┐  │  │
│  │ • Provider  │  │  │         Chat History               │  │  │
│  │ • Tool Set  │  │  │  ┌──────────────────────────────┐  │  │  │
│  │ • PDF Upload│  │  │  │ User: "Find soil indicators" │  │  │  │
│  │ • Export    │  │  │  └──────────────────────────────┘  │  │  │
│  │ • Clear     │  │  │  ┌──────────────────────────────┐  │  │  │
│  │             │  │  │  │ Assistant: "Found 15..."     │  │  │  │
│  └─────────────┘  │  │  └──────────────────────────────┘  │  │  │
│                   │  └────────────────────────────────────┘  │  │
│                   │  ┌────────────────────────────────────┐  │  │
│                   │  │       st.chat_input()              │  │  │
│                   │  └────────────────────────────────────┘  │  │
│                   └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Strands Agent                                │
│  • SlidingWindowConversationManager (window_size=5)             │
│  • Callback handler for streaming                               │
│  • Tools: REDUCED_TOOLS (24) or FULL_TOOLS (62)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Requirements

### FR-1: Chat Interface with Streaming

**Description:** Users can type messages and receive real-time streaming responses from the agent.

**Streamlit Components:**
- `st.chat_input()` — Captures user messages ([docs](https://docs.streamlit.io/develop/api-reference/chat/st.chat_input))
- `st.chat_message()` — Displays messages with role-based avatars ([docs](https://docs.streamlit.io/develop/api-reference/chat/st.chat_message))
- `st.write_stream()` — Renders streaming content with typewriter effect ([docs](https://docs.streamlit.io/develop/api-reference/write-magic/st.write_stream))

**Strands Integration:**
The Strands SDK supports two streaming patterns:

1. **Callback Handler** (synchronous) — Receives events via `callback_handler` parameter
2. **Async Iterator** — `agent.stream_async(prompt)` yields events

For Streamlit (which is synchronous by default), we use the **callback handler pattern**:

```python
# Strands callback handler receives these event keys:
# - data: str           # Text chunk from model output
# - complete: bool      # Whether this is the final chunk
# - current_tool_use: dict  # Tool being invoked {name, toolUseId, input}
# - reasoningText: str  # Reasoning text (if enabled)
```

**Implementation Approach:**

Since `st.write_stream()` expects a generator, we'll collect the final response and render it. True token-by-token streaming requires careful handling of Streamlit's rerun model.

**Option A: Spinner-based (simpler)**
```python
with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        result = agent(prompt)  # Blocks until complete
        st.markdown(result.message)
```

**Option B: Custom streaming callback (advanced)**
```python
def create_streaming_callback():
    """Create callback that accumulates text for st.write_stream."""
    chunks = []

    def handler(**kwargs):
        if "data" in kwargs:
            chunks.append(kwargs["data"])

    return handler, chunks

callback, chunks = create_streaming_callback()
agent = Agent(..., callback_handler=callback)

# Later, yield chunks to st.write_stream
def stream_response():
    for chunk in chunks:
        yield chunk

with st.chat_message("assistant"):
    response = st.write_stream(stream_response())
```

**Acceptance Criteria:**
- [ ] User input captured via `st.chat_input()`
- [ ] Messages display with appropriate role avatars
- [ ] Assistant responses stream or display progressively
- [ ] Chat history persists across page reruns

---

### FR-2: PDF Upload and Context Injection

**Description:** Users can upload PDF files. The extracted text is prepended to prompts as context.

**Components:**
- `st.file_uploader()` — File upload widget with `type=["pdf"]`
- `pymupdf (fitz)` — Text extraction from PDF bytes

**Text Extraction:**
```python
import fitz  # pymupdf

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from PDF bytes using pymupdf."""
    text_parts: list[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
    return "\n\n".join(text_parts)
```

**Context Injection Pattern:**
```python
full_prompt = prompt
if st.session_state.pdf_context:
    full_prompt = (
        f"I have uploaded a PDF document. Here is the extracted text:\n\n"
        f"--- PDF CONTENT START ---\n"
        f"{st.session_state.pdf_context}\n"
        f"--- PDF CONTENT END ---\n\n"
        f"User question: {prompt}"
    )
```

**Considerations:**
- Large PDFs may exceed context limits — consider chunking or summarization
- Store extracted text in `st.session_state.pdf_context` to avoid re-extraction
- Show character count to user: `st.caption(f"{len(pdf_text):,} characters extracted")`

**Acceptance Criteria:**
- [ ] PDF upload via sidebar
- [ ] Text extraction with page markers
- [ ] Visual feedback showing loaded filename and character count
- [ ] Clear PDF context button
- [ ] Context injected into prompts transparently

---

### FR-3: Provider and Tool Set Selection

**Description:** Users can switch between AI providers (Ollama, Anthropic, etc.) and tool sets (reduced/full).

**Components:**
- `st.selectbox()` — Provider dropdown populated from `providers.yaml`
- `st.radio()` — Tool set toggle (reduced vs full)

**Provider Detection:**
```python
def get_available_providers() -> list[str]:
    """Get list of available provider names from config."""
    try:
        config = load_config(None)
        providers = config.get("providers", {})
        return list(providers.keys())
    except Exception:
        return ["ollama"]  # Fallback
```

**Agent Recreation:**
When provider or tool set changes, recreate the agent:

```python
needs_new_agent = (
    st.session_state.agent is None
    or st.session_state.get("current_provider") != provider
    or st.session_state.get("current_tool_set") != tool_set
)

if needs_new_agent:
    with st.status("Initializing agent...", expanded=True) as status:
        agent, provider_config, agent_config = create_agent_for_ui(
            provider_name=provider,
            tool_set=tool_set,
        )
        st.session_state.agent = agent
        status.update(label=f"✅ Ready ({provider_config.model_id})", state="complete")
```

**Acceptance Criteria:**
- [ ] Provider dropdown shows all configured providers
- [ ] Tool set radio with clear labels (e.g., "Reduced (24 tools)")
- [ ] Agent recreated when settings change
- [ ] Loading status during agent initialization

---

### FR-4: Report Export

**Description:** When the agent generates a CBA Indicator Selection Report, enable one-click download.

**Report Detection:**
```python
def detect_report_in_response(text: str) -> str | None:
    """Detect if response contains a CBA Indicator Selection Report."""
    if "# CBA Indicator Selection Report" in text:
        start_idx = text.find("# CBA Indicator Selection Report")
        return text[start_idx:].strip()
    return None
```

**Download Button:**
```python
if st.session_state.last_report:
    st.sidebar.download_button(
        label="📄 Download Last Report",
        data=st.session_state.last_report,
        file_name="cba_indicator_report.md",
        mime="text/markdown",
    )
```

**User Notification:**
```python
report = detect_report_in_response(response_text)
if report:
    st.session_state.last_report = report
    st.toast("📄 Report detected! Download available in sidebar.")
```

**Acceptance Criteria:**
- [ ] Reports auto-detected by header pattern
- [ ] Download button appears in sidebar when report available
- [ ] Toast notification alerts user
- [ ] Downloaded file is valid Markdown

---

### FR-5: Session State Management

**Description:** Properly manage conversation state across Streamlit reruns.

**Streamlit Session State Basics:**
```python
# Initialize defaults
if "messages" not in st.session_state:
    st.session_state.messages = []

# Access/modify
st.session_state.messages.append({"role": "user", "content": prompt})

# Force re-render
st.rerun()
```

**State Schema:**
```python
def init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    defaults = {
        "messages": [],           # Chat history for display
        "agent": None,            # Strands Agent instance
        "provider_config": None,  # Current provider config
        "pdf_context": None,      # Extracted PDF text
        "pdf_filename": None,     # Uploaded PDF filename
        "last_report": None,      # Most recent detected report
        "agent_ready": False,     # Agent initialization flag
        "current_provider": None, # Tracks provider for change detection
        "current_tool_set": None, # Tracks tool set for change detection
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
```

**Design Decision: Dual State Management**

| State Layer | Purpose | Managed By |
|-------------|---------|------------|
| `st.session_state.messages` | UI display history | Streamlit |
| `agent.conversation_manager` | Full context with tool calls | Strands SDK |

The Strands `SlidingWindowConversationManager` maintains the conversation context internally (including tool calls). The UI only stores simplified `{role, content}` dicts for display.

**Acceptance Criteria:**
- [ ] State persists across reruns
- [ ] Clear chat resets both UI and agent state
- [ ] Provider changes preserve state appropriately
- [ ] No state leakage between sessions

---

## Implementation Plan

### Phase 1: Core Structure

**File:** `src/agentic_cba_indicators/ui.py`

**Dependencies:** Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps ...
    "streamlit>=1.40.0",
]

[project.scripts]
agentic-cba = "agentic_cba_indicators.cli:main"
agentic-cba-ui = "agentic_cba_indicators.ui:main"
```

### Phase 2: Implementation

```python
"""
Streamlit UI for Agentic CBA Indicators.

Provides:
- Chat interface with streaming responses
- PDF upload for context extraction
- Provider and tool set selection
- Markdown report export
"""

from __future__ import annotations

import re
from typing import Generator

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


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from PDF bytes using pymupdf."""
    text_parts: list[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
    return "\n\n".join(text_parts)


def create_agent_for_ui(
    provider_name: str,
    tool_set: str,
    conversation_window: int = 5,
) -> tuple[Agent, ProviderConfig, AgentConfig]:
    """Create agent with specified provider and tool set for UI use."""
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


def stream_agent_response(agent: Agent, prompt: str) -> Generator[str, None, None]:
    """Stream agent response. Yields the final message."""
    result = agent(prompt)

    if hasattr(result, "message") and result.message:
        yield result.message
    elif hasattr(result, "content"):
        for block in result.content:
            if hasattr(block, "text"):
                yield block.text


def get_available_providers() -> list[str]:
    """Get list of available provider names from config."""
    try:
        config = load_config(None)
        providers = config.get("providers", {})
        return list(providers.keys())
    except Exception:
        return ["ollama"]


def detect_report_in_response(text: str) -> str | None:
    """Detect if response contains a CBA Indicator Selection Report."""
    if "# CBA Indicator Selection Report" in text:
        start_idx = text.find("# CBA Indicator Selection Report")
        return text[start_idx:].strip()
    return None


def init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    defaults = {
        "messages": [],
        "agent": None,
        "provider_config": None,
        "pdf_context": None,
        "last_report": None,
        "agent_ready": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> tuple[str, str]:
    """Render sidebar with configuration options. Returns (provider, tool_set)."""
    st.sidebar.title("⚙️ Configuration")

    # Provider selection
    available_providers = get_available_providers()
    provider = st.sidebar.selectbox(
        "AI Provider",
        options=available_providers,
        index=0,
        help="Select the AI model provider",
    )

    # Tool set selection
    tool_set = st.sidebar.radio(
        "Tool Set",
        options=["reduced", "full"],
        index=0,
        format_func=lambda x: "Reduced (24 tools)" if x == "reduced" else "Full (62 tools)",
        help="Reduced set is faster; Full set includes all data tools",
    )

    st.sidebar.divider()

    # PDF Upload
    st.sidebar.subheader("📄 PDF Context")
    uploaded_file = st.sidebar.file_uploader(
        "Upload a PDF for context",
        type=["pdf"],
        help="The PDF text will be provided as context to the agent",
    )

    if uploaded_file is not None:
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

    if st.session_state.pdf_context:
        if st.sidebar.button("🗑️ Clear PDF Context"):
            st.session_state.pdf_context = None
            st.session_state.pdf_filename = None
            st.rerun()

    st.sidebar.divider()

    # Report Export
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

    # Clear chat
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.last_report = None
        st.session_state.agent = None
        st.session_state.agent_ready = False
        st.rerun()

    return provider, tool_set


def main() -> None:
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="CBA Indicators Assistant",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    provider, tool_set = render_sidebar()

    st.title("🌍 CBA Indicators Assistant")
    st.caption("Sustainable Agriculture Data & Indicator Selection")

    # Check if we need to (re)create the agent
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

                status.update(label=f"✅ Ready ({provider_config.model_id})", state="complete")
            except Exception as e:
                status.update(label=f"❌ Error: {e}", state="error")
                st.error(f"Failed to initialize agent: {e}")
                st.stop()

    # Display provider info
    if st.session_state.provider_config:
        pc = st.session_state.provider_config
        tool_count = len(FULL_TOOLS) if tool_set == "full" else len(REDUCED_TOOLS)
        st.info(f"**Provider:** {pc.name} | **Model:** {pc.model_id} | **Tools:** {tool_count}")

    # Display PDF context indicator
    if st.session_state.pdf_context:
        st.success(f"📄 PDF context loaded: {st.session_state.get('pdf_filename', 'document.pdf')}")

    # Chat message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about indicators, methods, climate, soil..."):
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

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response_text = ""
                    for chunk in stream_agent_response(st.session_state.agent, full_prompt):
                        response_text += chunk

                    st.markdown(response_text)

                    # Check for report and save for export
                    report = detect_report_in_response(response_text)
                    if report:
                        st.session_state.last_report = report
                        st.toast("📄 Report detected! Download available in sidebar.")

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

</details>

### Phase 3: Run Commands

After creating the file and syncing dependencies:

```bash
# Install dependencies
uv sync

# Run via entry point
agentic-cba-ui

# Or run directly with Streamlit
streamlit run src/agentic_cba_indicators/ui.py

# Run with specific port
streamlit run src/agentic_cba_indicators/ui.py --server.port 8502
```

### Phase 4: Testing Checklist

- [ ] Manual testing with all providers (ollama, anthropic, openai, bedrock, gemini)
- [ ] PDF upload with various file sizes (small, medium, large)
- [ ] Report generation and download workflow
- [ ] Provider switching mid-conversation
- [ ] Tool set switching (reduced ↔ full)
- [ ] Edge cases: empty prompts, network errors, Ollama not running
- [ ] Browser compatibility (Chrome, Firefox, Safari)

---

## Feature Summary

| Feature | Implementation | Status |
|---------|----------------|--------|
| **Sidebar** | Provider dropdown, tool set toggle, PDF uploader, report download button, clear chat | 🔲 Planned |
| **Chat** | Streaming responses (via Strands agent), markdown rendering, persistent history via `st.session_state` | 🔲 Planned |
| **PDF** | Text extraction with pymupdf, injected as context prefix | 🔲 Planned |
| **Export** | Auto-detects `# CBA Indicator Selection Report` in responses and enables download | 🔲 Planned |

---

## UI Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🌍 CBA Indicators Assistant                                              │
│  Sustainable Agriculture Data & Indicator Selection                       │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┬───────────────────────────────────────────────────┤
│  │  ⚙️ Configuration │                                                   │
│  │                  │  ℹ️ Provider: ollama | Model: llama3.1 | Tools: 24 │
│  │  AI Provider     │                                                   │
│  │  [ollama     ▼]  │  📄 PDF context loaded: project_overview.pdf      │
│  │                  │                                                   │
│  │  Tool Set        │  ┌───────────────────────────────────────────────┐│
│  │  ○ Reduced (24)  │  │ 👤 User                                       ││
│  │  ● Full (62)     │  │ Find indicators for measuring soil health in  ││
│  │                  │  │ a cotton farming project                      ││
│  │ ─────────────────│  └───────────────────────────────────────────────┘│
│  │  📄 PDF Context  │                                                   │
│  │                  │  ┌───────────────────────────────────────────────┐│
│  │  [Choose File]   │  │ 🤖 Assistant                                  ││
│  │                  │  │ I found 15 relevant indicators for soil       ││
│  │ ─────────────────│  │ health measurement:                           ││
│  │  📥 Export       │  │                                               ││
│  │                  │  │ **Top recommendations:**                      ││
│  │  [📄 Download    │  │ 1. [107] Soil organic carbon (SOC)            ││
│  │   Last Report]   │  │ 2. [100] Soil aggregate stability             ││
│  │                  │  │ 3. [106] Soil biodiversity index              ││
│  │ ─────────────────│  │ ...                                           ││
│  │                  │  └───────────────────────────────────────────────┘│
│  │  [🗑️ Clear Chat] │                                                   │
│  │                  │  ┌───────────────────────────────────────────────┐│
│  └──────────────────┤  │ Ask about indicators, methods, climate...  📤 ││
│                     │  └───────────────────────────────────────────────┘│
└─────────────────────┴───────────────────────────────────────────────────┘
```

---

## Technical Deep Dive

### Strands Agent Streaming Patterns

The Strands SDK provides two streaming approaches:

**1. Callback Handler (Synchronous)**
```python
def handle_events(**kwargs):
    if "data" in kwargs:
        print(kwargs["data"], end="")  # Text chunk
    if "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        if tool.get("name"):
            print(f"\n🔧 Using tool: {tool['name']}")

agent = Agent(callback_handler=handle_events)
agent("What is 2+2?")  # Events streamed via callback
```

**2. Async Iterator**
```python
async for event in agent.stream_async("What is 2+2?"):
    if "data" in event:
        print(event["data"], end="")
```

**Event Types Reference:**

| Event Key | Type | Description |
|-----------|------|-------------|
| `init_event_loop` | bool | True at start of agent invocation |
| `start_event_loop` | bool | True when event loop is starting |
| `data` | str | Text chunk from model output |
| `complete` | bool | Whether this is the final chunk |
| `current_tool_use` | dict | `{name, toolUseId, input}` |
| `reasoningText` | str | Reasoning text (if enabled) |
| `message` | dict | Present when new message created |
| `result` | AgentResult | Final result object |
| `force_stop` | bool | True if event loop was forced to stop |

### Streamlit Chat Components Reference

**`st.chat_input(placeholder)`**
- Returns user's message string when submitted
- Auto-clears after submission
- Positioned at page bottom by default
- Use walrus operator pattern: `if prompt := st.chat_input("..."):`

**`st.chat_message(name, avatar=None)`**
- Context manager for message display
- `name`: "user" or "assistant" (determines default avatar)
- Can contain any Streamlit elements (text, charts, tables, expanders)

**`st.write_stream(generator)`**
- Renders generator output with typewriter effect
- Accumulates and returns final text as string
- Ideal for streaming LLM responses

### Session State Design Notes

**Why Dual State?**

| State Layer | Purpose | Managed By |
|-------------|---------|------------|
| `st.session_state.messages` | UI display history (simple) | Streamlit |
| `agent.conversation_manager` | Full context with tool calls | Strands SDK |

The Strands `SlidingWindowConversationManager` maintains conversation context internally (including tool use blocks and results). The UI only stores simplified `{role, content}` dicts for display. This avoids:

1. Duplicating complex message structures
2. Serialization issues with tool call objects
3. Memory bloat from storing full context twice

**Session State Gotchas:**

1. **Widget keys must be unique** — Use f-strings with indices
2. **Callbacks run before rerun** — State updates visible in next cycle
3. **Objects in session_state** — Agent instances persist across reruns (good!)
4. **File uploader reset** — Clear by setting key or using `st.rerun()`

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Large PDF exceeds context | Agent errors or truncation | Medium | Show warning if >50KB, consider chunking |
| Slow provider initialization | Poor UX on provider switch | Medium | Show `st.status()` with progress |
| Streamlit rerun clears callback state | Lost streaming data | Low | Accumulate in session_state before render |
| Network timeout on Ollama | Hung UI | Medium | Set httpx timeout, show error gracefully |
| Context window overflow | Model rejection | Medium | Track token estimate, warn user |

---

## Future Enhancements (Out of Scope for v1)

- [ ] **Multi-file upload** — Support multiple PDFs or other document types (Excel, CSV)
- [ ] **Export formats** — PDF, DOCX in addition to Markdown
- [ ] **Conversation history** — Save/load conversations to file
- [ ] **Tool visualization** — Show tool invocations in expandable UI sections
- [ ] **User authentication** — Protect access in deployed environments
- [ ] **Ollama model dropdown** — Show and select from available local models
- [ ] **Token usage display** — Show estimated/actual token consumption
- [ ] **Feedback mechanism** — Thumbs up/down on responses

---

## References

- [Streamlit Chat API Reference](https://docs.streamlit.io/develop/api-reference/chat)
- [Streamlit Session State Concepts](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Strands Agents Streaming Overview](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/streaming/)
- [Strands Callback Handler API](https://strandsagents.com/latest/documentation/docs/api-reference/python/handlers/callback_handler/)
- [Strands CLI Reference Implementation](https://strandsagents.com/latest/documentation/docs/examples/python/cli-reference-agent/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Build a basic LLM chat app (Streamlit Tutorial)](https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps)
