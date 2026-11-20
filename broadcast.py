import argparse
from datetime import date
from dotenv import load_dotenv
import utils


def execute_broadcast(
    send_msg: bool = True,
    send_poll: bool | None = None,
    reference_date: date | None = None,
) -> None:
  token = utils.get_required_env("TELEGRAM_BOT_TOKEN")
  chat_id = utils.get_required_env("TELEGRAM_CHAT_ID")
  config = utils.load_config()

  today = reference_date or date.today()
  target_weekday = utils.parse_weekday(config["session"]["weekday"])
  session_date = utils.get_next_session_date(today, target_weekday)
  context = utils.build_template_context(config, today, session_date)

  should_poll = (
      send_poll
      if send_poll is not None
      else config.get("poll", {}).get("enabled", False)
  )

  if send_msg:
    send_message(token, chat_id, config, context)

  if should_poll:
    send_poll_to_chat(token, chat_id, config, context)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
      description="Send Smash club announcements and polls to Telegram."
  )
  parser.add_argument(
      "-m", "--message", action="store_true", help="Send only the announcement."
  )
  parser.add_argument(
      "-p", "--poll", action="store_true", help="Send only the poll."
  )
  return parser.parse_args()


def main_cli() -> None:
  args = parse_args()
  load_dotenv()

  no_flags = not args.message and not args.poll
  execute_broadcast(
      send_msg=args.message or no_flags,
      send_poll=True if args.poll else (None if no_flags else False),
  )


if __name__ == "__main__":
  main_cli()