# moods/tests/conftest.py
from __future__ import annotations

import itertools
from collections import Counter
from datetime import timedelta
from typing import Callable, Iterable

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from moods.models import MoodEntry


@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db) -> None:  # noqa: PT004
    """Grant DB access to all tests by default (pytest-django)."""
    pass


@pytest.fixture
def today():
    """Return today's local date once per test."""
    return timezone.localdate()


@pytest.fixture
def make_user() -> Callable[..., any]:
    """Factory fixture creating users with unique usernames."""
    seq = itertools.count(1)
    User = get_user_model()

    def _create(**kwargs):
        i = next(seq)
        username = kwargs.pop("username", f"user{i}")
        password = kwargs.pop("password", "pw")
        user = User.objects.create_user(username=username, password=password, **kwargs)
        return user

    return _create


@pytest.fixture
def auth_client(make_user) -> Client:
    """Logged-in Django test client."""
    user = make_user(username="tester")
    client = Client()
    client.login(username="tester", password="pw")
    return client


@pytest.fixture
def make_mood_entry():
    """Factory for MoodEntry rows."""

    def _make(*, user, days_ago: int = 0, score: int = 0, note: str = "") -> MoodEntry:
        d = timezone.localdate() - timedelta(days=days_ago)
        return MoodEntry.objects.create(user=user, date=d, score=score, note=note)

    return _make


@pytest.fixture
def seed_week(make_user, make_mood_entry):
    """Create a small 7-day dataset across 3 users for team views."""
    u1 = make_user(username="u1")
    u2 = make_user(username="u2")
    u3 = make_user(username="u3")
    for days_ago in range(0, 7):
        make_mood_entry(user=u1, days_ago=days_ago, score=(days_ago % 5) - 2)  # cycle -2..+2
        make_mood_entry(user=u2, days_ago=days_ago, score=2)
        make_mood_entry(user=u3, days_ago=days_ago, score=-1)
    return (u1, u2, u3)
