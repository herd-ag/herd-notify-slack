"""Tests for SlackNotifyAdapter."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from herd_notify_slack import SlackNotifyAdapter


class TestSlackNotifyAdapter:
    """Test suite for SlackNotifyAdapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = SlackNotifyAdapter(token="xoxb-test", default_channel="#test")
        assert adapter.token == "xoxb-test"
        assert adapter.default_channel == "#test"

    def test_post_success(self):
        """Test successful message posting."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "ts": "1234567890.123456", "channel": "C123456"}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = adapter.post(
                "Test message", channel="#test", username="TestBot", icon=":robot:"
            )

        assert result.message_id == "1234567890.123456"
        assert result.channel == "C123456"
        assert result.timestamp == "1234567890.123456"

    def test_post_uses_default_channel(self):
        """Test posting with default channel."""
        adapter = SlackNotifyAdapter(token="xoxb-test", default_channel="#default")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "ts": "1234567890.123456", "channel": "C123456"}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            adapter.post("Test message")

            # Verify request was made with default channel
            request = mock_open.call_args[0][0]
            payload = json.loads(request.data)
            assert payload["channel"] == "#default"

    def test_post_error(self):
        """Test posting with API error."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": False, "error": "invalid_auth"}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="invalid_auth"):
                adapter.post("Test message")

    def test_post_thread_success(self):
        """Test successful thread reply."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "ts": "1234567890.123457", "channel": "C123456"}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = adapter.post_thread(
                thread_id="1234567890.123456", message="Reply", channel="#test"
            )

        assert result.message_id == "1234567890.123457"
        assert result.channel == "C123456"
        assert result.timestamp == "1234567890.123457"

    def test_get_thread_replies_success(self):
        """Test fetching thread replies."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "ok": True,
                "messages": [
                    {
                        "user": "U123",
                        "text": "Parent message",
                        "ts": "1234567890.123456",
                    },
                    {
                        "user": "U456",
                        "text": "First reply",
                        "ts": "1234567890.123457",
                    },
                    {
                        "user": "U789",
                        "text": "Second reply",
                        "ts": "1234567890.123458",
                    },
                ],
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response):
            replies = adapter.get_thread_replies(
                channel="C123456", thread_id="1234567890.123456"
            )

        assert len(replies) == 2  # Excludes parent
        assert replies[0].author == "U456"
        assert replies[0].text == "First reply"
        assert replies[1].author == "U789"
        assert replies[1].text == "Second reply"

    def test_get_thread_replies_no_replies(self):
        """Test fetching thread with no replies."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "ok": True,
                "messages": [
                    {
                        "user": "U123",
                        "text": "Parent message",
                        "ts": "1234567890.123456",
                    }
                ],
            }
        ).encode()

        with patch("urllib.request.urlopen", return_value=mock_response):
            replies = adapter.get_thread_replies(
                channel="C123456", thread_id="1234567890.123456"
            )

        assert len(replies) == 0

    def test_get_thread_replies_error(self):
        """Test fetching thread replies with error."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": False}).encode()

        with patch("urllib.request.urlopen", return_value=mock_response):
            replies = adapter.get_thread_replies(
                channel="C123456", thread_id="1234567890.123456"
            )

        assert len(replies) == 0

    def test_search_success(self):
        """Test successful message search."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "user": "U123",
                            "text": "Found message 1",
                            "ts": "1234567890.123456",
                        },
                        {
                            "username": "bot",
                            "text": "Found message 2",
                            "ts": "1234567890.123457",
                        },
                    ]
                },
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = adapter.search("test query")

        assert len(results) == 2
        assert results[0].author == "U123"
        assert results[0].text == "Found message 1"
        assert results[1].author == "bot"
        assert results[1].text == "Found message 2"

    def test_search_with_channel_filter(self):
        """Test search with channel filter."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "messages": {"matches": []}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            adapter.search("test query", channel="#specific")

            # Verify query includes channel filter
            request = mock_open.call_args[0][0]
            assert "in%3A%23specific" in request.full_url

    def test_search_with_since_filter(self):
        """Test search with since filter."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "messages": {"matches": []}}
        ).encode()

        since = datetime(2026, 2, 14)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            adapter.search("test query", since=since)

            # Verify query includes date filter
            request = mock_open.call_args[0][0]
            assert "after%3A2026-02-14" in request.full_url

    def test_search_with_limit(self):
        """Test search respects limit."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        # Return more results than limit
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "user": f"U{i}",
                            "text": f"Message {i}",
                            "ts": f"1234567890.{i}",
                        }
                        for i in range(100)
                    ]
                },
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = adapter.search("test query", limit=10)

        assert len(results) == 10

    def test_search_error(self):
        """Test search with error."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": False}).encode()

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = adapter.search("test query")

        assert len(results) == 0

    def test_protocol_compliance(self):
        """Test that SlackNotifyAdapter satisfies NotifyAdapter protocol."""
        from herd_core.adapters.notify import NotifyAdapter

        adapter = SlackNotifyAdapter(token="xoxb-test")
        assert isinstance(adapter, NotifyAdapter)

    def test_http_error_handling(self):
        """Test HTTP error handling."""
        import urllib.error

        adapter = SlackNotifyAdapter(token="xoxb-test")

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="test",
                code=401,
                msg="Unauthorized",
                hdrs={},  # type: ignore
                fp=None,
            ),
        ):
            with pytest.raises(RuntimeError, match="HTTP error: 401"):
                adapter.post("Test message")

    def test_network_error_handling(self):
        """Test network error handling."""
        adapter = SlackNotifyAdapter(token="xoxb-test")

        with patch(
            "urllib.request.urlopen", side_effect=Exception("Network error")
        ):
            with pytest.raises(RuntimeError, match="Request failed"):
                adapter.post("Test message")
