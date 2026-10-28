from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("health", views.health, name="health-noslash"),
    path("geocode/", views.geocode_view, name="geocode"),
    path("geocode", views.geocode_view, name="geocode-noslash"),
    path("plan/", views.plan_view, name="plan"),
    path("plan", views.plan_view, name="plan-noslash"),
]
