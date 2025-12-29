from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import platform
import psutil
import requests
import time
import socket

# Initialize MCP
mcp = FastMCP("demo-tools")

# -------------------------
# WEATHER TOOL
# -------------------------
class WeatherInput(BaseModel):
    city: str

class WeatherOutput(BaseModel):
    city: str
    temperature_c: float
    wind_speed: float

@mcp.tool()
def get_weather(input: WeatherInput) -> WeatherOutput:
    """Fetch real-time weather using Open-Meteo API"""

    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={input.city}&count=1"
    geo_resp = requests.get(geo_url, timeout=10).json()

    if "results" not in geo_resp:
        return WeatherOutput(
            city=input.city,
            temperature_c=0.0,
            wind_speed=0.0
        )

    lat = geo_resp["results"][0]["latitude"]
    lon = geo_resp["results"][0]["longitude"]

    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )

    weather_resp = requests.get(weather_url, timeout=10).json()
    current = weather_resp["current_weather"]

    return WeatherOutput(
        city=input.city,
        temperature_c=current["temperature"],
        wind_speed=current["windspeed"]
    )

# -------------------------
# VOWEL TOOL
# -------------------------
class VowelInput(BaseModel):
    text: str

class VowelOutput(BaseModel):
    vowel_count: int
    vowels: list[str]

@mcp.tool()
def count_vowels(input: VowelInput) -> VowelOutput:
    """Count vowels in a given text"""

    vowels = [ch for ch in input.text.lower() if ch in "aeiou"]

    return VowelOutput(
        vowel_count=len(vowels),
        vowels=vowels
    )

# -------------------------
# SYSTEM DIAGNOSTICS TOOL
# -------------------------
class SystemInput(BaseModel):
    detail: str  # user intent, not mandatory but helps inspector

class SystemOutput(BaseModel):
    hostname: str
    ip_address: str

    os: str
    os_version: str
    architecture: str

    cpu_physical_cores: int
    cpu_logical_cores: int
    cpu_usage_percent: float
    cpu_frequency_mhz: float

    memory_total_gb: float
    memory_used_gb: float
    memory_free_gb: float
    memory_usage_percent: float

    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_usage_percent: float

    system_uptime_hours: float
    running_in_vm: bool

@mcp.tool()
def system_diagnostics(input: SystemInput) -> SystemOutput:
    """
    Provide detailed local system diagnostics.
    Covers OS, CPU, memory, disk, uptime, and VM heuristics.
    """

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_freq = psutil.cpu_freq()
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time

    # Host & IP
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except Exception:
        ip_address = "Unavailable"

    # VM detection heuristic
    vm_keywords = ["virtual", "vmware", "kvm", "hyper-v", "xen"]
    uname = platform.uname().release.lower()
    is_vm = any(word in uname for word in vm_keywords)

    return SystemOutput(
        hostname=hostname,
        ip_address=ip_address,

        os=platform.system(),
        os_version=platform.version(),
        architecture=platform.machine(),

        cpu_physical_cores=psutil.cpu_count(logical=False),
        cpu_logical_cores=psutil.cpu_count(logical=True),
        cpu_usage_percent=psutil.cpu_percent(interval=1),
        cpu_frequency_mhz=cpu_freq.current if cpu_freq else 0.0,

        memory_total_gb=round(mem.total / (1024 ** 3), 2),
        memory_used_gb=round(mem.used / (1024 ** 3), 2),
        memory_free_gb=round(mem.available / (1024 ** 3), 2),
        memory_usage_percent=mem.percent,

        disk_total_gb=round(disk.total / (1024 ** 3), 2),
        disk_used_gb=round(disk.used / (1024 ** 3), 2),
        disk_free_gb=round(disk.free / (1024 ** 3), 2),
        disk_usage_percent=disk.percent,

        system_uptime_hours=round(uptime_seconds / 3600, 2),
        running_in_vm=is_vm
    )

# -------------------------
# RUN MCP SERVER
# -------------------------
if __name__ == "__main__":
    mcp.run()
