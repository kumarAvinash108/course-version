"""Unit tests for the pure version-label helpers (run without edx-platform)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openedx_course_version.utils import build_tag_label, should_display_tag, version_payload


def test_both_fields():
    assert build_tag_label("v2.0", "CS101 - Intro to Python") == "CS101 - Intro to Python • Version v2.0"


def test_version_only():
    assert build_tag_label("v2.0", "") == "Version v2.0"


def test_parent_only():
    assert build_tag_label("", "CS101") == "CS101"


def test_empty():
    assert build_tag_label("", "") == ""
    assert should_display_tag("", "", True) is False
    assert should_display_tag("v2.0", "", False) is False
    assert should_display_tag("v2.0", "", True) is True


def test_payload_shape():
    p = version_payload("course-v1:Org+CS101+2026", "v2.0", "CS101", True)
    assert p["display"] is True
    assert p["tag_label"] == "CS101 • Version v2.0"
    assert p["course_id"] == "course-v1:Org+CS101+2026"


def test_whitespace_and_truncation():
    assert build_tag_label("  v2.0  ", "  CS101  ") == "CS101 • Version v2.0"
    long_version = "v" + "1" * 200
    assert build_tag_label(long_version, "").endswith("…")
