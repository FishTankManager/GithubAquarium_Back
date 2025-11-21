import re

def extract_svg_size(svg_text: str):
    """
    Extract width and height from <svg> tag.
    Supports:
      <svg width="512" height="512">
      <svg viewBox="0 0 800 600">
    Returns (width, height) as numbers.
    Defaults to (512, 512) if not found.
    """
    if not svg_text:
        return (512, 512)

    # width="512", height="512"
    width_match = re.search(r'width="([\d\.]+)"', svg_text)
    height_match = re.search(r'height="([\d\.]+)"', svg_text)

    if width_match and height_match:
        return (float(width_match.group(1)), float(height_match.group(1)))

    # viewBox="0 0 800 600"
    viewbox_match = re.search(r'viewBox="[^"]*?(\d+\.?\d*)\s+(\d+\.?\d*)"', svg_text)
    if viewbox_match:
        return (float(viewbox_match.group(1)), float(viewbox_match.group(2)))

    # fallback
    return (512, 512)


def strip_outer_svg(svg_text: str) -> str:
    """
    Removes the <svg> outer wrapper and returns only inner nodes.
    Required because species/background templates are stored as full SVGs.
    """
    if not svg_text:
        return ""

    # Find first tag after <svg ...>
    start = svg_text.find(">") + 1
    end = svg_text.rfind("</svg>")
    return svg_text[start:end].strip()

def safe_attr(value):
    """
    Convert None or empty to safe attribute values.
    """
    if value is None:
        return ""
    return str(value)