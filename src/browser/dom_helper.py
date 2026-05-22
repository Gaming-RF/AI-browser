"""
DOM Helper

Cleans raw page HTML into a compact, LLM-friendly representation.
Interactive elements are tagged with numeric IDs so the agent can
reference them by number (e.g., "click [3]").
"""

from typing import List, Dict, Any

try:
    from bs4 import BeautifulSoup, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# Tags to strip entirely (content is not useful for the agent)
_STRIP_TAGS = {
    "script", "style", "svg", "path", "noscript", "meta", "link",
    "head", "iframe", "object", "embed",
}

# Tags that represent interactive elements the agent can act on
_INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea"}

# Attributes worth keeping for context
_KEEP_ATTRS = {
    "href", "placeholder", "aria-label", "title", "alt", "name",
    "type", "value", "role", "id",
}


def clean_html(raw_html: str, max_length: int = 12000) -> str:
    """
    Convert raw page HTML into a compact text representation.

    Returns a string with two sections:
      1. INTERACTIVE ELEMENTS — numbered list the agent can reference.
      2. PAGE TEXT — visible text trimmed to *max_length* characters.

    Args:
        raw_html: The full page HTML string.
        max_length: Maximum character length for the page text section.

    Returns:
        A cleaned string suitable for inclusion in an LLM prompt.
    """
    if not HAS_BS4:
        # Fallback: return truncated raw HTML
        return raw_html[:max_length]

    soup = BeautifulSoup(raw_html, "html.parser")

    # ── Strip non-useful tags ──────────────────────────────
    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # ── Collect interactive elements ───────────────────────
    elements: List[Dict[str, Any]] = []
    idx = 1
    for tag in soup.find_all(_INTERACTIVE_TAGS):
        if not isinstance(tag, Tag):
            continue

        elem: Dict[str, Any] = {
            "id": idx,
            "tag": tag.name,
        }

        # Gather useful attributes
        for attr in _KEEP_ATTRS:
            val = tag.get(attr)
            if val:
                if isinstance(val, list):
                    val = " ".join(val)
                elem[attr] = val

        # Visible text inside the element (trimmed)
        inner_text = tag.get_text(strip=True)[:120]
        if inner_text:
            elem["text"] = inner_text

        # CSS selector for Playwright
        tag_id = tag.get("id")
        tag_name_attr = tag.get("name")
        if tag_id:
            elem["selector"] = f"#{tag_id}"
        elif tag_name_attr:
            elem["selector"] = f'{tag.name}[name="{tag_name_attr}"]'
        else:
            # Build a best-effort selector
            elem["selector"] = _build_selector(tag)

        elements.append(elem)
        idx += 1

    # ── Build interactive elements section ─────────────────
    lines = ["INTERACTIVE ELEMENTS:"]
    for el in elements:
        parts = [f"[{el['id']}]", f"<{el['tag']}>"]
        if el.get("text"):
            parts.append(f'"{el["text"]}"')
        for attr in ("href", "placeholder", "aria-label", "type", "value", "role"):
            if attr in el:
                parts.append(f'{attr}="{el[attr]}"')
        parts.append(f'selector="{el["selector"]}"')
        lines.append("  " + " ".join(parts))

    if len(elements) == 0:
        lines.append("  (none found)")

    # ── Build page text section ────────────────────────────
    page_text = soup.get_text(separator="\n", strip=True)
    # Collapse multiple blank lines
    cleaned_lines = []
    for line in page_text.splitlines():
        stripped = line.strip()
        if stripped:
            cleaned_lines.append(stripped)
    page_text = "\n".join(cleaned_lines)

    if len(page_text) > max_length:
        page_text = page_text[:max_length] + "\n... (truncated)"

    lines.append("")
    lines.append("PAGE TEXT:")
    lines.append(page_text)

    return "\n".join(lines)


def _build_selector(tag: "Tag") -> str:
    """Build a best-effort CSS selector for an element."""
    parts = [tag.name]

    # Add class-based specificity
    classes = tag.get("class", [])
    if classes:
        # Use the first two classes at most
        for cls in classes[:2]:
            if cls and not cls.startswith("_"):
                parts.append(f".{cls}")

    # Add aria-label if present
    aria = tag.get("aria-label")
    if aria:
        parts.append(f'[aria-label="{aria}"]')

    return "".join(parts)
