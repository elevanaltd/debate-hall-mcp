"""Shared topic validation for debate tools.

Provides consistent topic validation across init_debate and run_debate
tool boundaries (M4: CE Review mitigation).

Extracted to avoid circular imports between init.py and orchestrate.py.
"""

# M4: Maximum topic length (reasonable limit for debate topics)
MAX_TOPIC_LENGTH = 5000


def validate_topic(topic: str) -> None:
    """Validate topic input (M4: CE Review mitigation).

    Args:
        topic: The debate topic to validate

    Raises:
        ValueError: If topic is empty, whitespace-only, or too long
    """
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic exceeds maximum length of {MAX_TOPIC_LENGTH} characters")
