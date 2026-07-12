import os

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


def test_format_divergence_alert_includes_direction_strength_ticker_and_price():
    text = telegram.format_divergence_alert("AAPL", "1d", "bullish", "strong", 123.45)
    assert "BULLISH" in text
    assert "STRONG" in text
    assert "AAPL" in text
    assert "1d" in text
    assert "123.45" in text


def test_format_divergence_alert_labels_weak_signals():
    text = telegram.format_divergence_alert("AAPL", "1d", "bullish", "weak", 123.45)
    assert "weak" in text


def test_send_message_reaches_telegram():
    telegram.send_message("Axe scanner: test message from the pytest suite — setup verified.")


def test_send_divergence_alert_reaches_telegram():
    telegram.send_divergence_alert("AAPL", "1d", "bullish", "strong", 123.45)
