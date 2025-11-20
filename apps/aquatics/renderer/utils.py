
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