"""
REST API: GET /api/course_version/v1/<course_id>

Returns the version tag for one course run. Visible to:
* any authenticated user with course access (enrolled learner, staff, superuser), and
* anonymous users when the course allows anonymous access.

The Learning MFE badge and the legacy LMS snippet both consume this endpoint,
so learners and staff always see the same text (staff additionally get an
``is_staff`` flag so the UI can show an "Edit in Studio" link).
"""

from django.conf import settings
from django.http import JsonResponse
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import permissions, views

from .utils import version_payload


def _read_fields(course_key):
    """Read mixin fields from the modulestore; missing fields -> blanks."""
    from xmodule.modulestore.django import modulestore

    course_block = modulestore().get_course(course_key)
    if course_block is None:
        return None
    return {
        # `course_version_label` (not `course_version`): the latter collides with
        # Split Mongo's internal `block.course_version` version_guid (ObjectId).
        # Fall back to legacy `course_version` string field for courses saved
        # with plugin v1.0.0 before the rename (ignore ObjectId values).
        "version": _clean_version(getattr(course_block, "course_version_label", "") or getattr(course_block, "course_version", "") or ""),
        "version_of": getattr(course_block, "course_version_of", "") or "",
        "show_tag": getattr(course_block, "course_version_show_tag", True),
    }


def _clean_version(value):
    """Accept only real version strings; ignore internal ObjectId/version_guid."""
    if isinstance(value, str):
        return value
    return ""


def _can_see_course(user, course_key):
    """Same rule as course_home_api: enrolled, staff, or global staff."""
    try:
        from common.djangoapps.student.roles import CourseStaffRole
        from openedx.core.djangoapps.courseware_api.utils import get_course_by_id
    except Exception:  # pragma: no cover - edx not installed
        return True
    if getattr(user, "is_staff", False):
        return True
    try:
        course = get_course_by_id(course_key)
    except Exception:
        return False
    if course is None:
        return False
    if CourseStaffRole(course_key).has_user(user):
        return True
    try:
        from openedx.core.lib.courses import has_course_author_access  # noqa
    except Exception:
        pass
    # Enrolled learners
    try:
        from common.djangoapps.student.models import CourseEnrollment

        if CourseEnrollment.is_enrolled(user, course_key):
            return True
    except Exception:
        pass
    # Fall back to the platform's anonymous-access check
    try:
        from openedx.features.course_experience import COURSE_ENABLE_UNENROLLED_ACCESS_FLAG

        if COURSE_ENABLE_UNENROLLED_ACCESS_FLAG.is_enabled(course_key):
            return True
    except Exception:
        pass
    return False


class CourseVersionView(views.APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, course_id):
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            return JsonResponse({"detail": "Invalid course id."}, status=400)
        if request.user.is_anonymous and not getattr(settings, "FEATURES", {}).get(
            "ALLOW_PUBLIC_COURSE_VERSION", True
        ):
            return JsonResponse({"detail": "Authentication required."}, status=401)
        if not request.user.is_anonymous and not _can_see_course(request.user, course_key):
            return JsonResponse({"detail": "Not found."}, status=404)
        fields = _read_fields(course_key)
        if fields is None:
            return JsonResponse({"detail": "Course not found."}, status=404)
        payload = version_payload(
            course_id=str(course_key),
            version=fields["version"],
            version_of=fields["version_of"],
            show_tag=fields["show_tag"],
        )
        try:
            from common.djangoapps.student.roles import CourseStaffRole

            payload["is_staff"] = bool(
                request.user.is_staff or CourseStaffRole(course_key).has_user(request.user)
            )
        except Exception:  # pragma: no cover
            payload["is_staff"] = bool(getattr(request.user, "is_staff", False))
        return JsonResponse(payload)
