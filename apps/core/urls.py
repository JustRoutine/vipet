from django.urls import path

from apps.core.views import AboutPageView, HomePageView

app_name = "core"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("about/", AboutPageView.as_view(), name="about"),
]
