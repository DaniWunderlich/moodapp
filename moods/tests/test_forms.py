from __future__ import annotations

from django.test import TestCase

from moods.forms import MoodEntryForm
from moods.models import MoodEntry


class MoodEntryFormTests(TestCase):
    """Unit tests for the MoodEntryForm."""

    def test_fields_and_widgets(self) -> None:
        """Ensure field presence, required flags, and widget types."""
        form = MoodEntryForm()
        self.assertIn("score", form.fields)
        self.assertIn("note", form.fields)
        self.assertTrue(form.fields["score"].required)
        # score comes from model choices; we expect 9 choices (-4..+4)
        self.assertEqual(len(form.fields["score"].choices), 9)

    def test_valid_submission(self) -> None:
        """A valid POST payload should validate."""
        form = MoodEntryForm(data={"score": MoodEntry.Score.PLUS_1, "note": "Feeling ok"})
        self.assertTrue(form.is_valid())

    def test_invalid_submission_missing_score(self) -> None:
        """Score is required."""
        form = MoodEntryForm(data={"note": "oops"})
        self.assertFalse(form.is_valid())
        self.assertIn("score", form.errors)
