from dotenv import load_dotenv
load_dotenv()

import asyncio
import re
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

# MCP server config
server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)

user_name = None


def extract_city(text: str):
    match = re.search(r"(?:in|at)\s+([a-zA-Z\s]+)", text, re.I)
    if not match:
        return None

    city = match.group(1).strip().title()

    # common misspellings
    fixes = {
        "Banglore": "Bangalore",
        "Hydrabad": "Hyderabad",
        "Chenai": "Chennai"
    }

    return fixes.get(city, city)


def parse_tool_result(result):
    if not result or not result.content:
        return None

    text = "\n".join(c.text for c in result.content if hasattr(c, "text")).strip()
    try:
        return json.loads(text)
    except Exception:
        return text


# -----------------------------
# Main loop
# -----------------------------
async def main():
    global user_name

    print("🤖 Multi-Tool MCP Agent started (type 'exit' to quit)\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            while True:
                user_input = input("User: ").strip()
                if user_input.lower() == "exit":
                    break

                p = user_input.lower()

                # -------- GREETING --------
                if re.fullmatch(r"(hi|hello|hey)", p):
                    print("Agent: Hi there! 😊 How can I help you?")
                    continue

                # -------- NAME MEMORY --------
                m = re.search(r"(my name is|i am|iam)\s+(\w+)", p)
                if m:
                    user_name = m.group(2).capitalize()
                    print(f"Agent: Nice to meet you, {user_name}! 😊")
                    continue

                if "my name" in p:
                    if user_name:
                        print(f"Agent: Your name is {user_name}.")
                    else:
                        print("Agent: I don’t know your name yet.")
                    continue

                # -------- WEATHER TOOL --------
                if any(k in p for k in ["weather", "climate", "temperature", "wind"]):
                    city = extract_city(user_input)
                    if not city:
                        print("Agent: Please specify a city (e.g., weather in Hyderabad).")
                        continue

                    result = await session.call_tool(
                        "get_weather",
                        arguments={"input": {"city": city}}
                    )
                    data = parse_tool_result(result)

                    if isinstance(data, dict):
                        print(
                            f"Agent: 🌤 Weather in {city}\n"
                            f"• Temperature: {data['temperature_c']} °C\n"
                            f"• Wind Speed: {data['wind_speed']} km/h"
                        )
                    else:
                        print(f"Agent: {data}")
                    continue

                # -------- VOWELS TOOL --------
                if "vowel" in p:
                    word = re.sub(r"(vowels?|count|in|:)", "", p).strip()
                    if not word:
                        print("Agent: Please give a word (e.g., vowels in likhita).")
                        continue

                    result = await session.call_tool(
                        "count_vowels",
                        arguments={"input": {"text": word}}
                    )
                    data = parse_tool_result(result)

                    print(
                        f"Agent:  Vowels in '{word}': {data['vowel_count']}\n"
                        f"• Letters: {', '.join(data['vowels'])}"
                    )
                    continue

                # -------- SYSTEM TOOL --------
                if any(k in p for k in ["cpu", "memory", "ram", "disk", "system", "os"]):
                    result = await session.call_tool(
                        "system_diagnostics",
                        arguments={"input": {"detail": p}}
                    )
                    data = parse_tool_result(result)

                    print(
                        f"Agent:  System Info\n"
                        f"• Total: {data['memory_total_gb']} GB\n"
                        f"• Used: {data['memory_used_gb']} GB\n"
                        f"• Free: {data['memory_free_gb']} GB\n"
                        f"• Usage: {data['memory_usage_percent']}%"
                    )
                    continue

                print("Agent: Sorry, I don’t have access to that information with my current tools.")


if __name__ == "__main__":
    asyncio.run(main())
