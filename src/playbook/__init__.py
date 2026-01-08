"""Playbook core package.

The playbook package is organized into focused modules with clear separation of concerns:

- **processor**: Main orchestration class that coordinates file processing
- **trace_writer**: Debug trace persistence for pattern matching diagnostics
- **file_discovery**: Source file discovery, filtering, and glob matching
- **match_handler**: File match processing, link creation, and overwrite decisions
- **destination_builder**: Building destination paths from match context
- **metadata_loader**: Parallel metadata loading and fingerprint tracking
- **post_run_triggers**: Post-processing triggers (Plex sync, Kometa)
- **run_summary**: Logging summaries, run recaps, and statistics formatting

Most modules are internal implementation details and should be imported directly
when needed (e.g., ``from playbook.trace_writer import TraceOptions``).

The main entry point for file processing is the ``Processor`` class.
"""

from .processor import Processor
from .trace_writer import TraceOptions
from .version import __version__

__all__ = [
    "__version__",
    "Processor",
    "TraceOptions",
]
