"""Tests for consult tool — Issue #177.

Phase 2 of the headless governance chat API (Issue #173).
The consult tool creates advisory consultation sessions where
an agent asks an expert for guidance.

TDD Discipline: RED phase — these tests are written BEFORE implementation.
"""

import re
from pathlib import Path

import pytest

from debate_hall_mcp.state import (
    SessionType,
    load_debate_state,
)

# Import the function under test (will not exist yet during RED phase)
from debate_hall_mcp.tools.consult import consult
from debate_hall_mcp.tools.pick import debate_pick
from debate_hall_mcp.tools.turn import debate_turn


class TestConsultCreatesSession:
    """consult() creates a consultation session with correct properties."""

    def test_consult_returns_expected_shape(self, tmp_path: Path) -> None:
        """consult() returns dict with all required keys."""
        result = consult(
            topic="TDD guidance",
            advisor_role="TMG",
            question="Best TDD pattern for async providers?",
            state_dir=tmp_path,
        )

        assert "thread_id" in result
        assert result["status"] == "active"
        assert result["session_type"] == "consultation"
        assert result["question"] == "Best TDD pattern for async providers?"
        assert result["advisor_role"] == "TMG"
        assert result["questioner_role"] == "Questioner"
        assert result["awaiting"] == "TMG"
        assert result["turn_count"] == 1

    def test_consult_creates_room_with_consultation_session_type(self, tmp_path: Path) -> None:
        """Room created by consult() has session_type=consultation."""
        result = consult(
            topic="Architecture review",
            advisor_role="CE",
            question="Is this design scalable?",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.session_type == SessionType.CONSULTATION

    def test_consult_creates_room_in_mediated_mode(self, tmp_path: Path) -> None:
        """Room created by consult() uses mediated mode."""
        result = consult(
            topic="Mode check",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.mode.value == "mediated"

    def test_consult_sets_participants(self, tmp_path: Path) -> None:
        """Room has two participants: questioner and advisor."""
        result = consult(
            topic="Participants check",
            advisor_role="TMG",
            question="Question?",
            questioner_role="DevLead",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.participants is not None
        assert len(room.participants) == 2
        roles = [p.role for p in room.participants]
        assert "DevLead" in roles
        assert "TMG" in roles

    def test_consult_custom_questioner_role(self, tmp_path: Path) -> None:
        """consult() accepts custom questioner_role."""
        result = consult(
            topic="Custom questioner",
            advisor_role="CE",
            question="Is this safe?",
            questioner_role="SecurityLead",
            state_dir=tmp_path,
        )

        assert result["questioner_role"] == "SecurityLead"

    def test_consult_custom_max_turns(self, tmp_path: Path) -> None:
        """consult() accepts custom max_turns."""
        result = consult(
            topic="Max turns check",
            advisor_role="TMG",
            question="Question?",
            max_turns=10,
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.max_turns == 10

    def test_consult_default_max_turns_is_six(self, tmp_path: Path) -> None:
        """consult() defaults max_turns to 6."""
        result = consult(
            topic="Default max turns",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.max_turns == 6


class TestConsultQuestionRecording:
    """Question is recorded as the first turn with correct role."""

    def test_question_recorded_as_first_turn(self, tmp_path: Path) -> None:
        """The question is the first turn in the transcript."""
        result = consult(
            topic="First turn check",
            advisor_role="TMG",
            question="What is the best approach?",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert len(room.turns) == 1
        assert room.turns[0].content == "What is the best approach?"

    def test_question_turn_has_questioner_role(self, tmp_path: Path) -> None:
        """The question turn uses the questioner_role."""
        result = consult(
            topic="Questioner role check",
            advisor_role="TMG",
            question="Question?",
            questioner_role="DevLead",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.turns[0].role == "DevLead"

    def test_question_turn_default_questioner_role(self, tmp_path: Path) -> None:
        """Default questioner_role is 'Questioner'."""
        result = consult(
            topic="Default questioner",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.turns[0].role == "Questioner"


class TestConsultContextHandling:
    """Context is prepended as [CONTEXT]...[/CONTEXT] block."""

    def test_context_prepended_to_question(self, tmp_path: Path) -> None:
        """When context is provided, it's prepended in [CONTEXT] block."""
        result = consult(
            topic="Context test",
            advisor_role="TMG",
            question="What pattern should I use?",
            context="We are building an async provider layer.",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        content = room.turns[0].content
        assert content.startswith("[CONTEXT]")
        assert "We are building an async provider layer." in content
        assert "[/CONTEXT]" in content
        assert "What pattern should I use?" in content

    def test_context_format_exact(self, tmp_path: Path) -> None:
        """Context block follows exact format from contract."""
        result = consult(
            topic="Exact format",
            advisor_role="TMG",
            question="The question",
            context="The context",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        expected = "[CONTEXT]\nThe context\n[/CONTEXT]\n\nThe question"
        assert room.turns[0].content == expected

    def test_no_context_means_plain_question(self, tmp_path: Path) -> None:
        """When context is None, turn content is just the question."""
        result = consult(
            topic="No context",
            advisor_role="TMG",
            question="Plain question",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.turns[0].content == "Plain question"

    def test_empty_context_string_treated_as_no_context(self, tmp_path: Path) -> None:
        """Empty string context is treated as no context."""
        result = consult(
            topic="Empty context",
            advisor_role="TMG",
            question="Plain question",
            context="",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.turns[0].content == "Plain question"


class TestConsultExpectedNextRole:
    """expected_next_role is set to advisor_role after consult()."""

    def test_expected_next_role_set_to_advisor(self, tmp_path: Path) -> None:
        """After consult(), expected_next_role is the advisor."""
        result = consult(
            topic="Next role check",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        room = load_debate_state(result["thread_id"], tmp_path)
        assert room.expected_next_role == "TMG"


class TestConsultAdvisorCanRespond:
    """Advisor can respond via add_turn() after consult()."""

    def test_advisor_responds_via_add_turn(self, tmp_path: Path) -> None:
        """Advisor can add a turn after consult() sets up the session."""
        result = consult(
            topic="Advisor response",
            advisor_role="TMG",
            question="Best TDD pattern?",
            state_dir=tmp_path,
        )

        turn_result = debate_turn(
            thread_id=result["thread_id"],
            role="TMG",
            content="Use the AAA pattern for async providers.",
            state_dir=tmp_path,
        )

        assert turn_result["role"] == "TMG"
        assert turn_result["turn_count"] == 2

    def test_wrong_role_rejected_after_consult(self, tmp_path: Path) -> None:
        """A non-advisor role is rejected when expected_next_role is set."""
        result = consult(
            topic="Wrong role test",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        with pytest.raises(ValueError, match="Expected role 'TMG'"):
            debate_turn(
                thread_id=result["thread_id"],
                role="Questioner",
                content="This should fail.",
                state_dir=tmp_path,
            )


class TestConsultFollowUpTurns:
    """Follow-up turns work: questioner -> advisor -> questioner -> advisor."""

    def test_full_conversation_flow(self, tmp_path: Path) -> None:
        """Full consult flow: question -> advisor -> follow-up -> advisor."""
        result = consult(
            topic="Full flow",
            advisor_role="TMG",
            question="Best pattern?",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]

        # Advisor responds
        debate_turn(
            thread_id=tid,
            role="TMG",
            content="Use AAA pattern.",
            state_dir=tmp_path,
        )

        # Questioner follows up (need to pick first)
        debate_pick(thread_id=tid, role="Questioner", state_dir=tmp_path)
        debate_turn(
            thread_id=tid,
            role="Questioner",
            content="What about error cases?",
            state_dir=tmp_path,
        )

        # Advisor responds again
        debate_pick(thread_id=tid, role="TMG", state_dir=tmp_path)
        debate_turn(
            thread_id=tid,
            role="TMG",
            content="Error cases should use...",
            state_dir=tmp_path,
        )

        room = load_debate_state(tid, tmp_path)
        assert len(room.turns) == 4
        assert room.turns[0].role == "Questioner"
        assert room.turns[1].role == "TMG"
        assert room.turns[2].role == "Questioner"
        assert room.turns[3].role == "TMG"


class TestConsultGetDebateIntegration:
    """get_debate() returns session_type='consultation' and participants."""

    def test_get_debate_shows_consultation_type(self, tmp_path: Path) -> None:
        """get_debate returns session_type='consultation' for consult sessions."""
        from debate_hall_mcp.tools.get import debate_get

        result = consult(
            topic="Get debate test",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        debate_info = debate_get(thread_id=result["thread_id"], state_dir=tmp_path)
        assert debate_info["session_type"] == "consultation"
        assert debate_info["participants"] is not None
        assert len(debate_info["participants"]) == 2


class TestConsultThreadIdGeneration:
    """Thread ID auto-generation follows expected format."""

    def test_auto_generated_thread_id_format(self, tmp_path: Path) -> None:
        """Auto-generated thread_id follows YYYY-MM-DD-{slug}-consult-{ulid} format."""
        result = consult(
            topic="TDD guidance",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )

        tid = result["thread_id"]
        # Must start with date prefix
        assert re.match(r"^\d{4}-\d{2}-\d{2}-", tid)
        # Must contain 'consult' marker
        assert "consult" in tid

    def test_custom_thread_id_used_as_is(self, tmp_path: Path) -> None:
        """Custom thread_id is used directly."""
        result = consult(
            topic="Custom ID",
            advisor_role="TMG",
            question="Question?",
            thread_id="2026-02-21-my-custom-consult",
            state_dir=tmp_path,
        )

        assert result["thread_id"] == "2026-02-21-my-custom-consult"


class TestConsultValidation:
    """Validation rules enforced per contract."""

    def test_empty_advisor_role_raises(self, tmp_path: Path) -> None:
        """Empty advisor_role raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="",
                question="Question?",
                state_dir=tmp_path,
            )

    def test_whitespace_advisor_role_raises(self, tmp_path: Path) -> None:
        """Whitespace-only advisor_role raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="   ",
                question="Question?",
                state_dir=tmp_path,
            )

    def test_non_ascii_advisor_role_raises(self, tmp_path: Path) -> None:
        """Non-ASCII advisor_role raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="role\u00e9",
                question="Question?",
                state_dir=tmp_path,
            )

    def test_too_long_advisor_role_raises(self, tmp_path: Path) -> None:
        """advisor_role > 128 chars raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="A" * 129,
                question="Question?",
                state_dir=tmp_path,
            )

    def test_empty_questioner_role_raises(self, tmp_path: Path) -> None:
        """Empty questioner_role raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="Question?",
                questioner_role="",
                state_dir=tmp_path,
            )

    def test_whitespace_questioner_role_raises(self, tmp_path: Path) -> None:
        """Whitespace-only questioner_role raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="Question?",
                questioner_role="   ",
                state_dir=tmp_path,
            )

    def test_same_advisor_and_questioner_raises(self, tmp_path: Path) -> None:
        """advisor_role == questioner_role raises ValueError."""
        with pytest.raises(ValueError, match="must be distinct|same"):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="Question?",
                questioner_role="TMG",
                state_dir=tmp_path,
            )

    def test_empty_topic_raises(self, tmp_path: Path) -> None:
        """Empty topic raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="",
                advisor_role="TMG",
                question="Question?",
                state_dir=tmp_path,
            )

    def test_whitespace_topic_raises(self, tmp_path: Path) -> None:
        """Whitespace-only topic raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="   ",
                advisor_role="TMG",
                question="Question?",
                state_dir=tmp_path,
            )

    def test_empty_question_raises(self, tmp_path: Path) -> None:
        """Empty question raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="",
                state_dir=tmp_path,
            )

    def test_whitespace_question_raises(self, tmp_path: Path) -> None:
        """Whitespace-only question raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="   ",
                state_dir=tmp_path,
            )

    def test_duplicate_thread_id_raises(self, tmp_path: Path) -> None:
        """Duplicate thread_id raises ValueError."""
        consult(
            topic="First",
            advisor_role="TMG",
            question="Question?",
            thread_id="2026-02-21-duplicate-test",
            state_dir=tmp_path,
        )

        with pytest.raises((ValueError, FileExistsError)):
            consult(
                topic="Second",
                advisor_role="CE",
                question="Another question?",
                thread_id="2026-02-21-duplicate-test",
                state_dir=tmp_path,
            )

    def test_non_ascii_questioner_role_raises(self, tmp_path: Path) -> None:
        """Non-ASCII questioner_role raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="Question?",
                questioner_role="role\u00e9",
                state_dir=tmp_path,
            )

    def test_too_long_questioner_role_raises(self, tmp_path: Path) -> None:
        """questioner_role > 128 chars raises ValueError."""
        with pytest.raises(ValueError):
            consult(
                topic="Test",
                advisor_role="TMG",
                question="Question?",
                questioner_role="B" * 129,
                state_dir=tmp_path,
            )


class TestConsultSlugEdgeCases:
    """Thread ID slug generation handles edge-case topics."""

    def test_leading_whitespace_topic(self, tmp_path: Path) -> None:
        """Topics with leading whitespace produce valid thread IDs."""
        result = consult(
            topic="  hello world",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}-[a-zA-Z0-9]", tid)

    def test_emoji_only_topic(self, tmp_path: Path) -> None:
        """Emoji-only topics fall back to 'consult' slug."""
        result = consult(
            topic="\U0001f525\U0001f525",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}-consult-consult-", tid)

    def test_multiple_spaces_topic(self, tmp_path: Path) -> None:
        """Topics with multiple spaces don't produce consecutive hyphens."""
        result = consult(
            topic="hello   world",
            advisor_role="TMG",
            question="Question?",
            state_dir=tmp_path,
        )
        tid = result["thread_id"]
        assert "--" not in tid.split("-consult-")[0]  # No double hyphens in subject
