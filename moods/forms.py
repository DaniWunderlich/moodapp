from django import forms
from django.utils.translation import gettext_lazy as _
from .models import MoodEntry


class MoodEntryForm(forms.ModelForm):
    class Meta:
        model = MoodEntry
        fields = ["score", "note"]

        # i18n: Labels & Hilfetexte
        labels = {
            "score": _("Stimmung"),
            "note": _("Notiz"),
        }
        help_texts = {
            "note": _("Optional: kurzer Kontext"),
        }

        # Widgets
        widgets = {
            # RadioSelect – Choices kommen unten in __init__ nochmals aus dem Model
            "score": forms.RadioSelect(attrs={
                "class": "score-field",        # CSS-Hook (falls gebraucht)
                "aria-label": _("Stimmung"),   # a11y
            }),
            "note": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": _("Optional: kurzer Kommentar"),
                "maxlength": 280,              # soft-limit im UI
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Score ist Pflicht
        self.fields["score"].required = True

        # Single Source of Truth: Choices strikt aus dem Model
        self.fields["score"].choices = list(MoodEntry.Score.choices)

        # Keine leere Option bei RadioSelect (ist standardmäßig ohnehin nicht vorhanden),
        # aber falls mal ein anderer Widget-Typ gesetzt wird:
        if hasattr(self.fields["score"], "empty_values"):
            self.fields["score"].empty_values = []

        # Optional: Falls du das Feld im Template manuell renderst (Skala-Grid),
        # kannst du hier noch einen CSS-Hook setzen:
        self.fields["score"].widget.renderer = None  # Standard-Renderer (Django-Template)

    def clean_note(self):
        """Whitespace trimmen; sehr kurze Notizen zu leer machen."""
        note = (self.cleaned_data.get("note") or "").strip()
        return note if note else ""
