from dotenv import load_dotenv
load_dotenv()

import asyncio
import re
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# -----------------------------
# Gemini (fallback only)
# -----------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

# -----------------------------
# MCP server config
# -----------------------------
server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)

# -----------------------------
# State
# -----------------------------
user_name = None


# -----------------------------
# Helpers
# -----------------------------
def extract_city(text: str):
    match = re.search(r"(?:in|at)\s+([a-zA-Z\s]+)", text)
    return match.group(1).strip() if match else None


def parse_tool_result(result):
    """
    MCP CallToolResult → dict or string
    """
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

                parts = [p.strip() for p in user_input.split(",") if p.strip()]
                responses = []

                for part in parts:
                    p = part.lower()

                    # -------- GREETING --------
                    if re.fullmatch(r"(hi|hello|hey)", p):
                        responses.append("Hi there! 😊 How can I help you?")
                        continue

                    # -------- NAME MEMORY --------
                    m = re.search(r"my name is (\w+)", p)
                    if m:
                        user_name = m.group(1).capitalize()
                        responses.append(f"Nice to meet you, {user_name}! 😊")
                        continue

                    if user_name and "my name" in p:
                        responses.append(f"Your name is {user_name}.")
                        continue

                    # -------- WEATHER --------
                    if any(k in p for k in ["weather", "climate", "temperature", "wind"]):
                        city = extract_city(p)
                        if not city:
                            responses.append("Please specify a city (e.g., weather in guntur).")
                            continue

                        result = await session.call_tool(
                            "get_weather",
                            arguments={"input": {"city": city}}
                        )
                        data = parse_tool_result(result)

                        if isinstance(data, dict):
                            responses.append(
                                f"🌤 Weather in {city.title()}:\n"
                                f"• Temperature: {data['temperature_c']} °C\n"
                                f"• Wind Speed: {data['wind_speed']} km/h"
                            )
                        else:
                            responses.append(f"Weather info: {data}")
                        continue

                    # -------- VOWELS --------
                    if "vowel" in p:
                        word = re.sub(r"(vowels?|count|in|:)", "", p).strip()
                        if not word:
                            responses.append("Please give a word (e.g., vowels in terralogic).")
                            continue

                        result = await session.call_tool(
                            "count_vowels",
                            arguments={"input": {"text": word}}
                        )
                        data = parse_tool_result(result)

                        responses.append(
                            f"🔤 Vowels in '{word}': {data['vowel_count']}\n"
                            f"• Letters: {', '.join(data['vowels'])}"
                        )
                        continue

                    # -------- SYSTEM --------
                    if any(k in p for k in ["cpu", "memory", "ram", "disk", "system", "os"]):
                        result = await session.call_tool(
                            "system_diagnostics",
                            arguments={"input": {"detail": p}}
                        )
                        data = parse_tool_result(result)

                        if "cpu" in p:
                            responses.append(
                                f"⚙ CPU Info:\n"
                                f"• Usage: {data['cpu_usage_percent']}%\n"
                                f"• Physical cores: {data['cpu_physical_cores']}\n"
                                f"• Logical cores: {data['cpu_logical_cores']}"
                            )
                            continue

                        if "memory" in p or "ram" in p:
                            responses.append(
                                f"🧠 Memory Info:\n"
                                f"• Total: {data['memory_total_gb']} GB\n"
                                f"• Used: {data['memory_used_gb']} GB\n"
                                f"• Free: {data['memory_free_gb']} GB\n"
                                f"• Usage: {data['memory_usage_percent']}%"
                            )
                            continue

                        if "disk" in p:
                            responses.append(
                                f"💾 Disk Info:\n"
                                f"• Total: {data['disk_total_gb']} GB\n"
                                f"• Used: {data['disk_used_gb']} GB\n"
                                f"• Free: {data['disk_free_gb']} GB"
                            )
                            continue

                        responses.append(
                            f"🖥 System Info:\n"
                            f"• OS: {data['os']} {data['os_version']}\n"
                            f"• Architecture: {data['architecture']}\n"
                            f"• Uptime: {data['system_uptime_hours']} hours"
                        )
                        continue

                    # -------- FALLBACK --------
                    responses.append(
                        "Sorry, I don’t have access to that information with my current tools."
                    )

                print("Agent:", "\n\n".join(responses))


if __name__ == "__main__":
    asyncio.run(main())
