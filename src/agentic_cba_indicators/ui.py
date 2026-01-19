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

from typing import TYPE_CHECKING, Any

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
from agentic_cba_indicators.memory import (
    TokenBudgetConversationManager,
    estimate_tokens_heuristic,
)
from agentic_cba_indicators.prompts import get_system_prompt
from agentic_cba_indicators.security import sanitize_pdf_context, sanitize_user_input
from agentic_cba_indicators.tools import FULL_TOOLS, REDUCED_TOOLS
from agentic_cba_indicators.tools._help import set_active_tools

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence


def _estimate_system_prompt_budget(
    system_prompt: str, tools: Sequence[Callable[..., str]]
) -> int:
    """Estimate token budget needed for system prompt and tool definitions.

    This uses the heuristic estimator to keep provider-agnostic behavior.
    Tool definitions are approximated using tool names and docstrings.
    """
    parts = [system_prompt]
    for tool in tools:
        name = getattr(tool, "__name__", str(tool))
        doc = getattr(tool, "__doc__", "") or ""
        parts.append(f"{name}\n{doc}")

    return estimate_tokens_heuristic("\n\n".join(parts))


def _is_streamlit_runtime() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


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
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            page_text = str(page.get_text())
            if page_text.strip():
                text_parts.append(f"--- Page {page_index + 1} ---\n{page_text}")
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

    tools = FULL_TOOLS if tool_set == "full" else REDUCED_TOOLS
    system_prompt = get_system_prompt()

    # CR-0009: Calculate system_prompt_budget to match CLI behavior
    system_prompt_budget = _estimate_system_prompt_budget(system_prompt, list(tools))

    # Use token-budget manager if context_budget is set, otherwise fall back to sliding window
    if agent_config.context_budget is not None:
        conversation_manager = TokenBudgetConversationManager(
            max_tokens=agent_config.context_budget,
            system_prompt_budget=system_prompt_budget,
        )
    else:
        # Legacy mode: use fixed message count
        conversation_manager = SlidingWindowConversationManager(
            window_size=agent_config.conversation_window,
        )

    set_active_tools(list(tools))

    # Create agent with selected tools
    # Convert tuple to list since Agent expects list type
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        conversation_manager=conversation_manager,
        tools=list(tools),
    )

    return agent, provider_config, agent_config


# =============================================================================
# Response Streaming
# =============================================================================


def _iter_text_chunks(result: Any) -> Generator[str, None, None]:
    message = getattr(result, "message", None)

    if isinstance(message, str) and message:
        yield message
        return

    if message:
        message_content = getattr(message, "content", None)
        if isinstance(message_content, list):
            for block in message_content:
                text = getattr(block, "text", None)
                if isinstance(text, str) and text:
                    yield text

    result_content = getattr(result, "content", None)
    if isinstance(result_content, list):
        for block in result_content:
            text = getattr(block, "text", None)
            if isinstance(text, str) and text:
                yield text


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
    result: Any = agent(prompt)
    yielded = False
    for chunk in _iter_text_chunks(result):
        yielded = True
        yield chunk

    if not yielded:
        yield str(result)


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
    defaults: dict[str, Any] = {
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
        format_func=lambda x: (
            f"Reduced ({len(REDUCED_TOOLS)} tools)"
            if x == "reduced"
            else f"Full ({len(FULL_TOOLS)} tools)"
        ),
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

    if uploaded_file is not None and (
        st.session_state.pdf_context is None
        or st.session_state.get("pdf_filename") != uploaded_file.name
    ):
        with st.sidebar.status("Extracting PDF text..."):
            pdf_bytes = uploaded_file.read()
            pdf_text = extract_text_from_pdf(pdf_bytes)

            # Sanitize PDF text (remove control chars, truncate if too long)
            sanitized_text, was_truncated = sanitize_pdf_context(pdf_text)
            st.session_state.pdf_context = sanitized_text
            st.session_state.pdf_filename = uploaded_file.name

        st.sidebar.success(f"✅ Loaded: {uploaded_file.name}")
        st.sidebar.caption(f"{len(sanitized_text):,} characters extracted")

        if was_truncated:
            st.sidebar.warning(
                f"⚠️ PDF text truncated from {len(pdf_text):,} to "
                f"{len(sanitized_text):,} characters (limit: 50,000)"
            )

    # Show clear button if PDF is loaded
    if st.session_state.pdf_context and st.sidebar.button("🗑️ Clear PDF Context"):
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
    if not _is_streamlit_runtime():
        raise SystemExit(
            "This module must be run with Streamlit. Use: streamlit run "
            "src/agentic_cba_indicators/ui.py"
        )

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
                agent, provider_config, _agent_config = create_agent_for_ui(
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
        # Sanitize user input (length limit, control char removal)
        safe_prompt = sanitize_user_input(prompt)

        # Add user message to history (show original for display)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare full prompt with PDF context if available
        full_prompt = safe_prompt
        if st.session_state.pdf_context:
            full_prompt = (
                f"I have uploaded a PDF document. Here is the extracted text:\n\n"
                f"--- PDF CONTENT START ---\n"
                f"{st.session_state.pdf_context}\n"
                f"--- PDF CONTENT END ---\n\n"
                f"User question: {safe_prompt}"
            )

        # Generate assistant response
        with st.chat_message("assistant"), st.spinner("Thinking..."):
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
