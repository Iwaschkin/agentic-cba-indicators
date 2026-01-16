"""
Strands CLI Chatbot - Weather, Climate, and Socio-Economic Data Assistant

A conversational AI assistant that can query:
- Current weather and forecasts (via Open-Meteo)
- Climate normals and historical data (via Open-Meteo)
- Country information and World Bank indicators

Uses Ollama as the AI provider with conversation memory.
"""

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models.ollama import OllamaModel
from tools import (
    compare_indicators,
    export_indicator_selection,
    find_feasible_methods,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    find_indicators_by_principle,
    get_climate_data,
    get_country_indicators,
    get_current_weather,
    get_historical_climate,
    get_indicator_details,
    get_usecase_details,
    get_usecases_by_indicator,
    get_weather_forecast,
    get_world_bank_data,
    list_available_classes,
    list_indicators_by_component,
    list_knowledge_base_stats,
    search_indicators,
    search_methods,
    search_usecases,
)

SYSTEM_PROMPT = """You are a helpful data assistant specialized in weather, climate, socio-economic information, and CBA (Cost-Benefit Analysis) indicators for sustainable agriculture.

IMPORTANT: When answering questions, you MUST call the appropriate tools to gather real data. Do NOT describe what tools you would use or ask the user to make tool calls. Execute the tools yourself and present the results.

**Available Tools:**

Weather & Climate:
- get_current_weather(city): Current weather conditions
- get_weather_forecast(city, days): Weather forecast up to 16 days
- get_climate_data(city): 30-year climate normals
- get_historical_climate(city, year): Historical weather for a specific year

Socio-Economic:
- get_country_indicators(country): Country profile (population, area, languages, etc.)
- get_world_bank_data(country, indicator): Economic indicators - options: gdp, gdp_per_capita, gdp_growth, population, inflation, unemployment, life_expectancy, literacy, poverty, gini, co2, renewable_energy, internet, mobile

CBA ME Indicators Knowledge Base:
- search_indicators(query, n_results): Search indicators by topic (soil, water, biodiversity, labor, income, etc.)
- search_methods(query, n_results): Search measurement methods and techniques
- get_indicator_details(indicator_id): Full details for a specific indicator by ID
- list_knowledge_base_stats(): Show what's indexed

Indicator Selection Tools:
- find_indicators_by_principle(principle, include_criteria): Find indicators by CBA principle (1-7 or name like "Natural Environment")
- find_feasible_methods(indicator, max_cost, min_ease, min_accuracy): Filter methods by practical constraints
- list_indicators_by_component(component): Browse indicators by component (Biotic, Abiotic, Socio-economic)
- list_available_classes(): Discover all indicator classes (Biodiversity, Soil carbon, etc.)
- find_indicators_by_class(class_name): List indicators in a specific class
- find_indicators_by_measurement_approach(approach): Find indicators measurable via field/lab/remote/participatory/audit methods
- compare_indicators(indicator_ids): Side-by-side comparison of 2-5 indicators
- export_indicator_selection(indicator_ids, include_methods): Generate markdown report of selected indicators

Use Case Examples (Real Projects):
- search_usecases(query, n_results): Find example projects by commodity, country, or outcome
- get_usecase_details(use_case_slug): Get full project details with all outcomes and indicators
- get_usecases_by_indicator(indicator): Find projects that used a specific indicator (by ID or name)

**CRITICAL WORKFLOW for Location-Based Farming/Agriculture Questions:**

When a user asks about farming, agriculture, or indicators for a specific location, you MUST follow this sequence:

1. **GATHER CONTEXT FIRST** - Call these tools to understand the location:
   - get_climate_data(location) - to understand rainfall, temperature patterns
   - get_current_weather(location) - for current conditions
   - get_country_indicators(country) - for socio-economic context

2. **SEARCH RELEVANT INDICATORS** - Based on the context gathered:
   - search_indicators(query, n_results=5-10) - search for indicators relevant to the crop/activity AND the climate/conditions discovered
   - find_indicators_by_principle(principle) - if user mentions specific sustainability goals

3. **GET MEASUREMENT METHODS** - For each recommended indicator:
   - find_feasible_methods(indicator, max_cost, min_ease) - filter by practical constraints
   - Include method accuracy, ease of use, and cost in your recommendations

4. **SYNTHESIZE AND RECOMMEND** - Combine all data to provide:
   - Top indicators ranked by relevance to the location's climate and conditions
   - Specific measurement methods for each indicator
   - Explain WHY each indicator matters given the local context (climate, rainfall, etc.)

**Example workflow for "wheat farm in Cheshire":**
1. Call get_climate_data("Cheshire") → learn about rainfall, temperatures
2. Call get_country_indicators("UK") → economic context
3. Call search_indicators("wheat crop soil yield agriculture") → find relevant indicators
4. Call search_methods("soil measurement wheat") → get measurement approaches
5. Combine: recommend indicators suited to Cheshire's wet climate with practical methods

When users ask questions:
1. ALWAYS call tools to get real data - never just describe what you would do
2. Provide clear, well-formatted responses based on the tool results
3. Include BOTH indicators AND their measurement methods in recommendations
4. Explain your reasoning based on the location's actual climate/economic data

Be conversational and helpful. Do NOT ask users to make tool calls - you make them yourself."""


def create_agent(
    model_id: str = "llama3.1", host: str = "http://localhost:11434"
) -> Agent:
    """Create and configure the Strands agent with Ollama and tools."""

    # Configure Ollama model
    ollama_model = OllamaModel(
        host=host,
        model_id=model_id,
        temperature=0.7,
    )

    # Configure conversation memory - keep more messages for context
    conversation_manager = SlidingWindowConversationManager(
        window_size=40,  # Keep up to 40 message pairs
    )

    # Create agent with all tools and conversation memory
    agent = Agent(
        model=ollama_model,
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=conversation_manager,
        tools=[
            # Weather & Climate
            get_current_weather,
            get_weather_forecast,
            get_climate_data,
            get_historical_climate,
            # Socio-economic
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
        ],
    )

    return agent


def print_banner():
    """Print the welcome banner."""
    print("\n" + "=" * 60)
    print("🌍 Data Assistant - Weather, Climate, CBA Indicators")
    print("=" * 60)
    print("\nPowered by Strands Agents + Ollama")
    print("\nI can help you with:")
    print("  🌤️  Current weather and forecasts")
    print("  📊  Climate data and historical records")
    print("  🌐  Country information and economic indicators")
    print("  📋  CBA ME Indicators and measurement methods")
    print("  📊  Climate data and historical records")
    print("  🌐  Country information and economic indicators")
    print("\nType 'quit' or 'exit' to end the conversation.")
    print("Type 'help' for example queries.")
    print("-" * 60 + "\n")


def print_help():
    """Print example queries."""
    print("\n📖 Example Queries:\n")
    print("Weather:")
    print("  • What's the weather in Tokyo?")
    print("  • Give me a 5-day forecast for London")
    print("")
    print("Climate:")
    print("  • What are the climate normals for Sydney?")
    print("  • How was the weather in Paris in 2020?")
    print("")
    print("Socio-Economic:")
    print("  • Tell me about Japan")
    print("  • What's the GDP of Germany?")
    print("  • Compare life expectancy in Sweden and USA")
    print("  • Show unemployment data for Brazil")
    print("")


def main():
    """Main entry point for the CLI chatbot."""
    import sys

    # Parse command line arguments
    model_id = "llama3.1"
    host = "http://localhost:11434"

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith("--model="):
            model_id = arg.split("=")[1]
        elif arg.startswith("--host="):
            host = arg.split("=")[1]
        elif arg in ["-h", "--help"]:
            print("Usage: python main.py [--model=MODEL_ID] [--host=OLLAMA_HOST]")
            print("\nOptions:")
            print("  --model=MODEL_ID   Ollama model to use (default: llama3.1)")
            print(
                "  --host=HOST        Ollama server URL (default: http://localhost:11434)"
            )
            print("\nExample:")
            print("  python main.py --model=mistral --host=http://localhost:11434")
            sys.exit(0)

    print_banner()

    print(f"🔧 Connecting to Ollama ({host}) with model: {model_id}...")

    try:
        agent = create_agent(model_id=model_id, host=host)
        print("✅ Agent ready!\n")
    except Exception as e:
        print(f"\n❌ Error: Could not connect to Ollama at {host}")
        print(f"   Make sure Ollama is running: ollama serve")
        print(f"   And the model is pulled: ollama pull {model_id}")
        print(f"\n   Details: {e}")
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
            response = agent(user_input)

            print("\n")  # Add spacing after response

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
