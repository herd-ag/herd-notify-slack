# herd-notify-slack

**Herd notification adapter for Slack.**

Implements the `NotifyAdapter` protocol from [herd-core](https://github.com/dbt-conceptual/herd-core) for posting messages, managing threads, and searching Slack conversations.

Part of [The Herd](https://github.com/herd-ag/herd-core) ecosystem.

## Installation

```bash
pip install herd-notify-slack
```

## Usage

```python
from herd_notify_slack import SlackNotifyAdapter

# Initialize adapter
adapter = SlackNotifyAdapter(
    token="xoxb-...",
    default_channel="#herd-feed"
)

# Post a message
result = adapter.post("Hello from the Herd!")
print(f"Posted at {result.timestamp}")

# Reply to a thread
adapter.post_thread(
    thread_id=result.message_id,
    message="Thread reply"
)

# Get thread replies
replies = adapter.get_thread_replies(
    channel="#herd-feed",
    thread_id=result.message_id
)

# Search messages
results = adapter.search(
    query="DBC-141",
    channel="#herd-feed",
    limit=10
)
```

## Features

- Posts messages to Slack channels
- Thread-based conversations for bidirectional communication
- Search messages with filters (channel, date, limit)
- Protocol compliance with `NotifyAdapter` from herd-core
- No external HTTP dependencies (uses stdlib urllib)
- Full test coverage

## License

MIT
