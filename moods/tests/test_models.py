from __future__ import annotations

from datetime import date
from typing import cast

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from moods.models import MoodEntry


class MoodEntryModelTests(TestCase):
    """Unit tests for the MoodEntry model."""

    @classmethod
    def setUpTestData(cls) -> None:
        User = get_user_model()
        cls.user = User.objects.create_user(username="alice", password="x")
        cls.today = timezone.localdate()

    def test_create_valid_entry(self) -> None:
        """Creating a valid entry should succeed and render a readable __str__."""
        e = MoodEntry.objects.create(
            user=self.user, date=self.today, score=MoodEntry.Score.PLUS_2
        )
        self.assertEqual(e.user, self.user)
        self.assertEqual(e.date, self.today)
        self.assertEqual(e.score, MoodEntry.Score.PLUS_2)
        # No crash on __str__ and contains basic info
        s = str(e)
        self.assertIn("alice", s)
        self.assertIn(str(self.today), s)

    def test_unique_per_user_and_date(self) -> None:
        """(user, date) must be unique."""
        MoodEntry.objects.create(
            user=self.user, date=self.today, score=MoodEntry.Score.ZERO
        )
        with self.assertRaises(IntegrityError):
            MoodEntry.objects.create(
                user=self.user, date=self.today, score=MoodEntry.Score.PLUS_1
            )

    def test_score_check_constraint(self) -> None:
        """DB-level check should prevent scores outside [-4..4]."""
        # NOTE: This relies on DB enforcing CHECK constraints (SQLite/Postgres do).
        with self.assertRaises(IntegrityError):
            MoodEntry.objects.create(user=self.user, date=self.today, score=99)

    def test_score_label_property(self) -> None:
        """score_label should return the human readable label."""
        e = MoodEntry.objects.create(
            user=self.user, date=self.today, score=MoodEntry.Score.MINUS_3
        )
        label = e.score_label
        self.assertIsInstance(label, str)
        self.assertNotEqual(label.strip(), "")
        # Should match the choices mapping
        labels = dict(cast(list[tuple[int, str]], MoodEntry.Score.choices))
        self.assertEqual(label, labels[e.score])

    def test_default_ordering(self) -> None:
        """Newest first by date, then by created_at."""
        d1 = self.today
        d2 = date.fromordinal(self.today.toordinal() - 1)
        MoodEntry.objects.create(user=self.user, date=d2, score=0)
        MoodEntry.objects.create(user=self.user, date=d1, score=1)
        qs = list(MoodEntry.objects.filter(user=self.user))
        self.assertEqual([e.date for e in qs], [d1, d2])
