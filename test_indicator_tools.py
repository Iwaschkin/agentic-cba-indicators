"""Test CBA indicator tool calling with Strands."""

from strands import Agent
from strands.models.ollama import OllamaModel
from tools import (
    export_indicator_selection,
    find_feasible_methods,
    find_indicators_by_principle,
    get_indicator_details,
    list_indicators_by_component,
    search_indicators,
    search_methods,
)


def main():
    model = OllamaModel(
        host="http://localhost:11434",
        model_id="llama3.1:latest",
        temperature=0.1,
        options={"num_ctx": 8192},
    )

    agent = Agent(
        model=model,
        system_prompt="""You are a CBA indicators assistant. Use tools to answer questions about indicators and measurement methods. Never ask clarifying questions - just call the tools.""",
        tools=[
            search_indicators,
            search_methods,
            get_indicator_details,
            find_indicators_by_principle,
            find_feasible_methods,
            list_indicators_by_component,
            export_indicator_selection,
        ],
    )

    print("Testing CBA indicator tools...")
    print("-" * 40)

    response = agent("Find soil health indicators")
    print(f"Response: {response}")

    print("-" * 40)

    response = agent("What methods can measure indicator 107?")
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
