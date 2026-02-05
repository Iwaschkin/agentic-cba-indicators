"""
Streamlit UI for Agentic CBA Indicators.

Provides:
- Modern chat interface inspired by Streamlit AI assistant demo
- PDF upload for context extraction
- Provider and tool set selection
- Markdown report export
- CBA branding and styling

Entry point: agentic-cba-ui
"""

from __future__ import annotations

import datetime
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
from agentic_cba_indicators.logging_config import setup_logging
from agentic_cba_indicators.memory import (
    TokenBudgetConversationManager,
    estimate_tokens_heuristic,
)
from agentic_cba_indicators.prompts import get_system_prompt
from agentic_cba_indicators.security import sanitize_pdf_context, sanitize_user_input
from agentic_cba_indicators.tools import FULL_TOOLS, REDUCED_TOOLS

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence

# =============================================================================
# Constants and Configuration
# =============================================================================

# Local logo path (relative to cba_inputs folder)
CBA_LOGO_PATH = "cba_inputs/CBA_logo_negative_RGB.svg"

# CBA Brand Colors (from website screenshots)
CBA_COLORS = {
    "primary": "#0d1b2a",  # Dark Navy Blue (header/sidebar background)
    "secondary": "#1b3a4b",  # Lighter Navy (hover states)
    "accent_gold": "#c9a227",  # Golden/Amber (circles, highlights, CTAs)
    "accent_teal": "#4a9bb8",  # Teal/Cyan (secondary accent circles)
    "background": "#ffffff",  # White (content areas)
    "background_alt": "#f5f5f5",  # Light gray (alternating sections)
    "text_light": "#ffffff",  # White text on dark
    "text_dark": "#1a1a1a",  # Dark text on light
}

# Custom CSS for CBA branding (matching website design)
CBA_CUSTOM_CSS = """
<style>
    /* Import Google Fonts - matching CBA website typography */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Open+Sans:wght@400;600&display=swap');

    /* Main container background */
    .stApp {
        background-color: #ffffff;
    }

    /* Global typography sizing (slightly smaller) */
    html, body, [class*="st-"] {
        font-size: 14px;
        line-height: 1.45;
    }

    /* Headers - Montserrat (matching CBA website) */
    h1, h2, h3 {
        font-family: 'Montserrat', sans-serif !important;
        color: #0d1b2a !important;
        font-weight: 600 !important;
    }

    h1 {
        font-weight: 700 !important;
        font-size: 30px !important;
        letter-spacing: 0.2px;
    }

    h2 {
        font-size: 22px !important;
    }

    h3 {
        font-size: 18px !important;
    }

    /* Body text - Open Sans */
    p, li, span, div, label {
        font-family: 'Open Sans', sans-serif;
    }

    /* Primary buttons - Golden accent */
    .stButton > button[kind="primary"] {
        background-color: transparent !important;
        color: #c9a227 !important;
        border: 2px solid #c9a227 !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #c9a227 !important;
        color: #0d1b2a !important;
    }

    /* Secondary/tertiary buttons */
    .stButton > button[kind="secondary"],
    .stButton > button[kind="tertiary"] {
        color: #c9a227 !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Chat message styling */
    .stChatMessage {
        border-radius: 10px;
        border: 1px solid rgba(13, 27, 42, 0.08);
        background-color: #f7f8f9;
        font-family: 'Open Sans', sans-serif;
        padding: 4px 2px;
    }

    /* Sidebar styling - Dark Navy */
    [data-testid="stSidebar"] {
        background-color: #0d1b2a !important;
        border-right: 1px solid rgba(201, 162, 39, 0.25);
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stFileUploader label {
        color: #ffffff !important;
    }

    /* Sidebar input styling for contrast */
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: #122636 !important;
        border: 1px solid rgba(201, 162, 39, 0.45) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-size: 13px !important;
    }

    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] span {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
        color: #ffffff !important;
        font-size: 13px !important;
    }

    /* Dropdown menu styling (BaseWeb) */
    [data-baseweb="menu"] {
        background-color: #0d1b2a !important;
        color: #ffffff !important;
        border: 1px solid rgba(201, 162, 39, 0.35) !important;
        border-radius: 8px !important;
    }

    [data-baseweb="menu"] * {
        color: #ffffff !important;
    }

    [data-baseweb="menu"] [data-baseweb="option"]:hover {
        background-color: #1b3a4b !important;
    }

    /* Sidebar dividers */
    [data-testid="stSidebar"] hr {
        border-color: rgba(201, 162, 39, 0.3) !important;
        margin: 14px 0 !important;
    }

    /* Pills/suggestion buttons - Golden accent */
    .stPills [data-baseweb="tag"] {
        background-color: transparent !important;
        border: 2px solid #c9a227 !important;
        color: #c9a227 !important;
        font-size: 13px !important;
    }

    .stPills [data-baseweb="tag"]:hover {
        background-color: #c9a227 !important;
        color: #0d1b2a !important;
    }

    /* Links - Golden accent */
    a {
        color: #c9a227 !important;
    }

    a:hover {
        color: #e0b82d !important;
    }

    /* Success messages */
    .stSuccess {
        background-color: rgba(201, 162, 39, 0.1) !important;
        border-left-color: #c9a227 !important;
    }

    /* Info messages - Teal accent */
    .stInfo {
        background-color: rgba(74, 155, 184, 0.1) !important;
        border-left-color: #4a9bb8 !important;
    }

    /* Caption/subtitle styling */
    .stCaption {
        color: #666666 !important;
        font-family: 'Open Sans', sans-serif !important;
        font-size: 12.5px !important;
    }

    /* Chat input styling */
    .stChatInput input {
        font-family: 'Open Sans', sans-serif !important;
        font-size: 14px !important;
        border: 1px solid rgba(13, 27, 42, 0.15) !important;
        border-radius: 10px !important;
    }

    .stChatInput input:focus {
        border-color: #c9a227 !important;
        box-shadow: 0 0 0 2px rgba(201, 162, 39, 0.2) !important;
    }

    /* Spinner text */
    .stSpinner > div {
        color: #c9a227 !important;
    }

    /* Download button in sidebar */
    [data-testid="stSidebar"] .stDownloadButton > button {
        background-color: transparent !important;
        border: 2px solid #c9a227 !important;
        color: #c9a227 !important;
        font-size: 12.5px !important;
        letter-spacing: 0.5px !important;
    }

    [data-testid="stSidebar"] .stDownloadButton > button:hover {
        background-color: #c9a227 !important;
        color: #0d1b2a !important;
    }

    /* Status indicator */
    .stStatus {
        border-color: #4a9bb8 !important;
    }

    /* Toast notifications */
    .stToast {
        background-color: #0d1b2a !important;
        color: #ffffff !important;
    }
</style>
"""

# Suggested questions for new users (using material icons)
SUGGESTIONS = {
    ":material/eco: Soil health indicators": (
        "What indicators should I use to measure soil health improvement "
        "in a regenerative agriculture project?"
    ),
    ":material/groups: Farmer livelihoods": (
        "Help me find indicators to track farmer income and livelihoods "
        "for a cotton project in West Africa."
    ),
    ":material/forest: Biodiversity monitoring": (
        "What are low-cost methods to measure biodiversity in agricultural "
        "landscapes with limited budget?"
    ),
    ":material/water_drop: Water quality": (
        "Which indicators can track water quality and conservation "
        "in smallholder farming systems?"
    ),
    ":material/query_stats: Project baseline": (
        "I need to establish baseline data for a new project in Kenya. "
        "What data should I gather about the area?"
    ),
}


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
    system_prompt = get_system_prompt(agent_config.prompt_name)

    # CR-0009: Calculate system_prompt_budget to match CLI behavior
    system_prompt_budget = _estimate_system_prompt_budget(system_prompt, list(tools))

    # Use token-budget manager if context_budget is set, otherwise fall back to sliding window
    conversation_manager: (
        TokenBudgetConversationManager | SlidingWindowConversationManager
    )
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
    - initial_question: str | None - First question from welcome screen
    - selected_suggestion: str | None - Selected suggestion pill
    - prev_question_timestamp: datetime - Rate limiting
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
        "initial_question": None,
        "selected_suggestion": None,
        "prev_question_timestamp": datetime.datetime.fromtimestamp(0),
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
    1. CBA Logo
    2. Provider selection dropdown
    3. Tool set radio buttons
    4. PDF upload and management
    5. Report export download button
    6. Clear chat button

    Returns:
        Tuple of (selected_provider, selected_tool_set)
    """
    # --- CBA Logo ---
    st.sidebar.image(CBA_LOGO_PATH, width=220)
    st.sidebar.markdown("")

    # --- Provider Selection ---
    st.sidebar.markdown("### ⚙️ Configuration")
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
    st.sidebar.markdown("### 📄 Project Document")
    uploaded_file = st.sidebar.file_uploader(
        "Upload a PDF for context",
        type=["pdf"],
        help="Upload your project proposal or report for context",
        label_visibility="collapsed",
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

        st.sidebar.success(f"✅ {uploaded_file.name}")
        st.sidebar.caption(f"{len(sanitized_text):,} characters extracted")

        if was_truncated:
            st.sidebar.warning("⚠️ Text truncated to 50,000 characters")

    # Show clear button if PDF is loaded
    if st.session_state.pdf_context and st.sidebar.button(
        "Clear document", icon=":material/delete:"
    ):
        st.session_state.pdf_context = None
        st.session_state.pdf_filename = None
        st.rerun()

    st.sidebar.divider()

    # --- Report Export ---
    st.sidebar.markdown("### 📥 Export")
    if st.session_state.last_report:
        st.sidebar.download_button(
            label="Download Report",
            data=st.session_state.last_report,
            file_name="cba_indicator_report.md",
            mime="text/markdown",
            icon=":material/download:",
        )
    else:
        st.sidebar.caption("No report generated yet")

    return provider, tool_set


# =============================================================================
# Welcome Screen
# =============================================================================


def show_welcome_screen() -> None:
    """Display the welcome screen for new users.

    Shows:
    - Welcome message aligned with CBA mission
    - Initial chat input
    - Suggestion pills for common questions
    """
    # Welcome message - aligned with CBA website mission statement
    st.markdown(
        "**Accelerating the transition to a nature-first circular bioeconomy**\n\n"
        "I'm here to help you select the right **M&E indicators** for your sustainable "
        "agriculture and community development projects—combining scientific rigour "
        "with practical field knowledge.\n\n"
        "**How I can help:**\n\n"
        "🌱 **Environmental outcomes** — soil health, biodiversity, water quality, "
        "carbon sequestration\n\n"
        "👥 **Social impact** — farmer livelihoods, gender equity, community resilience\n\n"
        "📊 **Baseline research** — gathering contextual data about your project area\n\n"
        "📋 **Practical methods** — feasible measurement approaches within your budget\n\n"
        "---\n\n"
        "**Tell me about your project** to get started, or explore an example below:"
    )

    # Chat input for initial question
    st.chat_input(
        "Describe your project location, commodity, and goals...",
        key="initial_question",
    )

    # Suggestion pills
    st.pills(
        label="Example questions",
        label_visibility="collapsed",
        options=SUGGESTIONS.keys(),
        key="selected_suggestion",
    )


# =============================================================================
# About Dialog
# =============================================================================


@st.dialog("About the CBA Indicator Selection Assistant")
def show_about_dialog() -> None:
    """Display information about the tool aligned with CBA branding."""
    st.markdown(
        "The **Circular Bioeconomy Alliance** aims to accelerate the transition to "
        "a nature-first circular bioeconomy that is climate neutral, inclusive and "
        "powers prosperity.\n\n"
        "This AI assistant supports project leaders from partner organizations in "
        "selecting appropriate **M&E indicators** for sustainable agriculture and "
        "community development projects.\n\n"
        "---\n\n"
        "**Built on the CBA M&E Indicator Framework:**\n\n"
        "📚 Curated indicator knowledge base with scientific references\n\n"
        "🌍 Real-time environmental and socio-economic data\n\n"
        "🔬 Evidence-based measurement method recommendations\n\n"
        "---\n\n"
        "**External Data Sources:**\n"
        "- Climate & Weather: Open-Meteo, NASA POWER\n"
        "- Soil Properties: ISRIC SoilGrids\n"
        "- Biodiversity: GBIF\n"
        "- Forestry: Global Forest Watch, FAO\n"
        "- Socio-economic: World Bank, ILO\n\n"
        "---\n\n"
        "⚠️ AI-generated recommendations should be reviewed by qualified "
        "M&E specialists. Data accuracy depends on external sources.\n\n"
        "[**circularbioeconomyalliance.org**](https://circularbioeconomyalliance.org/)"
    )


# =============================================================================
# Main Application
# =============================================================================


def main() -> None:
    """Main Streamlit application entry point.

    Application flow:
    1. Configure page settings
    2. Initialize session state
    3. Render sidebar (returns provider/tool_set selections)
    4. Show welcome screen OR chat interface
    5. Handle agent initialization
    6. Display chat history
    7. Handle new user input
    8. Generate and display assistant response
    """
    if not _is_streamlit_runtime():
        raise SystemExit(
            "This module must be run with Streamlit. Use: streamlit run "
            "src/agentic_cba_indicators/ui.py"
        )

    setup_logging()

    # --- Page Configuration ---
    st.set_page_config(
        page_title="CBA Indicator Selection Assistant",
        page_icon="�",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Apply CBA Branding CSS ---
    st.markdown(CBA_CUSTOM_CSS, unsafe_allow_html=True)

    # --- Initialize State ---
    init_session_state()

    # --- Render Sidebar ---
    provider, tool_set = render_sidebar()

    # --- Detect user interaction state ---
    user_just_asked_initial_question = (
        "initial_question" in st.session_state and st.session_state.initial_question
    )

    user_just_clicked_suggestion = (
        "selected_suggestion" in st.session_state
        and st.session_state.selected_suggestion
    )

    user_first_interaction = (
        user_just_asked_initial_question or user_just_clicked_suggestion
    )

    has_message_history = (
        "messages" in st.session_state and len(st.session_state.messages) > 0
    )

    # --- Title Row with Restart Button ---
    title_row = st.container()

    with title_row:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.title("� CBA Indicator Selection Assistant")

        # Only show restart button if there's chat history
        if has_message_history or user_first_interaction:
            with col2:

                def clear_conversation():
                    st.session_state.messages = []
                    st.session_state.initial_question = None
                    st.session_state.selected_suggestion = None
                    st.session_state.last_report = None

                st.button(
                    "Restart",
                    icon=":material/refresh:",
                    on_click=clear_conversation,
                )

    # --- Show Welcome Screen if No Interaction Yet ---
    if not user_first_interaction and not has_message_history:
        st.session_state.messages = []
        show_welcome_screen()

        # About button at the bottom
        st.button(
            "&nbsp;:small[:gray[:material/info: About this tool]]",
            type="tertiary",
            on_click=show_about_dialog,
        )
        st.stop()

    # --- Agent Initialization (only when needed) ---
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
        st.caption(
            f"**Provider:** {pc.name} • **Model:** {pc.model_id} • **Tools:** {tool_count}"
        )

    # --- PDF Context Indicator ---
    if st.session_state.pdf_context:
        st.success(
            f"📄 Project document loaded: **{st.session_state.get('pdf_filename', 'document.pdf')}**"
        )

    # --- Chat History ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Chat Input ---
    user_message = st.chat_input("Ask a follow-up question...")

    # Handle initial question or suggestion click
    if not user_message:
        if user_just_asked_initial_question:
            user_message = st.session_state.initial_question
        if user_just_clicked_suggestion:
            user_message = SUGGESTIONS[st.session_state.selected_suggestion]

    if user_message:
        # Escape $ for LaTeX
        user_message = user_message.replace("$", r"\$")

        # Sanitize user input (length limit, control char removal)
        safe_prompt = sanitize_user_input(user_message)

        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        # Prepare full prompt with PDF context if available
        full_prompt = safe_prompt
        if st.session_state.pdf_context:
            full_prompt = (
                f"I have uploaded a project document. Here is the extracted text:\n\n"
                f"--- DOCUMENT CONTENT START ---\n"
                f"{st.session_state.pdf_context}\n"
                f"--- DOCUMENT CONTENT END ---\n\n"
                f"User question: {safe_prompt}"
            )

        # Generate assistant response
        with st.chat_message("assistant"), st.spinner("Researching..."):
            try:
                response_text = ""
                for chunk in stream_agent_response(st.session_state.agent, full_prompt):
                    response_text += chunk

                st.markdown(response_text)

                # Check for report and save for export
                report = detect_report_in_response(response_text)
                if report:
                    st.session_state.last_report = report
                    st.toast(
                        "📄 Report detected! Download available in sidebar.", icon="✅"
                    )

                # Add assistant message to history
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )

            except Exception as e:
                error_msg = f"I encountered an error: {e}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )


if __name__ == "__main__":
    main()
