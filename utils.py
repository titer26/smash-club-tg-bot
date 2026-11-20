from datetime import date, timedelta
import html
import json
import os
from pathlib import Path
import random
import requests

API_BASE_URL = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def get_required_env(name: str) -> str:
  value = os.getenv(name)
  if not value:
    raise RuntimeError(f"Missing required environment variable: {name}")
  return value


def load_config(path: Path | None = None) -> dict:
  config_path = path or Path(
      os.getenv("SMASHER_CONFIG_PATH", DEFAULT_CONFIG_PATH)
  )
  if not config_path.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_path}")
  with config_path.open("r", encoding="utf-8") as file:
    return json.load(file)


def parse_weekday(weekday_value: str | int) -> int:
  if isinstance(weekday_value, int) and 0 <= weekday_value <= 6:
    return weekday_value
  if isinstance(weekday_value, str):
    normalized = weekday_value.strip().lower()
    if normalized in WEEKDAY_MAP:
      return WEEKDAY_MAP[normalized]
  raise ValueError(f"Invalid weekday value in config: {weekday_value!r}")


def get_next_session_date(reference: date, target_weekday: int) -> date:
  """Returns the next occurrence of target_weekday (or today if it matches)."""
  days_ahead = (target_weekday - reference.weekday()) % 7
  return reference + timedelta(days=days_ahead)


def build_template_context(
    config: dict, reference: date, session_date: date
) -> dict[str, str]:
  locale = config["locale"]
  session = config["session"]

  days_until = (session_date - reference).days
  weekday_name = locale["weekdays"][session_date.weekday()]
  month_name = locale["months"][session_date.month - 1]
  formatted_date = f"{session_date.day} de {month_name}"

  relative_map = locale.get("relative_days", {})
  if str(days_until) in relative_map:
    when_lower = relative_map[str(days_until)]
  else:
    fallback = locale["default_relative_day"]
    when_lower = fallback.format(weekday=weekday_name, days=days_until)

  base_context = {
      "date": formatted_date,
      "weekday": weekday_name,
      "room": session["room"],
      "schedule": session["schedule"],
      "switch_contact": session["switch_contact"],
      "when": when_lower,
      "When": when_lower.capitalize(),
      "WHEN": when_lower.upper(),
  }

  raw_header = random.choice(config["headers"]).format(**base_context)
  return {**base_context, "header": raw_header}


def render_message(template: list[str] | str, context: dict[str, str]) -> str:
  raw_template = "\n".join(template) if isinstance(template, list) else template
  escaped_context = {
      key: html.escape(str(value)) for key, value in context.items()
  }
  return raw_template.format(**escaped_context)


def call_telegram_api(token: str, method: str, payload: dict) -> dict:
  url = f"{API_BASE_URL}/bot{token}/{method}"
  response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)

  if not response.ok:
    raise RuntimeError(
        f"HTTP {response.status_code} error calling {method}: {response.text}"
    )

  data = response.json()
  if not data.get("ok"):
    raise RuntimeError(f"Telegram API rejected {method}: {data}")

  return data