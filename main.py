"""
Strands CLI Chatbot - Weather, Climate, and Socio-Economic Data Assistant

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
Configuration via config/providers.yaml.
"""

from pathlib import Path

from config import (
    AgentConfig,
    ProviderConfig,
    create_model,
    get_agent_config,
    get_provider_config,
    load_config,
    print_provider_info,
)
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from tools import (
    compare_commodity_producers,
    compare_gender_gaps,
    compare_indicators,
    export_indicator_selection,
    find_feasible_methods,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    find_indicators_by_principle,
    get_agricultural_climate,
    get_biodiversity_summary,
    get_climate_data,
    get_commodity_production,
    get_commodity_trade,
    get_country_indicators,
    get_crop_production,
    get_current_weather,
    get_employment_by_gender,
    get_evapotranspiration,
    get_forest_statistics,
    get_gender_indicators,
    get_gender_time_series,
    get_historical_climate,
    get_indicator_details,
    get_labor_indicators,
    get_labor_time_series,
    get_land_use,
    get_sdg_for_cba_principle,
    get_sdg_progress,
    get_sdg_series_data,
    get_soil_carbon,
    get_soil_properties,
    get_soil_texture,
    get_solar_radiation,
    get_species_occurrences,
    get_species_taxonomy,
    get_usecase_details,
    get_usecases_by_indicator,
    get_weather_forecast,
    get_world_bank_data,
    list_available_classes,
    list_fas_commodities,
    list_indicators_by_component,
    list_knowledge_base_stats,
    search_commodity_data,
    search_fao_indicators,
    search_gender_indicators,
    search_indicators,
    search_labor_indicators,
    search_methods,
    search_sdg_indicators,
    search_species,
    search_usecases,
)

# Load system prompt from external file
PROMPT_FILE = Path(__file__).parent / "prompts" / "system_prompt_minimal.md"


def load_system_prompt() -> str:
    """Load the system prompt from the external markdown file."""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    else:
        # Fallback minimal prompt if file is missing
        return """You are a helpful data assistant for sustainable agriculture.
Call tools to get real data. Never ask clarifying questions."""


# =============================================================================
# Tool Sets
# =============================================================================

# Reduced tool set (19 tools) - for smaller models like llama3.1:8b
REDUCED_TOOLS = [
    # Essential Context Tools
    get_current_weather,
    get_climate_data,
    get_soil_properties,
    get_soil_carbon,
    get_country_indicators,
    # CBA Knowledge Base (core)
    search_indicators,
    search_methods,
    get_indicator_details,
    list_knowledge_base_stats,
    # Indicator Selection (core)
    find_indicators_by_principle,
    find_feasible_methods,
    list_indicators_by_component,
    list_available_classes,
    find_indicators_by_class,
    compare_indicators,
    export_indicator_selection,
    # Use Cases
    search_usecases,
    get_usecase_details,
    get_usecases_by_indicator,
]

# Full tool set (52 tools) - for larger models like Claude, GPT-4, etc.
FULL_TOOLS = [
    # Weather & Climate (Open-Meteo)
    get_current_weather,
    get_weather_forecast,
    get_climate_data,
    get_historical_climate,
    # Agricultural Climate (NASA POWER)
    get_agricultural_climate,
    get_solar_radiation,
    get_evapotranspiration,
    # Soil Properties (ISRIC SoilGrids)
    get_soil_properties,
    get_soil_carbon,
    get_soil_texture,
    # Biodiversity (GBIF)
    search_species,
    get_species_occurrences,
    get_biodiversity_summary,
    get_species_taxonomy,
    # Labor Statistics (ILO STAT)
    get_labor_indicators,
    get_employment_by_gender,
    get_labor_time_series,
    search_labor_indicators,
    # Gender Statistics (World Bank)
    get_gender_indicators,
    compare_gender_gaps,
    get_gender_time_series,
    search_gender_indicators,
    # Agriculture & Forestry (FAO)
    get_forest_statistics,
    get_crop_production,
    get_land_use,
    search_fao_indicators,
    # Commodity Markets (USDA FAS)
    get_commodity_production,
    get_commodity_trade,
    compare_commodity_producers,
    list_fas_commodities,
    search_commodity_data,
    # SDG Indicators (UN SDG API)
    get_sdg_progress,
    search_sdg_indicators,
    get_sdg_series_data,
    get_sdg_for_cba_principle,
    # Socio-economic (World Bank & REST Countries)
    get_country_indicators,
    get_world_bank_data,
    # Knowledge Base
    search_indicators,
    search_methods,
    get_indicator_details,
    list_knowledge_base_stats,
    # Indicator Selection
    find_indicators_by_principle,
    find_feasible_methods,
    list_indicators_by_component,
    list_available_classes,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    compare_indicators,
    export_indicator_selection,
    # Use Cases
    search_usecases,
    get_usecase_details,
    get_usecases_by_indicator,
]


def create_agent_from_config(
    config_path: Path | str | None = None,
    provider_override: str | None = None,
) -> tuple[Agent, ProviderConfig, AgentConfig]:
    """
    Create and configure the Strands agent from configuration file.

    Args:
        config_path: Path to providers.yaml (optional, defaults to config/providers.yaml)
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

    # Configure conversation memory
    conversation_manager = SlidingWindowConversationManager(
        window_size=agent_config.conversation_window,
    )

    # Select tool set
    if agent_config.tool_set == "full":
        tools = FULL_TOOLS
    else:
        tools = REDUCED_TOOLS

    # Create agent
    agent = Agent(
        model=model,
        system_prompt=load_system_prompt(),
        conversation_manager=conversation_manager,
        tools=tools,
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

    conversation_manager = SlidingWindowConversationManager(window_size=5)

    agent = Agent(
        model=ollama_model,
        system_prompt=load_system_prompt(),
        conversation_manager=conversation_manager,
        tools=REDUCED_TOOLS,
    )

    return agent


def print_banner(tool_count: int, provider_config: ProviderConfig | None = None):
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


def print_help():
    """Print example queries."""
    print("\n📖 Example Queries:\n")
    print("Weather & Climate:")
    print("  • What's the weather in Tokyo?")
    print("  • Give me a 5-day forecast for London")
    print("  • What are the climate normals for Sydney?")
    print("  • How was the weather in Paris in 2020?")
    print("")
    print("Agricultural Climate (NASA POWER):")
    print("  • Get agricultural climate data for Iowa from Jan-Jun 2024")
    print("  • What's the solar radiation in Brazil for 2023?")
    print("  • Calculate evapotranspiration for Kenya last month")
    print("")
    print("Soil Properties (SoilGrids):")
    print("  • What are the soil properties in Chad?")
    print("  • Get soil carbon data for my location: 5.5, -0.2")
    print("  • What's the soil texture at 10, 20?")
    print("")
    print("Biodiversity (GBIF):")
    print("  • Search for African elephant species")
    print("  • Where have lions been observed in Kenya?")
    print("  • Get biodiversity summary for the Amazon rainforest")
    print("")
    print("Labor Statistics (ILO):")
    print("  • What are the labor indicators for Brazil?")
    print("  • Compare employment by gender in Kenya")
    print("  • Show unemployment trends for Germany since 2010")
    print("")
    print("Gender Statistics (World Bank):")
    print("  • Get gender indicators for Kenya")
    print("  • Compare gender gaps in education for Brazil")
    print("  • Show female labor force participation trends in India")
    print("")
    print("Agriculture & Forestry (FAO):")
    print("  • Get forest statistics for Brazil")
    print("  • Show cotton production in Chad over the last 10 years")
    print("  • What's the land use pattern in Kenya?")
    print("")
    print("Commodity Markets (USDA FAS):")
    print("  • Get cotton production data for Chad")
    print("  • Compare top coffee producing countries")
    print("  • Show cocoa trade trends for Ivory Coast")
    print("  • List available commodities in the FAS database")
    print("")
    print("UN SDG Indicators:")
    print("  • What's Brazil's progress on SDG 2 (Zero Hunger)?")
    print("  • Find SDG indicators related to water quality")
    print("  • Which SDGs align with CBA principle 1?")
    print("")
    print("Socio-Economic:")
    print("  • Tell me about Japan")
    print("  • What's the GDP of Germany?")
    print("  • Compare life expectancy in Sweden and USA")
    print("")
    print("CBA Indicators:")
    print("  • Find indicators for soil health measurement")
    print("  • What methods measure biodiversity?")
    print("  • Show indicators for a cotton farm in Chad")
    print("")


def main():
    """Main entry point for the CLI chatbot."""
    import sys

    # Parse command line arguments
    config_path = None
    provider_override = None

    for arg in sys.argv[1:]:
        if arg.startswith("--config="):
            config_path = arg.split("=")[1]
        elif arg.startswith("--provider="):
            provider_override = arg.split("=")[1]
        elif arg in ["-h", "--help"]:
            print("Usage: python main.py [OPTIONS]")
            print("\nOptions:")
            print("  --config=PATH       Path to providers.yaml config file")
            print(
                "  --provider=NAME     Override active provider (ollama, anthropic, openai, bedrock, gemini)"
            )
            print("\nExamples:")
            print(
                "  python main.py                          # Use default config (Ollama)"
            )
            print("  python main.py --provider=anthropic     # Use Anthropic Claude")
            print("  python main.py --provider=openai        # Use OpenAI GPT")
            print("  python main.py --provider=bedrock       # Use AWS Bedrock")
            print("  python main.py --provider=gemini        # Use Google Gemini")
            print("  python main.py --config=my_config.yaml  # Use custom config file")
            print("\nConfiguration:")
            print("  Edit config/providers.yaml to set API keys and model preferences.")
            print("  Environment variables are supported: ${ANTHROPIC_API_KEY}")
            sys.exit(0)

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
        print("   Create config/providers.yaml or specify --config=PATH")
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

            print("\nAssistant: ", end="", flush=True)

            # Get response from agent (streams to stdout by default)
            agent(user_input)

            print("\n")  # Add spacing after response

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
