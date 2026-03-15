def format_for_platform(content: str, platform: str) -> str:
    """
    Format content for a specific platform.

    Args:
        content: The content to format
        platform: Target platform (whatsapp, telegram, linkedin, etc.)

    Returns:
        Formatted content
    """
    if platform.lower() == "whatsapp":
        # Apply WhatsApp formatting rules
        # Replace markdown bold with WhatsApp bold (*text*)
        # This is a simplified example
        return content.replace("**", "*")
    elif platform.lower() == "telegram":
        # Telegram supports HTML or Markdown
        return content
    elif platform.lower() == "linkedin":
        # LinkedIn formatting
        return content
    else:
        return content

def truncate_content(content: str, max_length: int) -> str:
    """
    Truncate content to a maximum length.

    Args:
        content: The content to truncate
        max_length: Maximum length

    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content
    else:
        return content[:max_length-3] + "..."