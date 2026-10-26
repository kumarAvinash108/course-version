"""Django app config: auto-registers REST URLs via edx_django_utils plugins."""

from django.apps import AppConfig

try:
    from edx_django_utils.plugins import PluginURLs

    from openedx.core.djangoapps.plugins.constants import ProjectType

    _PLUGIN_URLS = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: "course_version",
                PluginURLs.REGEX: r"^api/course_version/",
                PluginURLs.RELATIVE_PATH: "urls",
            },
        }
    }
except Exception:  # pragma: no cover - edx not installed (host-side)
    _PLUGIN_URLS = {}


class CourseVersionConfig(AppConfig):
    name = "openedx_course_version"
    verbose_name = "Course Version"
    default_auto_field = "django.db.models.BigAutoField"

    # Auto-mounts urlpatterns from openedx_course_version/urls.py at
    # /api/course_version/ in LMS (and CMS if enabled) -- no urls.py fork needed.
    # NOTE: must be a class attribute (not set in ready()) so that
    # edx_django_utils discovers it during URL loading.
    plugin_app = _PLUGIN_URLS

    def ready(self):
        # Keep instance attr in sync for any code reading it off the instance.
        self.plugin_app = self.__class__.plugin_app
