from django.contrib import admin

# WICHTIG:
# - Wir registrieren MoodEntry NICHT, damit Einzelwerte nicht über /admin sichtbar sind.
# - Das eingebaute User-Admin (django.contrib.auth) bleibt voll nutzbar:
#   Benutzer anlegen, löschen, Passwörter setzen etc.

admin.site.site_header = "MoodApp Admin"
admin.site.site_title = "MoodApp Admin"
admin.site.index_title = "Administration"
