"""OCTAVE primer utilities for loading primers from octave-mcp package.

The octave-mcp package includes several primers for teaching agents OCTAVE syntax:
- octave-literacy-primer: Basic OCTAVE syntax (~40 tokens)
- octave-mastery-primer: Advanced patterns
- octave-compression-primer: Compression techniques
- octave-mythology-primer: Mythological semantic shorthand

These primers can be injected into agent context to improve OCTAVE output quality.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

# Available primers in octave-mcp package
PrimerName = Literal[
    "octave-literacy-primer",
    "octave-mastery-primer",
    "octave-compression-primer",
    "octave-mythology-primer",
    "octave-ultra-mythic-primer",
]


def _get_primers_dir() -> Path:
    """Get the primers directory from octave-mcp package."""
    try:
        import octave_mcp

        pkg_path = Path(octave_mcp.__file__).parent
        primers_dir = pkg_path / "resources" / "primers"
        if primers_dir.exists():
            return primers_dir
        raise FileNotFoundError(f"Primers directory not found: {primers_dir}")
    except ImportError as e:
        raise ImportError(
            "octave-mcp package is required. Install with: pip install octave-mcp>=1.0.0"
        ) from e


@lru_cache(maxsize=8)
def load_primer(name: PrimerName) -> str:
    """Load an OCTAVE primer from the octave-mcp package.

    Args:
        name: Name of the primer to load (e.g., "octave-literacy-primer")

    Returns:
        The primer content as a string

    Raises:
        FileNotFoundError: If the primer doesn't exist
        ImportError: If octave-mcp is not installed

    Example:
        >>> primer = load_primer("octave-literacy-primer")
        >>> print(primer[:50])
        ===OCTAVE_LITERACY_PRIMER===
    """
    primers_dir = _get_primers_dir()
    primer_file = primers_dir / f"{name}.oct.md"

    if not primer_file.exists():
        available = list_available_primers()
        raise FileNotFoundError(f"Primer '{name}' not found. Available: {', '.join(available)}")

    return primer_file.read_text()


def list_available_primers() -> list[str]:
    """List all available primers in the octave-mcp package.

    Returns:
        List of primer names (without .oct.md extension)

    Example:
        >>> primers = list_available_primers()
        >>> "octave-literacy-primer" in primers
        True
    """
    try:
        primers_dir = _get_primers_dir()
        return sorted(
            f.stem.replace(".oct", "") for f in primers_dir.glob("*.oct.md") if f.is_file()
        )
    except (ImportError, FileNotFoundError):
        return []


def get_literacy_primer() -> str:
    """Get the basic OCTAVE literacy primer (~40 tokens).

    This is the recommended primer for basic OCTAVE syntax understanding.
    It's compact enough to include in every agent turn without significant
    token overhead.

    Returns:
        The octave-literacy-primer content

    Example:
        >>> primer = get_literacy_primer()
        >>> "===OCTAVE_LITERACY_PRIMER===" in primer
        True
    """
    return load_primer("octave-literacy-primer")


def get_mastery_primer() -> str:
    """Get the advanced OCTAVE mastery primer.

    This primer includes advanced patterns and techniques. Use when
    agents need to produce more sophisticated OCTAVE output.

    Returns:
        The octave-mastery-primer content
    """
    return load_primer("octave-mastery-primer")
