"""Slack implementation of NotifyAdapter protocol."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from herd_core.types import PostResult, ThreadMessage


class SlackNotifyAdapter:
    """Slack notification adapter implementing NotifyAdapter protocol.

    Uses stdlib urllib — no external HTTP dependencies.

    Args:
        token: Slack API token (xoxb-...).
        default_channel: Default channel for posts (e.g., "#herd-feed").
    """

    def __init__(self, token: str, default_channel: str = "#herd-feed"):
        self.token = token
        self.default_channel = default_channel

    def post(
        self,
        message: str,
        *,
        channel: str | None = None,
        username: str | None = None,
        icon: str | None = None,
    ) -> PostResult:
        """Post a message to a channel.

        Args:
            message: Message content.
            channel: Target channel. Defaults to the primary feed channel.
            username: Display name for this post.
            icon: Emoji icon for this post (e.g., ":hammer:").

        Returns:
            PostResult with message_id and timestamp.

        Raises:
            RuntimeError: On authentication failure or API error.
        """
        channel = channel or self.default_channel

        payload: dict[str, Any] = {
            "channel": channel,
            "text": message,
        }

        if username:
            payload["username"] = username
        if icon:
            payload["icon_emoji"] = icon

        result = self._api_call("chat.postMessage", payload)

        if not result.get("ok"):
            error = result.get("error", "unknown error")
            raise RuntimeError(f"Slack API error: {error}")

        return PostResult(
            message_id=result["ts"],
            channel=result["channel"],
            timestamp=result["ts"],
        )

    def post_thread(
        self,
        thread_id: str,
        message: str,
        *,
        channel: str | None = None,
    ) -> PostResult:
        """Reply to an existing thread.

        Args:
            thread_id: Parent message timestamp (ts).
            message: Reply content.
            channel: Target channel (required if not default).

        Returns:
            PostResult with message_id and timestamp.

        Raises:
            RuntimeError: On authentication failure or API error.
        """
        channel = channel or self.default_channel

        payload = {
            "channel": channel,
            "text": message,
            "thread_ts": thread_id,
        }

        result = self._api_call("chat.postMessage", payload)

        if not result.get("ok"):
            error = result.get("error", "unknown error")
            raise RuntimeError(f"Slack API error: {error}")

        return PostResult(
            message_id=result["ts"],
            channel=result["channel"],
            timestamp=result["ts"],
        )

    def get_thread_replies(
        self,
        channel: str,
        thread_id: str,
    ) -> list[ThreadMessage]:
        """Fetch all replies in a thread (excluding the parent message).

        Args:
            channel: Channel containing the thread.
            thread_id: Parent message timestamp (ts).

        Returns:
            List of thread replies, or empty list if not found.
        """
        params = urllib.parse.urlencode({"channel": channel, "ts": thread_id})
        url = f"https://slack.com/api/conversations.replies?{params}"

        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
            )

            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())

            if not result.get("ok"):
                return []

            messages = result.get("messages", [])
            # Filter out parent message (first message)
            replies = messages[1:] if len(messages) > 1 else []

            return [
                ThreadMessage(
                    author=msg.get("user", "unknown"),
                    text=msg.get("text", ""),
                    timestamp=msg.get("ts", ""),
                )
                for msg in replies
            ]
        except Exception:
            return []

    def search(
        self,
        query: str,
        *,
        channel: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[ThreadMessage]:
        """Search messages in a channel.

        Args:
            query: Search query string.
            channel: Restrict to a specific channel.
            since: Only messages after this timestamp.
            limit: Maximum results to return.

        Returns:
            Matching messages, most recent first.
        """
        # Build search query with filters
        search_query = query
        if channel:
            search_query = f"{query} in:{channel}"
        if since:
            # Slack uses YYYY-MM-DD format for date filters
            date_str = since.strftime("%Y-%m-%d")
            search_query = f"{search_query} after:{date_str}"

        params = urllib.parse.urlencode(
            {"query": search_query, "count": min(limit, 100)}
        )
        url = f"https://slack.com/api/search.messages?{params}"

        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
            )

            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())

            if not result.get("ok"):
                return []

            matches = result.get("messages", {}).get("matches", [])

            return [
                ThreadMessage(
                    author=msg.get("user", msg.get("username", "unknown")),
                    text=msg.get("text", ""),
                    timestamp=msg.get("ts", ""),
                )
                for msg in matches[:limit]
            ]
        except Exception:
            return []

    def _api_call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a Slack API call.

        Args:
            method: API method (e.g., "chat.postMessage").
            payload: JSON payload.

        Returns:
            API response as dict.

        Raises:
            RuntimeError: On HTTP error.
        """
        url = f"https://slack.com/api/{method}"
        data = json.dumps(payload).encode()

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP error: {e.code} {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}")
