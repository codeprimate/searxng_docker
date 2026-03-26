"""Plain-text content trimming helpers."""

from searxng_mcp.config import CONTENT_TRUNCATED, LINKS_SECTION_MARKER


def truncate_content_with_links(content: str, max_length: int) -> str:
    """Truncate content while preserving links section if present."""
    if max_length is None or len(content) <= max_length:
        return content

    links_section_start = content.find(LINKS_SECTION_MARKER)
    if links_section_start != -1:
        main_content = content[:links_section_start]
        links_section = content[links_section_start:]
        if len(main_content) > max_length:
            main_content = main_content[:max_length] + CONTENT_TRUNCATED
        return main_content + links_section
    return content[:max_length] + CONTENT_TRUNCATED
