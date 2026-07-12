import os

import pandas as pd
import pytest

import telegram

HAS_CREDENTIALS = bool(os.environ.get("TELEGRAM_BOT_TOKEN")) and bool(
    os.environ.get("TELEGRAM_CHAT_ID")
)

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set — copy scanner/.env.example "
    "to scanner/.env and fill in your bot token and chat id to run this test",
)

PIVOT_1_TS = pd.Timestamp("2026-07-07 13:30:00", tz="UTC")
PIVOT_2_TS = pd.Timestamp("2026-07-08 09:00:00", tz="UTC")


def test_format_divergence_alert_includes_direction_strength_ticker_price_and_dates():
    text = telegram.format_divergence_alert("AAPL", "1d", "bullish", "strong", 123.45, PIVOT_1_TS, PIVOT_2_TS)
    assert "BULLISH" in text
    assert "STRONG" in text
    assert "AAPL" in text
    assert "1d" in text
    assert "123.45" in text

    lines = {line.split(": ", 1)[0]: line.split(": ", 1)[1] for line in text.splitlines() if ": " in line}
    # Dates only (ET), no time-of-day.
    assert lines["Pivot 1"] == "Jul 07"
    assert lines["Pivot 2"] == "Jul 08"


def test_format_divergence_alert_labels_weak_signals():
    text = telegram.format_divergence_alert("AAPL", "1d", "bullish", "weak", 123.45, PIVOT_1_TS, PIVOT_2_TS)
    assert "weak" in text


def test_send_message_reaches_telegram():
    telegram.send_message("Axe scanner: test message from the pytest suite — setup verified.")


def test_send_divergence_alert_reaches_telegram():
    telegram.send_divergence_alert("AAPL", "1d", "bullish", "strong", 123.45, PIVOT_1_TS, PIVOT_2_TS)
