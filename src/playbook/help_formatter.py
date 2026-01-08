from __future__ import annotations

import argparse
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class RichHelpFormatter(argparse.HelpFormatter):
    """
    Custom argparse help formatter that uses Rich for colorful, structured output.

    Supports rendering sections with enhanced formatting:
    - Description: Main command description
    - Usage: Command usage syntax
    - Arguments: Positional arguments
    - Options: Optional flags and parameters
    - Examples: Usage examples with syntax highlighting
    - Environment Variables: Relevant environment variables
    - Tips: Helpful tips and best practices
    """

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
        console: Console | None = None,
    ) -> None:
        """
        Initialize the RichHelpFormatter.

        Args:
            prog: Program name
            indent_increment: Spaces per indent level
            max_help_position: Maximum position for help text
            width: Terminal width (auto-detected if None)
            console: Rich Console instance (creates new if None)
        """
        # Detect terminal width if not provided
        if width is None:
            terminal_size = shutil.get_terminal_size()
            width = min(terminal_size.columns, 120)  # Cap at 120 for readability

        super().__init__(
            prog=prog,
            indent_increment=indent_increment,
            max_help_position=max_help_position,
            width=width,
        )

        self.console = console or Console()
        self._sections: list[tuple[str, str]] = []
        self._examples: list[tuple[str, str]] = []
        self._env_vars: list[tuple[str, str]] = []
        self._tips: list[str] = []

    def add_examples(self, examples: list[tuple[str, str]]) -> None:
        """
        Add usage examples to the help output.

        Args:
            examples: List of (description, command) tuples
        """
        self._examples = examples

    def add_environment_variables(self, env_vars: list[tuple[str, str]]) -> None:
        """
        Add environment variable documentation to the help output.

        Args:
            env_vars: List of (variable_name, description) tuples
        """
        self._env_vars = env_vars

    def add_tips(self, tips: list[str]) -> None:
        """
        Add helpful tips to the help output.

        Args:
            tips: List of tip strings
        """
        self._tips = tips

    def format_help(self) -> str:
        """
        Format the complete help message using Rich.

        Returns:
            Formatted help string
        """
        # Check if output is a TTY - if not, fall back to standard formatting
        if not self.console.is_terminal:
            return super().format_help()

        # Build the help output using Rich
        help_parts: list[str] = []

        # Get the standard argparse help
        standard_help = super().format_help()

        # Parse and enhance the standard help
        lines = standard_help.split("\n")
        current_section = None
        section_content: list[str] = []

        for line in lines:
            # Detect section headers (lines ending with ':' and not indented)
            if line and not line[0].isspace() and line.endswith(":"):
                # Save previous section
                if current_section:
                    self._render_section(current_section, "\n".join(section_content), help_parts)
                current_section = line[:-1]
                section_content = []
            else:
                section_content.append(line)

        # Save last section
        if current_section:
            self._render_section(current_section, "\n".join(section_content), help_parts)

        # Add examples section
        if self._examples:
            help_parts.append(self._render_examples())

        # Add environment variables section
        if self._env_vars:
            help_parts.append(self._render_env_vars())

        # Add tips section
        if self._tips:
            help_parts.append(self._render_tips())

        return "\n".join(help_parts)

    def _render_section(self, title: str, content: str, output: list[str]) -> None:
        """
        Render a section with Rich formatting.

        Args:
            title: Section title
            content: Section content
            output: List to append rendered output to
        """
        # Map section titles to icons for visual scanning
        section_icons = {
            "usage": "🚀",
            "positional arguments": "📋",
            "optional arguments": "⚙️",
            "options": "⚙️",
            "description": "📝",
        }

        # Get icon for this section (case-insensitive lookup)
        icon = section_icons.get(title.lower(), "")
        icon_prefix = f"{icon} " if icon else ""

        # Create a styled title with icon
        title_text = Text()
        title_text.append(f"{icon_prefix}{title}", style="bold bright_cyan")

        # Render title
        with self.console.capture() as capture:
            self.console.print(title_text)
        output.append(capture.get())

        # Render content (with slight indent)
        if content.strip():
            output.append(content)

        output.append("")  # Blank line after section

    def _render_examples(self) -> str:
        """
        Render the examples section with syntax highlighting.

        Returns:
            Formatted examples string
        """
        if not self._examples:
            return ""

        with self.console.capture() as capture:
            # Section header with icon
            self.console.print(Text("📚 Examples:", style="bold bright_cyan"))
            self.console.print()

            for i, (description, command) in enumerate(self._examples, 1):
                # Print description with subtle numbering
                desc_text = Text()
                desc_text.append(f"  {i}. ", style="dim cyan")
                desc_text.append(description, style="bright_white")
                self.console.print(desc_text)

                # Print command in a code block style with good contrast
                self.console.print(f"     $ {command}", style="bright_yellow")

                if i < len(self._examples):
                    self.console.print()  # Spacing between examples

            # Add note about --examples flag with icon
            self.console.print()
            self.console.print(
                "  💡 Run with --examples to see more comprehensive usage examples", style="dim italic bright_blue"
            )

        return capture.get()

    def _render_env_vars(self) -> str:
        """
        Render the environment variables section.

        Returns:
            Formatted environment variables string
        """
        with self.console.capture() as capture:
            # Section header with icon
            self.console.print(Text("🔧 Environment Variables:", style="bold bright_cyan"))
            self.console.print()

            # Create a table for better readability with enhanced styling
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Variable", style="bright_green bold", no_wrap=True)
            table.add_column("Description", style="bright_white")

            for var_name, description in self._env_vars:
                table.add_row(var_name, description)

            self.console.print(table)

        return capture.get()

    def _render_tips(self) -> str:
        """
        Render the tips section.

        Returns:
            Formatted tips string
        """
        with self.console.capture() as capture:
            # Section header with icon
            self.console.print(Text("💡 Tips:", style="bold bright_cyan"))
            self.console.print()

            for tip in self._tips:
                # Use a styled bullet point for each tip with good readability
                tip_text = Text()
                tip_text.append("  ✨ ", style="bright_yellow")
                tip_text.append(tip, style="bright_white")
                self.console.print(tip_text)

        return capture.get()


def render_extended_examples(
    command_name: str,
    examples: list[tuple[str, str]],
    console: Console | None = None,
) -> None:
    """
    Render extended examples in a comprehensive cookbook-style format.

    Args:
        command_name: Name of the command (for the title)
        examples: List of (description, command) tuples
        console: Rich Console instance (creates new if None)
    """
    if console is None:
        console = Console()

    # Render title with icon
    title = Text()
    title.append("📚 Extended Examples: ", style="bold bright_white")
    title.append(f"playbook {command_name}", style="bold bright_cyan")

    console.print()
    console.print(Panel(title, style="bold bright_cyan", border_style="bright_cyan"))
    console.print()

    # Group examples by category
    cli_examples = []
    docker_examples = []
    kubernetes_examples = []
    python_examples = []
    other_examples = []

    for description, command in examples:
        if command.startswith("docker "):
            docker_examples.append((description, command))
        elif command.startswith("kubectl "):
            kubernetes_examples.append((description, command))
        elif command.startswith("python "):
            python_examples.append((description, command))
        elif command.startswith(f"playbook {command_name}") or command.startswith("playbook "):
            cli_examples.append((description, command))
        else:
            other_examples.append((description, command))

    # Render CLI examples
    if cli_examples:
        console.print(Text("💻 Command-Line Interface", style="bold bright_yellow"))
        console.print()
        for i, (description, command) in enumerate(cli_examples, 1):
            desc_text = Text()
            desc_text.append(f"  {i}. ", style="dim bright_cyan")
            desc_text.append(description, style="bright_white")
            console.print(desc_text)
            console.print(f"     $ {command}", style="bright_green")
            console.print()

    # Render Docker examples
    if docker_examples:
        console.print(Text("🐳 Docker Usage", style="bold bright_yellow"))
        console.print()
        for i, (description, command) in enumerate(docker_examples, 1):
            desc_text = Text()
            desc_text.append(f"  {i}. ", style="dim bright_cyan")
            desc_text.append(description, style="bright_white")
            console.print(desc_text)
            console.print(f"     $ {command}", style="bright_blue")
            console.print()

    # Render Kubernetes examples
    if kubernetes_examples:
        console.print(Text("☸️  Kubernetes Usage", style="bold bright_yellow"))
        console.print()
        for i, (description, command) in enumerate(kubernetes_examples, 1):
            desc_text = Text()
            desc_text.append(f"  {i}. ", style="dim bright_cyan")
            desc_text.append(description, style="bright_white")
            console.print(desc_text)
            console.print(f"     $ {command}", style="bright_magenta")
            console.print()

    # Render Python module examples
    if python_examples:
        console.print(Text("🐍 Python Module Usage", style="bold bright_yellow"))
        console.print()
        for i, (description, command) in enumerate(python_examples, 1):
            desc_text = Text()
            desc_text.append(f"  {i}. ", style="dim bright_cyan")
            desc_text.append(description, style="bright_white")
            console.print(desc_text)
            console.print(f"     $ {command}", style="bright_cyan")
            console.print()

    # Render other examples
    if other_examples:
        console.print(Text("📝 Other Examples", style="bold bright_yellow"))
        console.print()
        for i, (description, command) in enumerate(other_examples, 1):
            desc_text = Text()
            desc_text.append(f"  {i}. ", style="dim bright_cyan")
            desc_text.append(description, style="bright_white")
            console.print(desc_text)
            console.print(f"     $ {command}", style="bright_yellow")
            console.print()

    # Footer note
    console.print()
    footer_text = Text()
    footer_text.append("💡 Tip: ", style="bright_yellow bold")
    footer_text.append("Use --help to see concise help with common options", style="bright_white")
    console.print(
        Panel(
            footer_text,
            style="dim bright_blue",
            border_style="dim bright_blue",
        )
    )
    console.print()
