from django.urls import path
from . import views

app_name = "moods"

urlpatterns = [
    path("", views.dashboard_redirect, name="dashboard"),
    path("today/", views.today_mood_view, name="today"),
    path("history/", views.my_history_view, name="history"),
    path("team/", views.team_overview_view, name="team"),
]
