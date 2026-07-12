import os

import requests

API_BASE = "https://api.telegram.org"


def _get_credentials():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set. "
            "Copy scanner/.env.example to scanner/.env and fill them in."
        )
    return token, chat_id


def send_message(text: str) -> None:
    token, chat_id = _get_credentials()
    response = requests.post(
        f"{API_BASE}/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10,
    )
    response.raise_for_status()


def format_divergence_alert(ticker: str, timeframe: str, direction: str, strength: str, price: float) -> str:
    strength_label = "STRONG" if strength == "strong" else "weak"
    lines = [
        f"<b>{direction.upper()} divergence</b> ({strength_label}) — {ticker} ({timeframe})",
        f"Price at signal: {price:.2f}",
    ]
    dashboard_url = os.environ.get("DASHBOARD_URL")
    if dashboard_url:
        lines.append(f'<a href="{dashboard_url.rstrip("/")}/symbol/{ticker}">Compare timeframes</a>')
    return "\n".join(lines)


def send_divergence_alert(ticker: str, timeframe: str, direction: str, strength: str, price: float) -> None:
    send_message(format_divergence_alert(ticker, timeframe, direction, strength, price))


def send_health_check_alert(hours_since_last_success: float) -> None:
    send_message(
        f"No successful scan in {hours_since_last_success:.1f}h. "
        "Check the GitHub Actions workflow and cron-job.org trigger."
    )
