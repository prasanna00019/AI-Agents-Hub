"""
Platform-specific content formatting engine.

Handles WhatsApp, Telegram, LinkedIn, Twitter/X, and generic fallback.
"""

from __future__ import annotations

import re


def format_for_platform(content: str, platform: str) -> str:
    platform = platform.lower().strip()
    formatters = {
        "whatsapp": _format_whatsapp,
        "telegram": _format_telegram,
        "linkedin": _format_linkedin,
        "twitter": _format_twitter,
    }
    formatter = formatters.get(platform, _format_generic)
    return formatter(content)


def _format_whatsapp(content: str) -> str:
    """
    WhatsApp formatting rules:
    - Bold: *text*
    - Italic: _text_
    - Strikethrough: ~text~
    - Monospace: ```text```
    - Line breaks every 2-3 sentences for readability
    - Soft limit ~4000 chars per message
    """
    # Convert markdown bold **text** → WhatsApp bold *text*
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', content)

    # Convert markdown italic (single underscore already works for WhatsApp)
    # __text__ → _text_
    text = re.sub(r'__(.*?)__', r'_\1_', text)

    # Convert markdown headers to bold text with line break
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert markdown code blocks to WhatsApp monospace
    text = re.sub(r'`([^`]+)`', r'```\1```', text)

    # Remove markdown links, keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _format_telegram(content: str) -> str:
    """
    Telegram MarkdownV2 formatting.
    Telegram supports: *bold*, _italic_, ~strikethrough~, `code`,
    ```pre```, [inline URL](url), ||spoiler||
    """
    # Keep markdown mostly as-is, Telegram handles it well
    text = content

    # Convert headers to bold
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _format_linkedin(content: str) -> str:
    """
    LinkedIn formatting:
    - Professional paragraph structure
    - 3000 char limit
    - Hashtags at end
    - No markdown (LinkedIn strips most of it)
    """
    text = content

    # Remove markdown formatting  
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)

    # Convert headers to plain text with line break
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

    # Remove markdown links, keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Enforce 3000 char limit
    if len(text) > 3000:
        text = text[:2997] + "..."

    return text.strip()


def _format_twitter(content: str) -> str:
    """
    Twitter/X formatting:
    - 280 char limit per tweet
    - Thread format for long content (split by paragraphs)
    """
    # Remove all markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = text.strip()

    if len(text) <= 280:
        return text

    # Create thread format
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    tweets = []
    for i, para in enumerate(paragraphs):
        if len(para) <= 275:
            tweets.append(f"{i+1}/{len(paragraphs)} {para}")
        else:
            # Split long paragraphs
            words = para.split()
            chunk = f"{i+1}/ "
            for word in words:
                if len(chunk) + len(word) + 1 > 275:
                    tweets.append(chunk.strip())
                    chunk = ""
                chunk += word + " "
            if chunk.strip():
                tweets.append(chunk.strip())

    return "\n\n---\n\n".join(tweets)


def _format_generic(content: str) -> str:
    """Fallback: minimal cleanup."""
    return re.sub(r'\n{3,}', '\n\n', content).strip()


def truncate_content(content: str, max_length: int) -> str:
    if len(content) <= max_length:
        return content
    return content[:max_length - 3] + "..."