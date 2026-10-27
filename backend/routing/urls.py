from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("geocode/", views.geocode_view, name="geocode"),
    path("plan/", views.plan_view, name="plan"),
]
