from django.contrib import admin
from django.urls import include, path

from routing.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health-root"),
    path("health", health, name="health-root-noslash"),
    path("api/", include("routing.urls")),
]
