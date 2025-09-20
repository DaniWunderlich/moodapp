from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from moods.models import MoodEntry


def make_entry(username: str, days_ago: int, score: int) -> MoodEntry:
    """Helper to create a user and a mood entry `days_ago` days from today."""
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username, defaults={"password": "x"})
    # set a password if not created
    if not user.has_usable_password():
        user.set_password("x")
        user.save()
    d = timezone.localdate() - timedelta(days=days_ago)
    return MoodEntry.objects.create(user=user, date=d, score=score)


class AuthRequiredTests(TestCase):
    """Basic auth coverage for all login-protected views."""

    def test_login_required_redirects(self) -> None:
        c = Client()
        for name in ("moods:today", "moods:history", "moods:team"):
            resp = c.get(reverse(name))
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/accounts/login/", resp["Location"])


class TodayViewTests(TestCase):
    """Tests for creating/updating today's entry."""

    def setUp(self) -> None:
        self.User = get_user_model()
        self.user = self.User.objects.create_user("bob", password="pw")
        self.client = Client()
        self.client.login(username="bob", password="pw")

    def test_get_does_not_autocreate(self) -> None:
        """GET should not create a MoodEntry implicitly."""
        resp = self.client.get(reverse("moods:today"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(MoodEntry.objects.filter(user=self.user).count(), 0)

    def test_post_creates_entry(self) -> None:
        """POST should create a new entry and redirect to team overview."""
        payload = {"score": MoodEntry.Score.PLUS_2, "note": "yay"}
        resp = self.client.post(reverse("moods:today"), data=payload, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith(reverse("moods:team")))
        qs = MoodEntry.objects.filter(user=self.user)
        self.assertEqual(qs.count(), 1)
        e = qs.get()
        self.assertEqual(e.score, MoodEntry.Score.PLUS_2)
        self.assertEqual(e.note, "yay")

    def test_post_updates_existing_entry(self) -> None:
        """Posting again for the same day should update the existing row."""
        today = timezone.localdate()
        MoodEntry.objects.create(user=self.user, date=today, score=0, note="old")
        payload = {"score": MoodEntry.Score.MINUS_1, "note": "new"}
        resp = self.client.post(reverse("moods:today"), data=payload)
        self.assertEqual(resp.status_code, 302)
        e = MoodEntry.objects.get(user=self.user, date=today)
        self.assertEqual(e.score, MoodEntry.Score.MINUS_1)
        self.assertEqual(e.note, "new")


class HistoryViewTests(TestCase):
    """Tests for the history page and its chart context."""

    def setUp(self) -> None:
        self.User = get_user_model()
        self.user = self.User.objects.create_user("carol", password="pw")
        self.client = Client()
        self.client.login(username="carol", password="pw")

    def test_history_default_30_days_window(self) -> None:
        """Default window is 30 days; chart dict should be present."""
        # Create some entries within last 10 days
        for i, s in enumerate([0, 1, -2, 3, -1, 4, -4, 2, 0, 1]):
            d = timezone.localdate() - timedelta(days=9 - i)
            MoodEntry.objects.create(user=self.user, date=d, score=s)
        resp = self.client.get(reverse("moods:history"))
        self.assertEqual(resp.status_code, 200)
        chart = resp.context["chart"]
        self.assertIsInstance(chart, dict)
        self.assertIn("bars", chart)
        self.assertGreater(len(chart["bars"]), 0)
        # bars should carry pos/neg classes coherently
        classes = {b["cls"] for b in chart["bars"]}
        self.assertTrue(classes.issubset({"pos", "neg"}))

    def test_history_custom_days_validated(self) -> None:
        """?days is validated against whitelist; illegal falls back to default."""
        resp = self.client.get(reverse("moods:history") + "?days=999")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["days"], 30)
        resp2 = self.client.get(reverse("moods:history") + "?days=14")
        self.assertEqual(resp2.context["days"], 14)


class TeamViewTests(TestCase):
    """Tests for team overview (aggregated + weekly)."""

    def setUp(self) -> None:
        self.client = Client()
        # Prepare multiple users and entries across 7 days
        for days_ago in range(0, 7):
            make_entry("u1", days_ago, score=days_ago % 5 - 2)  # -2..+2 cycle
            make_entry("u2", days_ago, score=2)
            make_entry("u3", days_ago, score=-1)

        # Login a user to access views
        User = get_user_model()
        self.user = User.objects.create_user("dave", password="pw")
        self.client.login(username="dave", password="pw")

    def test_aggregated_default(self) -> None:
        """Aggregated view should show 9 bars (-4..+4) and rows for all scores."""
        resp = self.client.get(reverse("moods:team"))
        self.assertEqual(resp.status_code, 200)
        ctx: dict[str, Any] = resp.context  # type: ignore[assignment]
        self.assertEqual(ctx["range_param"], "day")
        self.assertIn("rows", ctx)
        self.assertEqual(len(ctx["rows"]), 9)  # -4..+4
        chart = ctx["chart"]
        self.assertEqual(len(chart["bars"]), 9)

    def test_aggregated_custom_days(self) -> None:
        """Dropdown param should control the window size."""
        resp = self.client.get(reverse("moods:team") + "?days=7")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["days"], 7)

    def test_weekly_view(self) -> None:
        """Weekly view should render 7 day rows with avg/median buckets."""
        resp = self.client.get(reverse("moods:team") + "?range=week")
        self.assertEqual(resp.status_code, 200)
        ctx = resp.context
        self.assertEqual(ctx["range_param"], "week")
        self.assertIn("day_rows", ctx)
        self.assertEqual(len(ctx["day_rows"]), 7)
        # Buckets must be in [-4..4] or None
        for row in ctx["day_rows"]:
            for key in ("avg_bucket", "med_bucket"):
                b = row[key]
                if b is not None:
                    self.assertGreaterEqual(b, -4)
                    self.assertLessEqual(b, 4)
