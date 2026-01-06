from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSequence, Sequence
from textwrap import wrap
from typing import Union

DEFAULT_WRAP_WIDTH = 110
DEFAULT_LABEL_WIDTH = 22
DEFAULT_INDENT = "    "

FieldMapping = Union[Mapping[str, object], Sequence[tuple[str, object]]]


def _coerce_items(fields: FieldMapping) -> list[tuple[str, object]]:
    if isinstance(fields, Mapping):
        return list(fields.items())
    return list(fields)


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_stringify(item) for item in value)
    return str(value)


def _wrap_text(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    for raw_line in text.splitlines() or [""]:
        wrapped = wrap(raw_line, width=width) or [""]
        lines.extend(wrapped)
    return lines


class LogBlockBuilder:
    def __init__(
        self,
        title: str,
        *,
        wrap_width: int = DEFAULT_WRAP_WIDTH,
        label_width: int = DEFAULT_LABEL_WIDTH,
        indent: str = DEFAULT_INDENT,
        pad_top: bool = True,
    ) -> None:
        self.title = title
        self.wrap_width = wrap_width
        self.label_width = label_width
        self.indent = indent
        self.lines: MutableSequence[str] = []
        if pad_top:
            self.lines.append("")
        self.lines.append(title)
        self.lines.append("-" * len(title))

    def add_blank_line(self) -> None:
        if not self.lines or self.lines[-1] == "":
            return
        self.lines.append("")

    def add_fields(self, fields: FieldMapping | None) -> None:
        if not fields:
            return
        items = _coerce_items(fields)
        if not items:
            return

        computed_width = max((len(str(key)) for key, _ in items), default=0)
        label_width = max(min(computed_width, self.label_width), 8)
        value_width = max(self.wrap_width - len(self.indent) - label_width - 4, 32)

        for key, value in items:
            text = _stringify(value)
            wrapped = _wrap_text(text, value_width)
            first_line = wrapped[0] if wrapped else ""
            self.lines.append(f"{self.indent}{str(key):<{label_width}}: {first_line}")
            for continuation in wrapped[1:]:
                self.lines.append(f"{self.indent}{'':<{label_width}}  {continuation}")

    def add_section(
        self,
        heading: str,
        items: Iterable[str],
        *,
        empty_label: str = "(none)",
    ) -> None:
        self.add_blank_line()
        self.lines.append(f"{heading}:")
        materialized = [item for item in items if item is not None]
        if not materialized:
            self.lines.append(f"{self.indent}{empty_label}")
            return

        bullet_indent = self.indent + "- "
        continuation_indent = self.indent + "  "
        bullet_width = max(self.wrap_width - len(bullet_indent), 24)

        for item in materialized:
            text = _stringify(item)
            wrapped = _wrap_text(text, bullet_width)
            if not wrapped:
                self.lines.append(bullet_indent.rstrip())
                continue
            self.lines.append(f"{bullet_indent}{wrapped[0]}")
            for continuation in wrapped[1:]:
                self.lines.append(f"{continuation_indent}{continuation}")

    def render(self) -> str:
        return "\n".join(self.lines).rstrip()


def render_fields_block(title: str, fields: FieldMapping, *, pad_top: bool = True) -> str:
    builder = LogBlockBuilder(title, pad_top=pad_top)
    builder.add_fields(fields)
    return builder.render()


def render_section_block(
    title: str,
    sections: Sequence[tuple[str, Sequence[str]]],
    *,
    pad_top: bool = True,
) -> str:
    builder = LogBlockBuilder(title, pad_top=pad_top)
    for heading, items in sections:
        builder.add_section(heading, items)
    return builder.render()

