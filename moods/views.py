from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Optional, Sequence

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from .forms import MoodEntryForm
from .models import MoodEntry


# =============================================================================
# Score constants (single source of truth from the model)
# =============================================================================

# Immutable tuples to prevent accidental mutation.
SCORES: tuple[int, ...] = tuple(val for val, _ in MoodEntry.Score.choices)   # e.g. (-4, -3, ..., 4)
SCORES_ASC: tuple[int, ...] = tuple(sorted(SCORES))                          # (-4..4)
SCORES_DESC: tuple[int, ...] = tuple(sorted(SCORES, reverse=True))           # (4..-4)
LABELS: dict[int, str] = dict(MoodEntry.Score.choices)

S_MIN, S_MAX = min(SCORES), max(SCORES)
# Used for symmetric charts around the zero line.
MAX_ABS: int = max(abs(S_MIN), abs(S_MAX))

# Allowed day windows for dropdowns (immutable).
HISTORY_DAYS_CHOICES: tuple[int, ...] = (7, 14, 30, 60, 90, 180, 365)
TEAM_AGG_DAYS_CHOICES: tuple[int, ...] = (1, 7, 14, 30, 60, 90, 180, 365)


# =============================================================================
# Utilities (pure functions)
# =============================================================================

def _parse_days(param: Optional[str], allowed: Sequence[int], default: int) -> int:
    """Safely parse ?days=N and validate against a whitelist.

    Args:
        param: Raw query string value (e.g., request.GET.get("days")).
        allowed: Allowed integer values.
        default: Fallback when parsing fails or value is not allowed.

    Returns:
        A safe integer from the whitelist.
    """
    try:
        d = int(param or "")
    except (TypeError, ValueError):
        return default
    return d if d in allowed else default


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp an integer to the closed interval [low, high]."""
    return max(low, min(high, value))


def _bucket_rounded(v: Optional[float]) -> Optional[int]:
    """Round a float to the nearest score bucket and clamp to score range.

    Args:
        v: The float value (e.g., average/median) or None.

    Returns:
        An integer bucket in [S_MIN..S_MAX] or None if input is None.
    """
    if v is None:
        return None
    return _clamp(int(round(v)), S_MIN, S_MAX)


@dataclass(frozen=True)
class Stats:
    """Aggregate statistics for a multiset of integer scores.

    Attributes:
        total: Total number of observations.
        average: Arithmetic mean or None if total==0.
        median: Median value or None if total==0.
        counter: Score -> count mapping (defensive copy).
    """
    total: int
    average: Optional[float]
    median: Optional[float]
    counter: Counter[int]


def _stats_from_counter(c: Counter[int]) -> Stats:
    """Compute total, average, median directly from a Counter without expansion.

    This avoids expanding the multiset (memory efficient for larger samples).

    Args:
        c: Counter mapping score -> frequency.

    Returns:
        Stats with total, average, median, and a defensive copy of the counter.
    """
    total = sum(c.values())
    if total == 0:
        return Stats(total=0, average=None, median=None, counter=c.copy())

    # Average
    avg = sum(s * n for s, n in c.items()) / float(total)

    # Median via cumulative counts (no expansion).
    keys_sorted = sorted(c.keys())
    mid1_idx = (total - 1) // 2
    mid2_idx = total // 2

    running = 0
    mid1_val: Optional[int] = None
    mid2_val: Optional[int] = None
    for k in keys_sorted:
        running += c[k]
        if mid1_val is None and running - 1 >= mid1_idx:
            mid1_val = k
        if mid2_val is None and running - 1 >= mid2_idx:
            mid2_val = k
            break

    med = None if (mid1_val is None or mid2_val is None) else (mid1_val + mid2_val) / 2.0
    return Stats(total=total, average=avg, median=med, counter=c.copy())


def _stats_from_scores(scores: Iterable[int]) -> Stats:
    """Thin wrapper: build a Counter and delegate to `_stats_from_counter`.

    Args:
        scores: Iterable of integer scores.

    Returns:
        Stats computed from the score frequencies.
    """
    return _stats_from_counter(Counter(scores))


# =============================================================================
# SVG chart builders (history + team distribution)
# =============================================================================

def _build_history_bar_chart(
    values_asc: Sequence[int],
    width: int = 720,
    height: int = 200,
    margin: int = 16,
) -> dict[str, Any]:
    """Build a symmetric vertical bar chart (around zero) for the history page.

    Args:
        values_asc: Scores ordered from oldest → newest (ascending by date).
        width: SVG width (px).
        height: SVG height (px).
        margin: Outer margin (px).

    Returns:
        Dict with keys: width, height, bars (list), grid (dict), count (int).
        Each bar has: x, y, w, h, cls ("pos" | "neg").
    """
    inner_h = height - 2 * margin
    zero_y = margin + inner_h / 2.0
    half_h = inner_h / 2.0

    n = len(values_asc)
    bars: list[dict[str, Any]] = []

    if n == 1:
        step = float(width - 2 * margin)
        bar_w = max(8.0, step * 0.5)
        x_center = margin + step / 2.0
        val = int(values_asc[0])
        h = (abs(val) / float(MAX_ABS) * half_h) if MAX_ABS else 0.0
        x = x_center - bar_w / 2.0
        y = (zero_y - h) if val >= 0 else zero_y
        bars.append({
            "x": round(x, 1), "y": round(y, 1),
            "w": round(bar_w, 1), "h": round(h, 1),
            "cls": "pos" if val >= 0 else "neg",
        })
    elif n > 1:
        step = float(width - 2 * margin) / float(n)
        bar_w = max(8.0, step * 0.7)
        for i, val in enumerate(values_asc):
            h = (abs(val) / float(MAX_ABS) * half_h) if MAX_ABS else 0.0
            x = margin + i * step + (step - bar_w) / 2.0
            y = (zero_y - h) if val >= 0 else zero_y
            bars.append({
                "x": round(x, 1), "y": round(y, 1),
                "w": round(bar_w, 1), "h": round(h, 1),
                "cls": "pos" if val >= 0 else "neg",
            })

    grid = {"top": margin, "zero": round(zero_y, 1), "bottom": round(height - margin, 1)}
    return {"width": width, "height": height, "bars": bars, "grid": grid, "count": n}


def _build_distribution_chart(
    counter: Counter[int],
    scores_axis: Optional[Sequence[int]] = None,
    width: int = 720,
    height: int = 220,
    margins: tuple[int, int, int, int] = (12, 12, 28, 12),
) -> dict[str, Any]:
    """Build SVG-ready data for the team distribution bar chart.

    Args:
        counter: Mapping score -> count for the selected time window.
        scores_axis: X-axis scores to render (defaults to SCORES_ASC).
        width: SVG viewport width (px).
        height: SVG viewport height (px).
        margins: (top, right, bottom, left) margins (px).

    Returns:
        Dict with `width`, `height`, margin `m`, list of `bars`
        (x, y, w, h, cx, score, count, fill), and precomputed axis positions.
    """
    if scores_axis is None:
        scores_axis = SCORES_ASC  # immutable tuple

    m_top, m_right, m_bottom, m_left = margins
    inner_w: float = float(width - m_left - m_right)
    inner_h: float = float(height - m_top - m_bottom)

    total = sum(counter.values())
    max_count: int = max(counter.values()) if total else 0

    step: float = inner_w / float(len(scores_axis)) if scores_axis else inner_w
    bar_w: float = max(10.0, step * 0.65)  # float to keep types consistent

    def css_var_for(score: int) -> str:
        if score == 0:
            return "var(--neutral)"
        if score > 0:
            return f"var(--pos-{score})"
        return f"var(--neg-{abs(score)})"

    bars: list[dict[str, Any]] = []
    for i, s in enumerate(scores_axis):
        cnt: int = int(counter.get(s, 0))
        h: float = (cnt / float(max_count) * inner_h) if max_count else 0.0
        x: float = m_left + i * step + (step - bar_w) / 2.0
        y: float = m_top + (inner_h - h)
        cx: float = x + bar_w / 2.0
        bars.append({
            "score": s,
            "count": cnt,
            "x": round(x, 1), "y": round(y, 1),
            "w": round(bar_w, 1), "h": round(h, 1),
            "cx": round(cx, 1),
            "fill": css_var_for(s),
        })

    axis_y: float = float(height - m_bottom)
    x_labels_y: float = float(height) - (m_bottom / 2.0)

    return {
        "width": width,
        "height": height,
        "m": {"t": m_top, "r": m_right, "b": m_bottom, "l": m_left},
        "bars": bars,
        "axis_y": round(axis_y, 1),
        "x_labels_y": round(x_labels_y, 1),
    }


# =============================================================================
# Views
# =============================================================================

@login_required
def dashboard_redirect(_request: HttpRequest) -> HttpResponse:
    """Redirect site root to the 'today' page."""
    return redirect("moods:today")


@login_required
def today_mood_view(request: HttpRequest) -> HttpResponse:
    """Create/update today's mood entry for the current user.

    GET:
        Do not auto-create an entry (absence → no record).
    POST:
        Create or update today's entry; then redirect to team overview.
    """
    today = timezone.localdate()
    entry = MoodEntry.objects.filter(user=request.user, date=today).first()

    if request.method == "POST":
        form = MoodEntryForm(request.POST, instance=entry)
        if form.is_valid():
            obj = form.save(commit=False)
            if entry is None:
                obj.user = request.user
                obj.date = today
            obj.save()
            messages.success(request, _("Danke! Dein heutiger Mood wurde gespeichert."))
            return redirect("moods:team")
    else:
        form = MoodEntryForm(instance=entry)

    return render(request, "moods/today.html", {"form": form, "today": today})


@login_required
def my_history_view(request: HttpRequest) -> HttpResponse:
    """Show personal history with a symmetric bar chart around zero.

    Query params:
        days: One of HISTORY_DAYS_CHOICES (default 30).

    Returns:
        Rendered 'moods/history.html' with chart + table context.
    """
    days = _parse_days(request.GET.get("days"), HISTORY_DAYS_CHOICES, default=30)

    today = timezone.localdate()
    date_from = today - timedelta(days=days - 1)

    # Latest first for the table; chart wants oldest→newest.
    entries_desc = list(
        MoodEntry.objects.filter(user=request.user, date__gte=date_from, date__lte=today)
        .order_by("-date", "-created_at")
    )
    values_asc = [e.score for e in reversed(entries_desc)]

    chart = _build_history_bar_chart(values_asc)

    context = {
        "entries": entries_desc,
        "today": today,
        "chart": chart,
        "days": days,
        "days_choices": HISTORY_DAYS_CHOICES,
        "entries_count": len(entries_desc),
    }
    return render(request, "moods/history.html", context)


@login_required
def team_overview_view(request: HttpRequest) -> HttpResponse:
    """Team overview.

    Modes:
        - Aggregated (default): distribution over N days (?days in TEAM_AGG_DAYS_CHOICES)
        - Weekly detail (?range=week): last 7 days with colored avg/median.
    """
    range_param = request.GET.get("range", "day")
    today: date = timezone.localdate()

    # -------------------- Weekly detail (last 7 days) --------------------
    if range_param == "week":
        days_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
        day_rows: list[dict[str, Any]] = []
        weekly_counter: Counter[int] = Counter()

        for d in days_list:
            scores = list(MoodEntry.objects.filter(date=d).values_list("score", flat=True))
            c_day = Counter(scores)
            st = _stats_from_counter(c_day)
            weekly_counter.update(c_day)

            day_rows.append({
                "date": d,
                "total": st.total,
                "avg": st.average, "avg_bucket": _bucket_rounded(st.average),
                "med": st.median,  "med_bucket": _bucket_rounded(st.median),
            })

        week_stats = _stats_from_counter(weekly_counter)

        context = {
            "range_param": "week",
            "day_rows": day_rows,
            "weekly_total": week_stats.total,
            "weekly_avg": week_stats.average,
            "weekly_avg_bucket": _bucket_rounded(week_stats.average),
            "weekly_med": week_stats.median,
            "weekly_med_bucket": _bucket_rounded(week_stats.median),
            "date_from": days_list[0],
            "date_to": days_list[-1],
        }
        return render(request, "moods/team_overview_week.html", context)

    # -------------------- Aggregated distribution over N days ------------
    days = _parse_days(request.GET.get("days"), TEAM_AGG_DAYS_CHOICES, default=30)
    date_from = today - timedelta(days=days - 1)

    scores = list(
        MoodEntry.objects.filter(date__gte=date_from, date__lte=today)
        .values_list("score", flat=True)
    )
    st = _stats_from_counter(Counter(scores))

    rows = [
        {
            "score": s,
            "label": LABELS[s],
            "count": st.counter.get(s, 0),
            "percent": ((st.counter.get(s, 0) * 100.0 / st.total) if st.total else 0.0),
        }
        for s in SCORES_DESC
    ]

    chart = _build_distribution_chart(st.counter)

    context = {
        "range_param": "day",
        "days": days,
        "days_choices": TEAM_AGG_DAYS_CHOICES,
        "count": st.total,
        "avg": st.average,
        "med": st.median,
        "rows": rows,
        "chart": chart,
        "date_from": date_from,
        "date_to": today,
    }
    return render(request, "moods/team_overview.html", context)
