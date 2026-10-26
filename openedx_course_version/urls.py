"""URL routes mounted automatically at /api/course_version/ (see apps.py)."""

from django.urls import path

from .views import CourseVersionView

urlpatterns = [
    path("v1/<str:course_id>", CourseVersionView.as_view(), name="course-version-detail"),
]
