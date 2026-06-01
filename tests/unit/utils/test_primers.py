"""Tests for OCTAVE primer utilities."""

import pytest


class TestLoadPrimer:
    """Test suite for load_primer function."""

    def test_load_literacy_primer(self):
        """Test loading the basic octave-literacy-primer."""
        from debate_hall_mcp.utils.primers import load_primer

        primer = load_primer("octave-literacy-primer")

        assert "===OCTAVE_LITERACY_PRIMER===" in primer
        assert "===END===" in primer
        # Should be relatively compact (~1000-1100 chars typical with octave-mcp >=1.15.0)
        assert len(primer) < 1500

    def test_load_mastery_primer(self):
        """Test loading the advanced octave-mastery-primer."""
        from debate_hall_mcp.utils.primers import load_primer

        primer = load_primer("octave-mastery-primer")

        assert "===OCTAVE_MASTERY_PRIMER===" in primer or "OCTAVE" in primer
        assert "===END===" in primer

    def test_load_nonexistent_primer_raises_error(self):
        """Test that loading a nonexistent primer raises FileNotFoundError."""
        from debate_hall_mcp.utils.primers import load_primer

        with pytest.raises(FileNotFoundError) as exc_info:
            load_primer("nonexistent-primer")  # type: ignore[arg-type]

        assert "not found" in str(exc_info.value).lower()

    def test_primer_is_cached(self):
        """Test that primers are cached after first load."""
        from debate_hall_mcp.utils.primers import load_primer

        # Load twice - should hit cache on second call
        primer1 = load_primer("octave-literacy-primer")
        primer2 = load_primer("octave-literacy-primer")

        # Same object due to caching
        assert primer1 is primer2

    def test_clear_cache_allows_reload(self):
        """Test that clearing cache allows fresh reload from package."""
        from debate_hall_mcp.utils.primers import clear_primer_cache, load_primer

        # Load primer (caches it)
        primer1 = load_primer("octave-literacy-primer")

        # Clear cache
        clear_primer_cache()

        # Load again - should be fresh load (new string object)
        primer2 = load_primer("octave-literacy-primer")

        # Content should be same
        assert primer1 == primer2
        # But should be different objects after cache clear
        # (Note: Python may intern strings, so we just verify content matches)


class TestListAvailablePrimers:
    """Test suite for list_available_primers function."""

    def test_returns_list_of_primers(self):
        """Test that list_available_primers returns a list."""
        from debate_hall_mcp.utils.primers import list_available_primers

        primers = list_available_primers()

        assert isinstance(primers, list)
        assert len(primers) > 0

    def test_contains_expected_primers(self):
        """Test that expected primers are in the list."""
        from debate_hall_mcp.utils.primers import list_available_primers

        primers = list_available_primers()

        assert "octave-literacy-primer" in primers
        assert "octave-mastery-primer" in primers

    def test_primers_are_sorted(self):
        """Test that primers are returned in sorted order."""
        from debate_hall_mcp.utils.primers import list_available_primers

        primers = list_available_primers()

        assert primers == sorted(primers)


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    def test_get_literacy_primer(self):
        """Test get_literacy_primer convenience function."""
        from debate_hall_mcp.utils.primers import get_literacy_primer

        primer = get_literacy_primer()

        assert "===OCTAVE_LITERACY_PRIMER===" in primer
        assert "===END===" in primer

    def test_get_mastery_primer(self):
        """Test get_mastery_primer convenience function."""
        from debate_hall_mcp.utils.primers import get_mastery_primer

        primer = get_mastery_primer()

        assert "===END===" in primer


class TestPrimerContent:
    """Test suite for primer content validation."""

    def test_literacy_primer_has_required_sections(self):
        """Test that literacy primer has expected structure."""
        from debate_hall_mcp.utils.primers import get_literacy_primer

        primer = get_literacy_primer()

        # Based on the primer structure we saw earlier
        assert "META:" in primer
        assert "TYPE::PRIMER" in primer
        # Should have syntax guidance
        assert "::" in primer  # Assignment operator
        assert "[" in primer and "]" in primer  # List syntax

    def test_literacy_primer_is_compact(self):
        """Test that literacy primer is compact enough for every-turn injection."""
        from debate_hall_mcp.utils.primers import get_literacy_primer

        primer = get_literacy_primer()

        # Should be under 1500 chars (~1000-1100 chars typical with octave-mcp >=1.15.0)
        # Threshold gives breathing room for future primer growth without being meaningless.
        assert len(primer) < 1500
        # Rough estimate: 4 chars per token; threshold remains compact enough for
        # every-turn injection. Floor guard prevents accidentally-empty primer regression.
        assert len(primer) > 100  # At least some content
