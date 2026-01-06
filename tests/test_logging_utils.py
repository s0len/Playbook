from __future__ import annotations

import pytest

from playbook.logging_utils import (
    LogBlockBuilder,
    _coerce_items,
    _stringify,
    _wrap_text,
    render_fields_block,
    render_section_block,
)


# Tests for helper functions


class TestCoerceItems:
    """Tests for _coerce_items helper function."""

    def test_coerce_items_with_dict(self):
        """Test _coerce_items with a dictionary input."""
        fields = {"key1": "value1", "key2": "value2"}
        result = _coerce_items(fields)
        assert isinstance(result, list)
        assert len(result) == 2
        # Check that all items are present (dict order may vary in older Python)
        assert ("key1", "value1") in result
        assert ("key2", "value2") in result

    def test_coerce_items_with_sequence(self):
        """Test _coerce_items with a sequence of tuples."""
        fields = [("key1", "value1"), ("key2", "value2")]
        result = _coerce_items(fields)
        assert isinstance(result, list)
        assert result == [("key1", "value1"), ("key2", "value2")]

    def test_coerce_items_preserves_order_in_sequence(self):
        """Test _coerce_items preserves order when given a sequence."""
        fields = [("z", 1), ("a", 2), ("m", 3)]
        result = _coerce_items(fields)
        assert result == [("z", 1), ("a", 2), ("m", 3)]

    def test_coerce_items_with_empty_dict(self):
        """Test _coerce_items with an empty dictionary."""
        result = _coerce_items({})
        assert result == []

    def test_coerce_items_with_empty_sequence(self):
        """Test _coerce_items with an empty sequence."""
        result = _coerce_items([])
        assert result == []


class TestStringify:
    """Tests for _stringify helper function."""

    def test_stringify_with_none(self):
        """Test _stringify with None returns empty string."""
        assert _stringify(None) == ""

    def test_stringify_with_string(self):
        """Test _stringify with a string returns stripped string."""
        assert _stringify("hello") == "hello"
        assert _stringify("  hello  ") == "hello"
        assert _stringify("  ") == ""

    def test_stringify_with_list(self):
        """Test _stringify with a list returns comma-separated values."""
        assert _stringify([1, 2, 3]) == "1, 2, 3"
        assert _stringify(["a", "b", "c"]) == "a, b, c"
        assert _stringify([]) == ""

    def test_stringify_with_tuple(self):
        """Test _stringify with a tuple returns comma-separated values."""
        assert _stringify((1, 2, 3)) == "1, 2, 3"
        assert _stringify(("a", "b", "c")) == "a, b, c"
        assert _stringify(()) == ""

    def test_stringify_with_set(self):
        """Test _stringify with a set returns comma-separated values."""
        result = _stringify({1, 2, 3})
        # Sets are unordered, so we check the components
        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert ", " in result or result in ["1", "2", "3"]  # Handle single-item case

    def test_stringify_with_int(self):
        """Test _stringify with an integer."""
        assert _stringify(42) == "42"
        assert _stringify(0) == "0"
        assert _stringify(-10) == "-10"

    def test_stringify_with_bool(self):
        """Test _stringify with a boolean."""
        assert _stringify(True) == "True"
        assert _stringify(False) == "False"

    def test_stringify_with_float(self):
        """Test _stringify with a float."""
        assert _stringify(3.14) == "3.14"

    def test_stringify_with_nested_list(self):
        """Test _stringify with nested lists."""
        result = _stringify([1, [2, 3], 4])
        assert "1" in result
        assert "4" in result

    def test_stringify_with_mixed_list(self):
        """Test _stringify with mixed types in list."""
        result = _stringify([1, "two", None, True])
        assert "1" in result
        assert "two" in result
        assert "True" in result


class TestWrapText:
    """Tests for _wrap_text helper function."""

    def test_wrap_text_with_empty_string(self):
        """Test _wrap_text with empty string returns list with empty string."""
        result = _wrap_text("", 50)
        assert result == [""]

    def test_wrap_text_with_single_short_line(self):
        """Test _wrap_text with text shorter than width."""
        result = _wrap_text("hello world", 50)
        assert result == ["hello world"]

    def test_wrap_text_with_single_long_line(self):
        """Test _wrap_text with text longer than width."""
        text = "This is a very long line that should be wrapped at the specified width"
        result = _wrap_text(text, 30)
        assert len(result) > 1
        # Verify all lines are within width
        for line in result:
            assert len(line) <= 30
        # Verify content is preserved (when joined)
        assert " ".join(result) == text

    def test_wrap_text_with_multiple_lines(self):
        """Test _wrap_text with multi-line text."""
        text = "Line 1\nLine 2\nLine 3"
        result = _wrap_text(text, 50)
        assert len(result) == 3
        assert result == ["Line 1", "Line 2", "Line 3"]

    def test_wrap_text_with_multiple_lines_needing_wrap(self):
        """Test _wrap_text with multi-line text where lines need wrapping."""
        text = "This is a long first line that needs wrapping\nShort line\nAnother long line that also needs wrapping"
        result = _wrap_text(text, 30)
        assert len(result) > 3  # More than 3 because some lines wrap

    def test_wrap_text_with_blank_lines(self):
        """Test _wrap_text preserves blank lines."""
        text = "Line 1\n\nLine 3"
        result = _wrap_text(text, 50)
        assert len(result) == 3
        assert result[0] == "Line 1"
        assert result[1] == ""
        assert result[2] == "Line 3"

    def test_wrap_text_with_only_newlines(self):
        """Test _wrap_text with only newline characters."""
        result = _wrap_text("\n\n", 50)
        assert result == ["", "", ""]

    def test_wrap_text_with_exact_width(self):
        """Test _wrap_text with text exactly at width."""
        text = "x" * 50
        result = _wrap_text(text, 50)
        assert result == [text]

    def test_wrap_text_with_small_width(self):
        """Test _wrap_text with very small width."""
        result = _wrap_text("hello world", 5)
        assert len(result) > 1
        for line in result:
            assert len(line) <= 5


# Tests for LogBlockBuilder class will be added in subsequent subtasks


# Tests for convenience functions will be added in subsequent subtasks
