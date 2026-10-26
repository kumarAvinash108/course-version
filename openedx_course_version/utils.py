"""Pure helpers for the course-version tag (no edx imports: unit-testable)."""

MAX_LABEL_LEN = 120


def clean_text(value):
    """Strip whitespace; coerce None/non-str to empty string."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def build_tag_label(version="", version_of=""):
    """
    Build the human-readable pill text.

    Examples:
        ("v2.0", "CS101") -> "CS101 • Version v2.0"
        ("v2.0", "")      -> "Version v2.0"
        ("", "CS101")     -> "CS101"
        ("", "")          -> ""
    """
    version = clean_text(version)
    version_of = clean_text(version_of)
    if version and version_of:
        label = f"{version_of} • Version {version}"
    elif version:
        label = f"Version {version}"
    else:
        label = version_of
    if len(label) > MAX_LABEL_LEN:
        label = label[: MAX_LABEL_LEN - 1] + "…"
    return label


def should_display_tag(version="", version_of="", show_tag=True):
    """Tag is visible only when enabled AND at least one text field is set."""
    if not show_tag:
        return False
    return bool(build_tag_label(version, version_of))


def version_payload(course_id="", version="", version_of="", show_tag=True):
    """Shape returned by the REST API (single source of truth for frontends)."""
    label = build_tag_label(version, version_of)
    return {
        "course_id": str(course_id),
        "version": clean_text(version),
        "version_of": clean_text(version_of),
        "show_tag": bool(show_tag),
        "display": should_display_tag(version, version_of, show_tag),
        "tag_label": label,
    }
