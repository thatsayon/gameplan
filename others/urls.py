from django.urls import path
from .views import HelpandSupportView

urlpatterns = [
    path("helpandsupport/", HelpandSupportView.as_view()),
]