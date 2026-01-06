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


class TestLogBlockBuilder:
    """Tests for LogBlockBuilder class."""

    def test_initialization_with_defaults(self):
        """Test LogBlockBuilder initialization with default parameters."""
        builder = LogBlockBuilder("Test Title")
        assert builder.title == "Test Title"
        assert builder.wrap_width == 110  # DEFAULT_WRAP_WIDTH
        assert builder.label_width == 22  # DEFAULT_LABEL_WIDTH
        assert builder.indent == "    "  # DEFAULT_INDENT
        # Check that lines contain the title and header
        assert len(builder.lines) >= 2
        assert builder.lines[0] == ""  # pad_top=True by default
        assert builder.lines[1] == "Test Title"
        assert builder.lines[2] == "-" * len("Test Title")

    def test_initialization_without_pad_top(self):
        """Test LogBlockBuilder initialization with pad_top=False."""
        builder = LogBlockBuilder("Test Title", pad_top=False)
        # Should start with title, not blank line
        assert builder.lines[0] == "Test Title"
        assert builder.lines[1] == "-" * len("Test Title")

    def test_initialization_with_custom_parameters(self):
        """Test LogBlockBuilder initialization with custom parameters."""
        builder = LogBlockBuilder(
            "Custom Title",
            wrap_width=80,
            label_width=15,
            indent="  ",
            pad_top=False,
        )
        assert builder.wrap_width == 80
        assert builder.label_width == 15
        assert builder.indent == "  "
        assert builder.lines[0] == "Custom Title"

    def test_title_and_header_rendering(self):
        """Test that title and header are rendered correctly."""
        builder = LogBlockBuilder("Sample", pad_top=False)
        result = builder.render()
        lines = result.split("\n")
        assert lines[0] == "Sample"
        assert lines[1] == "------"  # 6 dashes for "Sample"

    def test_add_blank_line(self):
        """Test add_blank_line adds a blank line."""
        builder = LogBlockBuilder("Title", pad_top=False)
        initial_count = len(builder.lines)
        builder.add_blank_line()
        assert len(builder.lines) == initial_count + 1
        assert builder.lines[-1] == ""

    def test_add_blank_line_deduplication(self):
        """Test add_blank_line doesn't add duplicate blank lines."""
        builder = LogBlockBuilder("Title", pad_top=False)
        builder.add_blank_line()
        line_count_after_first = len(builder.lines)
        builder.add_blank_line()
        # Should not add another blank line
        assert len(builder.lines) == line_count_after_first

    def test_add_blank_line_on_empty_lines(self):
        """Test add_blank_line on builder with no lines (edge case)."""
        builder = LogBlockBuilder("Title", pad_top=False)
        builder.lines = []
        builder.add_blank_line()
        # Should not add a blank line when lines is empty
        assert len(builder.lines) == 0

    def test_add_fields_with_dict(self):
        """Test add_fields with a dictionary."""
        builder = LogBlockBuilder("Fields", pad_top=False)
        builder.add_fields({"key1": "value1", "key2": "value2"})
        result = builder.render()
        assert "key1" in result
        assert "value1" in result
        assert "key2" in result
        assert "value2" in result

    def test_add_fields_with_sequence(self):
        """Test add_fields with a sequence of tuples."""
        builder = LogBlockBuilder("Fields", pad_top=False)
        builder.add_fields([("first", "alpha"), ("second", "beta")])
        result = builder.render()
        assert "first" in result
        assert "alpha" in result
        assert "second" in result
        assert "beta" in result

    def test_add_fields_with_none(self):
        """Test add_fields with None does nothing."""
        builder = LogBlockBuilder("Title", pad_top=False)
        initial_count = len(builder.lines)
        builder.add_fields(None)
        assert len(builder.lines) == initial_count

    def test_add_fields_with_empty_dict(self):
        """Test add_fields with empty dictionary does nothing."""
        builder = LogBlockBuilder("Title", pad_top=False)
        initial_count = len(builder.lines)
        builder.add_fields({})
        assert len(builder.lines) == initial_count

    def test_add_fields_with_various_value_types(self):
        """Test add_fields with different value types."""
        builder = LogBlockBuilder("Types", pad_top=False)
        builder.add_fields({
            "string": "text",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
        })
        result = builder.render()
        assert "string" in result and "text" in result
        assert "number" in result and "42" in result
        assert "boolean" in result and "True" in result
        assert "none" in result
        assert "list" in result and "1, 2, 3" in result

    def test_add_fields_with_long_value_wrapping(self):
        """Test add_fields wraps long values."""
        builder = LogBlockBuilder("Wrap Test", pad_top=False, wrap_width=50)
        long_value = "This is a very long value that should be wrapped to multiple lines when rendered"
        builder.add_fields({"key": long_value})
        result = builder.render()
        lines = result.split("\n")
        # Should have more lines due to wrapping
        assert len(lines) > 3  # Title, header, and at least 2 for wrapped value

    def test_add_fields_formatting(self):
        """Test add_fields formats with proper indentation and colons."""
        builder = LogBlockBuilder("Format", pad_top=False)
        builder.add_fields({"name": "value"})
        result = builder.render()
        # Should have indent (4 spaces by default), key, colon, space, value
        assert "    name" in result
        assert ": value" in result

    def test_add_section_with_empty_items(self):
        """Test add_section with empty items shows empty label."""
        builder = LogBlockBuilder("Sections", pad_top=False)
        builder.add_section("Empty Section", [])
        result = builder.render()
        assert "Empty Section:" in result
        assert "(none)" in result

    def test_add_section_with_custom_empty_label(self):
        """Test add_section with custom empty_label."""
        builder = LogBlockBuilder("Sections", pad_top=False)
        builder.add_section("No Items", [], empty_label="<nothing>")
        result = builder.render()
        assert "No Items:" in result
        assert "<nothing>" in result

    def test_add_section_with_items(self):
        """Test add_section with populated items."""
        builder = LogBlockBuilder("List", pad_top=False)
        builder.add_section("Items", ["item1", "item2", "item3"])
        result = builder.render()
        assert "Items:" in result
        assert "- item1" in result
        assert "- item2" in result
        assert "- item3" in result

    def test_add_section_with_none_items_filtered(self):
        """Test add_section filters out None items."""
        builder = LogBlockBuilder("Filtered", pad_top=False)
        builder.add_section("Mixed", ["item1", None, "item2", None])
        result = builder.render()
        assert "- item1" in result
        assert "- item2" in result
        # Should have exactly 2 bullet points
        assert result.count("- ") == 2

    def test_add_section_adds_blank_line_before(self):
        """Test add_section adds a blank line before the section."""
        builder = LogBlockBuilder("Title", pad_top=False)
        builder.add_fields({"key": "value"})
        initial_lines = len(builder.lines)
        builder.add_section("Section", ["item"])
        # Should have added blank line + heading + item
        assert len(builder.lines) > initial_lines + 1

    def test_add_section_with_long_items_wrapping(self):
        """Test add_section wraps long items."""
        builder = LogBlockBuilder("Wrap", pad_top=False, wrap_width=60)
        long_item = "This is a very long item that should wrap to multiple lines"
        builder.add_section("Wrapped", [long_item])
        result = builder.render()
        lines = result.split("\n")
        # Check that we have multiple lines (more than just title, header, blank, heading, first line)
        assert len(lines) > 5

    def test_render_returns_joined_lines(self):
        """Test render joins lines with newlines."""
        builder = LogBlockBuilder("Test", pad_top=False)
        builder.add_fields({"a": "1"})
        result = builder.render()
        assert isinstance(result, str)
        assert "\n" in result
        assert result.count("\n") >= 2  # At least title separator and field

    def test_render_strips_trailing_whitespace(self):
        """Test render strips trailing whitespace."""
        builder = LogBlockBuilder("Test", pad_top=False)
        result = builder.render()
        assert not result.endswith(" ")
        assert not result.endswith("\n")

    def test_complex_block_with_multiple_sections(self):
        """Test building a complex block with fields and sections."""
        builder = LogBlockBuilder("Complex Report")
        builder.add_fields({
            "Status": "Active",
            "Count": 42,
        })
        builder.add_section("Warnings", ["Warning 1", "Warning 2"])
        builder.add_section("Errors", [])
        result = builder.render()

        # Verify all content is present
        assert "Complex Report" in result
        assert "Status" in result
        assert "Active" in result
        assert "Count" in result
        assert "42" in result
        assert "Warnings:" in result
        assert "- Warning 1" in result
        assert "- Warning 2" in result
        assert "Errors:" in result
        assert "(none)" in result

    def test_builder_preserves_order_of_operations(self):
        """Test that operations are rendered in the order they're called."""
        builder = LogBlockBuilder("Order Test", pad_top=False)
        builder.add_fields([("first", "1")])
        builder.add_section("Middle Section", ["item"])
        builder.add_fields([("last", "2")])

        result = builder.render()
        lines = result.split("\n")

        # Find indices to verify order
        first_idx = next(i for i, line in enumerate(lines) if "first" in line)
        middle_idx = next(i for i, line in enumerate(lines) if "Middle Section" in line)
        last_idx = next(i for i, line in enumerate(lines) if "last" in line)

        assert first_idx < middle_idx < last_idx


class TestRenderFieldsBlock:
    """Tests for render_fields_block convenience function."""

    def test_render_fields_block_basic(self):
        """Test render_fields_block with basic field dictionary."""
        result = render_fields_block("Test Block", {"key1": "value1", "key2": "value2"})
        assert isinstance(result, str)
        assert "Test Block" in result
        assert "-" * len("Test Block") in result
        assert "key1" in result
        assert "value1" in result
        assert "key2" in result
        assert "value2" in result

    def test_render_fields_block_with_pad_top_true(self):
        """Test render_fields_block with pad_top=True (default)."""
        result = render_fields_block("Title", {"key": "value"}, pad_top=True)
        lines = result.split("\n")
        # First line should be empty with pad_top=True
        assert lines[0] == ""
        assert lines[1] == "Title"

    def test_render_fields_block_with_pad_top_false(self):
        """Test render_fields_block with pad_top=False."""
        result = render_fields_block("Title", {"key": "value"}, pad_top=False)
        lines = result.split("\n")
        # First line should be title, not empty
        assert lines[0] == "Title"
        assert lines[1] == "-" * len("Title")

    def test_render_fields_block_with_sequence(self):
        """Test render_fields_block with sequence of tuples."""
        fields = [("first", "alpha"), ("second", "beta")]
        result = render_fields_block("Ordered", fields, pad_top=False)
        assert "Ordered" in result
        assert "first" in result
        assert "alpha" in result
        assert "second" in result
        assert "beta" in result

    def test_render_fields_block_with_empty_fields(self):
        """Test render_fields_block with empty fields."""
        result = render_fields_block("Empty", {}, pad_top=False)
        lines = result.split("\n")
        # Should only have title and separator
        assert lines[0] == "Empty"
        assert lines[1] == "-----"
        assert len(lines) == 2

    def test_render_fields_block_with_various_types(self):
        """Test render_fields_block with various value types."""
        result = render_fields_block(
            "Types",
            {
                "string": "text",
                "number": 42,
                "list": [1, 2, 3],
                "none": None,
            },
            pad_top=False,
        )
        assert "string" in result and "text" in result
        assert "number" in result and "42" in result
        assert "list" in result and "1, 2, 3" in result
        assert "none" in result

    def test_render_fields_block_formatting(self):
        """Test render_fields_block has proper formatting."""
        result = render_fields_block("Format", {"name": "value"}, pad_top=False)
        # Check for proper indentation and formatting
        assert "    name" in result
        assert ": value" in result


class TestRenderSectionBlock:
    """Tests for render_section_block convenience function."""

    def test_render_section_block_single_section(self):
        """Test render_section_block with a single section."""
        sections = [("Items", ["item1", "item2", "item3"])]
        result = render_section_block("Test", sections, pad_top=False)
        assert "Test" in result
        assert "Items:" in result
        assert "- item1" in result
        assert "- item2" in result
        assert "- item3" in result

    def test_render_section_block_multiple_sections(self):
        """Test render_section_block with multiple sections."""
        sections = [
            ("Section A", ["a1", "a2"]),
            ("Section B", ["b1", "b2", "b3"]),
            ("Section C", ["c1"]),
        ]
        result = render_section_block("Multi", sections, pad_top=False)

        # Check title
        assert "Multi" in result

        # Check all section headings
        assert "Section A:" in result
        assert "Section B:" in result
        assert "Section C:" in result

        # Check all items
        assert "- a1" in result
        assert "- a2" in result
        assert "- b1" in result
        assert "- b2" in result
        assert "- b3" in result
        assert "- c1" in result

    def test_render_section_block_with_pad_top_true(self):
        """Test render_section_block with pad_top=True (default)."""
        sections = [("Items", ["item1"])]
        result = render_section_block("Title", sections, pad_top=True)
        lines = result.split("\n")
        # First line should be empty with pad_top=True
        assert lines[0] == ""
        assert lines[1] == "Title"

    def test_render_section_block_with_pad_top_false(self):
        """Test render_section_block with pad_top=False."""
        sections = [("Items", ["item1"])]
        result = render_section_block("Title", sections, pad_top=False)
        lines = result.split("\n")
        # First line should be title, not empty
        assert lines[0] == "Title"
        assert lines[1] == "-" * len("Title")

    def test_render_section_block_with_empty_section(self):
        """Test render_section_block with empty section."""
        sections = [("Empty Section", [])]
        result = render_section_block("Test", sections, pad_top=False)
        assert "Empty Section:" in result
        assert "(none)" in result

    def test_render_section_block_mixed_empty_and_populated(self):
        """Test render_section_block with mix of empty and populated sections."""
        sections = [
            ("Has Items", ["item1", "item2"]),
            ("Empty", []),
            ("More Items", ["item3"]),
        ]
        result = render_section_block("Mixed", sections, pad_top=False)

        assert "Has Items:" in result
        assert "- item1" in result
        assert "- item2" in result

        assert "Empty:" in result
        assert "(none)" in result

        assert "More Items:" in result
        assert "- item3" in result

    def test_render_section_block_filters_none_items(self):
        """Test render_section_block filters out None items."""
        sections = [("Filtered", ["item1", None, "item2", None, "item3"])]
        result = render_section_block("Test", sections, pad_top=False)
        assert "- item1" in result
        assert "- item2" in result
        assert "- item3" in result
        # Should have exactly 3 bullet points
        assert result.count("- item") == 3

    def test_render_section_block_with_empty_sections_list(self):
        """Test render_section_block with no sections."""
        result = render_section_block("No Sections", [], pad_top=False)
        lines = result.split("\n")
        # Should only have title and separator
        assert lines[0] == "No Sections"
        assert lines[1] == "-----------"
        assert len(lines) == 2

    def test_render_section_block_section_order(self):
        """Test render_section_block preserves section order."""
        sections = [
            ("First", ["1"]),
            ("Second", ["2"]),
            ("Third", ["3"]),
        ]
        result = render_section_block("Order", sections, pad_top=False)
        lines = result.split("\n")

        # Find indices of section headings
        first_idx = next(i for i, line in enumerate(lines) if "First:" in line)
        second_idx = next(i for i, line in enumerate(lines) if "Second:" in line)
        third_idx = next(i for i, line in enumerate(lines) if "Third:" in line)

        # Verify they appear in order
        assert first_idx < second_idx < third_idx
