# moods/management/commands/seed_moods.py
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from moods.models import MoodEntry


@dataclass(frozen=True)
class BiasConfig:
    """Weights for drawing scores (-4..+4) depending on bias."""
    # order must match SCORES_ASC below
    weights: tuple[int, ...]


# Immutable score axis from the model choice range
SCORES_ASC: tuple[int, ...] = (-4, -3, -2, -1, 0, 1, 2, 3, 4)

# Simple, hand-tuned weights for the demo
BIAS_WEIGHTS = {
    "neg": BiasConfig(weights=(10, 9, 8, 7, 6, 4, 3, 2, 1)),
    "neutral": BiasConfig(weights=(2, 3, 5, 8, 10, 8, 5, 3, 2)),
    "pos": BiasConfig(weights=(1, 2, 3, 4, 6, 7, 8, 9, 10)),
}


def _iter_workdays(days: int, end_date: date, include_weekends: bool) -> Iterable[date]:
    """Yield dates from (end_date - days + 1) .. end_date, optionally skipping weekends."""
    start = end_date - timedelta(days=days - 1)
    d = start
    while d <= end_date:
        if include_weekends or d.weekday() < 5:  # 0=Mon .. 6=Sun
            yield d
        d += timedelta(days=1)


def _pick_score(bias: str) -> int:
    """Draw a score using the configured bias weights."""
    conf = BIAS_WEIGHTS[bias]
    return random.choices(SCORES_ASC, weights=conf.weights, k=1)[0]


class Command(BaseCommand):
    """Seed demo users and mood entries for local/dev demos.

    Examples:
        python manage.py seed_moods --users 8 --days 365 --seed 42 --bias neg
        python manage.py seed_moods --reset-only
        python manage.py seed_moods --clear --delete-users

    Safety:
        - Only touches users whose username starts with the given prefix (default 'demo').
        - Mood entries are created/updated idempotently via (user, date) uniqueness.
    """

    help = "Seed demo users and mood entries (idempotent)."

    def add_arguments(self, parser):
        # Core seeding controls
        parser.add_argument("--users", type=int, default=8, help="Number of demo users to ensure/create (default: 8).")
        parser.add_argument("--password", type=str, default="demo1234", help="Password for created demo users.")
        parser.add_argument("--days", type=int, default=30, help="Number of calendar days to seed (default: 30).")
        parser.add_argument(
            "--start",
            type=str,
            default=None,
            help="End date (YYYY-MM-DD) to seed up to (default: today in project timezone).",
        )
        parser.add_argument(
            "--bias",
            type=str,
            choices=("neg", "neutral", "pos"),
            default="neutral",
            help="Distribution bias for scores (default: neutral).",
        )
        parser.add_argument(
            "--include-weekends",
            action="store_true",
            help="Include Saturdays/Sundays (default: skip weekends).",
        )

        # Determinism
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Random seed for reproducible results (optional).",
        )

        # Safety / cleanup
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete mood entries for demo users (keeps users).",
        )
        parser.add_argument(
            "--users-only",
            action="store_true",
            help="Create/ensure users but do not generate mood entries.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Shortcut: --clear + --delete-users.",
        )
        parser.add_argument(
            "--delete-users",
            action="store_true",
            help="Delete demo users (non-superusers) with the chosen prefix.",
        )
        parser.add_argument(
            "--reset-only",
            action="store_true",
            help="Perform reset (clear entries + delete users) and exit.",
        )

        parser.add_argument(
            "--username-prefix",
            type=str,
            default="demo",
            help="Username prefix for demo users (default: 'demo').",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        # Seed RNG for reproducibility if requested
        seed: Optional[int] = opts.get("seed")
        if seed is not None:
            random.seed(seed)
            self.stdout.write(self.style.NOTICE(f"[seed] Using random seed {seed}"))

        # Resolve options
        users: int = int(opts["users"])
        password: str = str(opts["password"])
        days: int = int(opts["days"])
        start_raw: Optional[str] = opts.get("start") or None
        include_weekends: bool = bool(opts["include_weekends"])
        bias: str = str(opts["bias"])
        do_clear: bool = bool(opts["clear"])
        users_only: bool = bool(opts["users_only"])
        do_reset: bool = bool(opts["reset"])
        delete_users: bool = bool(opts["delete_users"])
        reset_only: bool = bool(opts["reset_only"])
        prefix: str = str(opts["username_prefix"]).strip() or "demo"

        User = get_user_model()

        # Compute date range
        today = timezone.localdate()
        end_date = date.fromisoformat(start_raw) if start_raw else today

        # Reset switches
        if do_reset:
            do_clear = True
            delete_users = True

        # Clear entries?
        if do_clear or reset_only:
            qs = MoodEntry.objects.filter(user__username__startswith=prefix)
            deleted, _ = qs.delete()
            self.stdout.write(self.style.WARNING(f"[clear] Deleted {deleted} mood entries for users '{prefix}*'."))

        # Delete users?
        if delete_users or reset_only:
            uqs = User.objects.filter(username__startswith=prefix, is_superuser=False)
            ucount = uqs.count()
            uqs.delete()
            self.stdout.write(self.style.WARNING(f"[users] Deleted {ucount} users '{prefix}*' (non-superusers)."))

        if reset_only:
            self.stdout.write(self.style.SUCCESS("[done] Reset-only completed."))
            return

        # Ensure demo users exist
        ensured_users = []
        for i in range(1, users + 1):
            username = f"{prefix}{i:02d}"
            u, created = User.objects.get_or_create(username=username, defaults={"is_active": True})
            if created or not u.has_usable_password():
                u.set_password(password)
                u.save(update_fields=["password"])
            ensured_users.append(u)
        self.stdout.write(self.style.NOTICE(f"[users] Ensured {len(ensured_users)} users with prefix '{prefix}'."))

        if users_only:
            self.stdout.write(self.style.SUCCESS("[done] Users created/ensured (no entries generated)."))
            return

        # Generate mood entries
        count_created = 0
        count_updated = 0
        for u in ensured_users:
            for d in _iter_workdays(days=days, end_date=end_date, include_weekends=include_weekends):
                score = _pick_score(bias)
                # idempotent upsert
                obj, created = MoodEntry.objects.get_or_create(user=u, date=d, defaults={"score": score})
                if not created:
                    # Update existing to make runs with --seed deterministic w.r.t. distribution
                    obj.score = score
                    obj.save(update_fields=["score", "updated_at"])
                    count_updated += 1
                else:
                    count_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[done] Entries created: {count_created}, updated: {count_updated} "
                f"(users={len(ensured_users)}, days={days}, bias={bias}, weekends={'on' if include_weekends else 'off'})"
            )
        )
