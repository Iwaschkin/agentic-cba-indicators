"""
Agentic CBA Indicators Chatbot - Weather, Climate, and Socio-Economic Data Assistant

A conversational AI assistant that can query:
- Current weather and forecasts (via Open-Meteo)
- Climate normals and historical data (via Open-Meteo)
- Agricultural climate data (via NASA POWER)
- Soil properties (via ISRIC SoilGrids)
- Biodiversity data (via GBIF)
- Labor statistics (via ILO STAT)
- SDG indicator progress (via UN SDG API)
- Country information and World Bank indicators

Supports multiple AI providers: Ollama, Anthropic, OpenAI, AWS Bedrock, Google Gemini.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from agentic_cba_indicators.config import (
    AgentConfig,
    ProviderConfig,
    create_model,
    get_agent_config,
    get_provider_config,
    load_config,
    print_provider_info,
)
from agentic_cba_indicators.logging_config import set_correlation_id, setup_logging
from agentic_cba_indicators.memory import (
    TokenBudgetConversationManager,
    estimate_tokens_heuristic,
)
from agentic_cba_indicators.prompts import get_system_prompt
from agentic_cba_indicators.security import (
    detect_injection_patterns,
    sanitize_user_input,
)
from agentic_cba_indicators.tools import FULL_TOOLS, REDUCED_TOOLS

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path


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


def create_agent_from_config(
    config_path: Path | str | None = None,
    provider_override: str | None = None,
) -> tuple[Agent, ProviderConfig, AgentConfig]:
    """
    Create and configure the Strands agent from configuration file.

    Args:
        config_path: Path to providers.yaml (optional, uses bundled default)
        provider_override: Override the active provider from command line

    Returns:
        Tuple of (Agent, ProviderConfig, AgentConfig)
    """
    # Load configuration
    config = load_config(config_path)

    # Allow command-line override of provider
    if provider_override:
        config["active_provider"] = provider_override

    provider_config = get_provider_config(config)
    agent_config = get_agent_config(config)

    # Create the model
    model = create_model(provider_config)

    # Select tool set (includes internal help tools)
    tools = FULL_TOOLS if agent_config.tool_set == "full" else REDUCED_TOOLS
    if not agent_config.parallel_tool_calls:
        tools = tuple(
            t for t in tools if getattr(t, "__name__", "") != "run_tools_parallel"
        )

    # Build system prompt and estimate reserved budget
    system_prompt = get_system_prompt(agent_config.prompt_name)
    system_prompt_budget = _estimate_system_prompt_budget(system_prompt, tools)

    # Configure conversation memory
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

    # Create agent with selected tools
    # Convert tuple to list since Agent expects list type
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        conversation_manager=conversation_manager,
        tools=list(tools),
    )

    return agent, provider_config, agent_config


def create_agent(
    model_id: str = "llama3.1:latest", host: str = "http://localhost:11434"
) -> Agent:
    """
    Create agent with Ollama (legacy interface for backward compatibility).

    Args:
        model_id: Ollama model ID
        host: Ollama server URL

    Returns:
        Configured Agent instance
    """
    from strands.models.ollama import OllamaModel

    ollama_model = OllamaModel(
        host=host,
        model_id=model_id,
        temperature=0.1,
        options={"num_ctx": 16384},
    )

    # Default token budget for legacy interface (conservative)
    system_prompt = get_system_prompt()
    system_prompt_budget = _estimate_system_prompt_budget(system_prompt, REDUCED_TOOLS)
    conversation_manager = TokenBudgetConversationManager(
        max_tokens=8000,
        system_prompt_budget=system_prompt_budget,
    )

    agent = Agent(
        model=ollama_model,
        system_prompt=system_prompt,
        conversation_manager=conversation_manager,
        tools=list(REDUCED_TOOLS),
    )

    return agent


def print_banner(
    tool_count: int, provider_config: ProviderConfig | None = None
) -> None:
    """Print the welcome banner."""
    print("\n" + "=" * 60)
    print("🌍 Data Assistant - CBA Indicators & Sustainable Agriculture")
    print("=" * 60)

    if provider_config:
        print()
        print_provider_info(provider_config)
        print(f"   Tools: {tool_count}")
    else:
        print(f"\nPowered by Strands Agents ({tool_count} tools loaded)")

    print("\nI can help you with:")
    print("  🌤️  Weather and climate data")
    print("  🪨  Soil properties and carbon content")
    print("  🌐  Country information")
    print("  📋  CBA ME Indicators and measurement methods")
    print("  📊  Indicator selection and comparison")
    print("  📁  Real project use cases")
    print("\nType 'quit' or 'exit' to end the conversation.")
    print("Type 'help' for example queries.")
    print("-" * 60 + "\n")


def print_help() -> None:
    """Print example queries."""
    print("\n📖 Example Queries:\n")
    print("Weather & Climate:")
    print("  • What's the weather in Tokyo?")
    print("  • Give me a 5-day forecast for London")
    print("  • What are the climate normals for Sydney?")
    print("")
    print("Agricultural Climate (NASA POWER):")
    print("  • Get agricultural climate data for Iowa from Jan-Jun 2024")
    print("  • What's the solar radiation in Brazil for 2023?")
    print("")
    print("Soil Properties (SoilGrids):")
    print("  • What are the soil properties in Chad?")
    print("  • Get soil carbon data for my location: 5.5, -0.2")
    print("")
    print("Biodiversity (GBIF):")
    print("  • Search for African elephant species")
    print("  • Get biodiversity summary for the Amazon rainforest")
    print("")
    print("Labor Statistics (ILO):")
    print("  • What are the labor indicators for Brazil?")
    print("  • Compare employment by gender in Kenya")
    print("")
    print("Gender Statistics (World Bank):")
    print("  • Get gender indicators for Kenya")
    print("  • Compare gender gaps in education for Brazil")
    print("")
    print("Agriculture & Forestry (FAO):")
    print("  • Get forest statistics for Brazil")
    print("  • Show cotton production in Chad over the last 10 years")
    print("")
    print("UN SDG Indicators:")
    print("  • What's Brazil's progress on SDG 2 (Zero Hunger)?")
    print("  • Find SDG indicators related to water quality")
    print("")
    print("Socio-Economic:")
    print("  • Tell me about Japan")
    print("  • What's the GDP of Germany?")
    print("")
    print("CBA Indicators:")
    print("  • Find indicators for soil health measurement")
    print("  • What methods measure biodiversity?")
    print("  • Show indicators for a cotton farm in Chad")
    print("")


def main() -> None:
    """Main entry point for the CLI chatbot."""
    import argparse
    import sys
    import uuid

    setup_logging()

    # Set up argument parser
    parser = argparse.ArgumentParser(
        prog="agentic-cba",
        description="CBA Indicators & Sustainable Agriculture Data Assistant",
        epilog=(
            "Examples:\n"
            "  agentic-cba                          # Use default config (Ollama)\n"
            "  agentic-cba --provider=anthropic     # Use Anthropic Claude\n"
            "  agentic-cba --provider=openai        # Use OpenAI GPT\n"
            "  agentic-cba --provider=bedrock       # Use AWS Bedrock\n"
            "  agentic-cba --provider=gemini        # Use Google Gemini\n"
            "  agentic-cba --config=my_config.yaml  # Use custom config file\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to providers.yaml config file",
    )

    parser.add_argument(
        "--provider",
        metavar="NAME",
        choices=["ollama", "anthropic", "openai", "bedrock", "gemini"],
        help="Override active provider (ollama, anthropic, openai, bedrock, gemini)",
    )

    args = parser.parse_args()

    config_path = args.config
    provider_override = args.provider

    try:
        agent, provider_config, agent_config = create_agent_from_config(
            config_path=config_path,
            provider_override=provider_override,
        )
        tool_count = (
            len(FULL_TOOLS) if agent_config.tool_set == "full" else len(REDUCED_TOOLS)
        )

        print_banner(tool_count=tool_count, provider_config=provider_config)
        print("✅ Agent ready!\n")

    except FileNotFoundError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("   Create a providers.yaml config file or specify --config=PATH")
        sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Missing Dependency: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error creating agent: {e}")
        sys.exit(1)

    # Main conversation loop
    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "bye", "q"]:
                print("\n👋 Goodbye! Have a great day!\n")
                break

            if user_input.lower() == "help":
                print_help()
                continue

            # Sanitize user input (length limit, control char removal)
            safe_input = sanitize_user_input(user_input)

            # Log potential injection patterns (for monitoring, not blocking)
            if patterns := detect_injection_patterns(safe_input):
                import logging

                logging.getLogger(__name__).debug(
                    "Potential injection pattern detected: %s", patterns
                )

            # CR-0016: correlation_id inside try for proper cleanup on any exception
            try:
                correlation_id = str(uuid.uuid4())
                set_correlation_id(correlation_id)

                print("\nAssistant: ", end="", flush=True)

                # Get response from agent (streams to stdout by default)
                agent(safe_input)

                print("\n")  # Add spacing after response
            finally:
                set_correlation_id(None)

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
