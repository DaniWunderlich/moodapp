from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class MoodEntry(models.Model):
    """Single daily mood entry for a user."""

    class Score(models.IntegerChoices):
        MINUS_4 = -4, _("no comment ☠️")
        MINUS_3 = -3, _("unterirdisch 💀")
        MINUS_2 = -2, _("meh 😵‍💫")
        MINUS_1 = -1, _("mau 🙁")
        ZERO    =  0, _("passt scho 😐")
        PLUS_1  =  1, _("ganz okay 🙂")
        PLUS_2  =  2, _("gut drauf 😎")
        PLUS_3  =  3, _("geilo 🤩")
        PLUS_4  =  4, _("geilomatico 🚀")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mood_entries",
        verbose_name=_("User"),
    )
    date = models.DateField(
        default=timezone.localdate,
        verbose_name=_("Date"),
        help_text=_("Local date of the entry (one per user & day)."),
    )
    score = models.IntegerField(
        choices=Score.choices,
        verbose_name=_("Score"),
        help_text=_("Mood score from -4 to +4."),
    )
    note = models.CharField(
        max_length=280,
        blank=True,
        default="",
        verbose_name=_("Note"),
        help_text=_("Optional short comment (max. 280 chars)."),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            # Ensure a user can only create one entry per day.
            models.UniqueConstraint(
                fields=["user", "date"], name="unique_mood_per_user_per_date"
            ),
            # DB-level guard: score stays within the known range.
            models.CheckConstraint(
                condition=models.Q(score__gte=-4, score__lte=4),
                name="score_in_range"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "date"], name="idx_user_date"),
        ]
        verbose_name = _("Mood entry")
        verbose_name_plural = _("Mood entries")

    @property
    def score_label(self) -> str:
        """Human-readable, localized label for the current score.

        Returns:
            str: Display label from the `choices`, localized.
        """
        # Django auto-generates `get_score_display()` for fields with `choices`.
        # Static analyzers don't know it; cast to Any to silence any warning.
        return cast(Any, self).get_score_display()

    def __str__(self) -> str:
        """Readable string for admin/debug."""
        return f"{self.user} @ {self.date}: {self.score_label}"
