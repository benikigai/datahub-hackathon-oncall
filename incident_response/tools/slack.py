"""Slack webhook helper for the Fixer agent's postmortem post.

If SLACK_WEBHOOK_URL is unset, falls back to printing to stderr so the demo
still works without a real Slack workspace configured.
"""
import os
import sys
import httpx


def post(text: str, *, channel: str = "#data-incidents") -> dict:
    """Post a message via Slack incoming webhook.
    Returns {"sent": bool, "channel": str, ...}.
    Falls back to stderr if no webhook URL configured.
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print(f"[slack disabled] would post to {channel}:\n{text}", file=sys.stderr)
        return {"sent": False, "channel": channel, "fallback": "stderr"}
    try:
        r = httpx.post(
            webhook_url,
            json={"text": text, "channel": channel},
            timeout=5.0,
        )
        return {"sent": r.status_code == 200, "channel": channel, "status": r.status_code}
    except Exception as e:
        print(f"[slack error] {e}\nfallback to stderr:\n{text}", file=sys.stderr)
        return {"sent": False, "channel": channel, "error": str(e)}


if __name__ == "__main__":
    result = post("smoke test from incident_response.tools.slack")
    print(result)
