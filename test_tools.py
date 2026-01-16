"""Test tool calling with Ollama and Strands."""

from strands import Agent, tool
from strands.models.ollama import OllamaModel


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name
    """
    return f"Weather in {city}: 20°C, Sunny"


@tool
def calculate(expression: str) -> str:
    """Calculate a math expression.

    Args:
        expression: The math expression to evaluate
    """
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


def main():
    model = OllamaModel(
        host="http://localhost:11434",
        model_id="llama3.1:latest",
        temperature=0.1,
    )

    agent = Agent(
        model=model,
        system_prompt="You are a helpful assistant. Use tools when needed.",
        tools=[get_weather, calculate],
    )

    print("Testing tool calling...")
    print("-" * 40)

    response = agent("What's the weather in London?")
    print(f"Response: {response}")

    print("-" * 40)

    response = agent("What is 25 * 4?")
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
