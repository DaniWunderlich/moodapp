from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

def health(_request):
    return HttpResponse("ok")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", health, name="health"),
    path("accounts/", include("django.contrib.auth.urls")),  # Login/Logout
    path("i18n/", include("django.conf.urls.i18n")),         # <— für set_language
    path("", include("moods.urls")),
]
