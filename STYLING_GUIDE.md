# Rich Styling Guide for Playbook Interactive Help

## Color Scheme

The help system uses a consistent color scheme optimized for both dark and light terminal themes:

### Primary Colors
- **Headers**: `bold bright_cyan` - Section titles and command names
- **Text**: `bright_white` - Main descriptive text for maximum readability
- **Examples**: `bright_yellow` - Command examples stand out clearly
- **Tips**: `bright_yellow` and `bright_white` - Highlighted important information

### Category-Specific Colors
- **CLI Examples**: `bright_green` - Native command-line usage
- **Docker Examples**: `bright_blue` - Docker-related commands
- **Kubernetes Examples**: `bright_magenta` - Kubernetes commands
- **Python Examples**: `bright_cyan` - Python module usage
- **Environment Variables**: `bright_green bold` - Variable names

### Accent Colors
- **Numbering**: `dim cyan` - Subtle numbering for examples
- **Hints**: `dim italic bright_blue` - Subtle informational hints
- **Icons**: `bright_yellow` - Emoji icons for visual scanning

## Icons & Emojis

Icons are strategically placed for quick visual scanning:

### Section Headers
- 🚀 **Usage** - Quick launch/usage section
- 📋 **Positional Arguments** - Required arguments
- ⚙️ **Options** - Optional flags and parameters
- 📝 **Description** - Command description
- 📚 **Examples** - Usage examples
- 🔧 **Environment Variables** - Configuration via env vars
- 💡 **Tips** - Helpful tips and best practices

### Example Categories
- 💻 **Command-Line Interface** - Direct CLI usage
- 🐳 **Docker Usage** - Docker-specific examples
- ☸️ **Kubernetes Usage** - K8s-specific examples
- 🐍 **Python Module Usage** - Python -m usage
- 📝 **Other Examples** - Miscellaneous usage

### Special Icons
- ✨ - Individual tips (sparkling star)
- 💡 - Information hints and notes

## Design Rationale

### Brightness for Cross-Theme Compatibility
Using `bright_*` variants ensures:
- **Dark themes**: Colors are vivid and easy to read
- **Light themes**: Colors have enough contrast to remain visible
- **Low-color terminals**: Falls back to standard colors gracefully

### Consistent Hierarchy
1. **Section headers** - Most prominent (bold bright_cyan with icons)
2. **Content text** - High readability (bright_white)
3. **Code examples** - Distinguished (bright_yellow for commands)
4. **Hints/notes** - Subtle (dim styles)

### Visual Scanning
- Icons at start of sections for quick navigation
- Consistent color per category (Docker = blue, K8s = magenta, etc.)
- Numbered lists with subtle coloring on numbers

## Testing

The styling has been verified to:
- ✅ Work without errors in TTY environments
- ✅ Fall back to standard argparse in non-TTY (CI/CD)
- ✅ Use consistent colors across all sections
- ✅ Include emojis for visual differentiation
- ✅ Provide good contrast in both dark and light themes

### Manual Testing Commands
```bash
# Test main help
playbook --help

# Test subcommand help
playbook run --help
playbook validate-config --help
playbook kometa-trigger --help

# Test extended examples
playbook run --examples
playbook validate-config --examples
playbook kometa-trigger --examples
```

## No-Color Support

The formatter automatically detects when running in a non-TTY environment (like CI/CD pipelines) and falls back to standard argparse formatting, ensuring compatibility everywhere.
