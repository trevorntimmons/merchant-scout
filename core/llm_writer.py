"""Optional: use Claude to turn raw signals into a polished history + angle write-up.

Falls back silently to the rule-based angle if no ANTHROPIC_API_KEY is set, the
`anthropic` package isn't installed, or the API call fails for any reason —
this must never break the pipeline.
"""
import os
from typing import List


def write_pitch_summary(place: dict, explanation: List[str], angle: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return angle

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        name = place.get("displayName", {}).get("text", "This business")
        prompt = (
            f"You are a merchant-services sales assistant. In 2-3 concise sentences, "
            f"summarize why {name} is a good prospect and the best angle to pitch them, "
            f"based on these signals:\n" + "\n".join(explanation) +
            f"\n\nRule-based angle for reference: {angle}\n"
            f"Write in plain, direct language a field sales rep would say out loud. "
            f"No headers, no bullet points."
        )
        msg = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return angle
