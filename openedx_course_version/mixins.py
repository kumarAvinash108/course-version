"""
Course version XBlock mixin.

These fields are injected into the CourseBlock via the ``XBLOCK_MIXINS``
Django setting (see tutor plugin patches). Because
``CourseMetadata.fetch_all`` iterates over *every* ``Scope.settings`` field
on the course block, each field below automatically appears in:

* Studio legacy Advanced Settings page, and
* Course Authoring MFE Advanced Settings page (``/api/contentstore/v0/advanced_settings``)

No fork of edx-platform is required.

Fields
------
* ``course_version_label`` — the version label of THIS course run
  (e.g. ``v2.0``, ``2026``, ``Fall-2026``). Named *_label (not *course_version*)
  because Split Mongo already uses ``block.course_version`` for its internal
  version_guid (ObjectId).
* ``course_version_of`` — WHICH course this is a version of
  (e.g. ``CS101 - Intro to Python`` or a course key). Leave blank when this
  course is the original.
* ``course_version_show_tag`` — toggle for the learner/staff pill badge.
"""

_ = lambda text: text  # scraped for i18n; real translation happens via field help


try:
    from xblock.fields import Boolean, Scope, String

    class CourseVersionMixin:
        """
        Mixin added to CourseBlock through ``XBLOCK_MIXINS``.

        Keep field names stable: they are persisted in the modulestore and
        served by the ``/api/course_version/v1`` REST endpoint.
        """

        # NOTE: Do NOT name a field `course_version` — Split Mongo already uses
        # `block.course_version` internally for its version_guid (ObjectId).
        # Using that name shadows it and corrupts course loading
        # (FailingEnforceTypeWarning). Hence `course_version_label`.
        course_version_label = String(
            display_name=_("Course Version"),
            help=_(
                "Which version is this course? Examples: v1.0, v2.0, 2026, Fall-2026. "
                "This text is shown to learners and staff as a pill badge on the course home "
                "and courseware pages (for example: 'Version v2.0'). Leave blank to hide the badge."
            ),
            default="",
            scope=Scope.settings,
        )

        course_version_of = String(
            display_name=_("Version Of (Parent Course)"),
            help=_(
                "Which course is this a version of? Examples: 'CS101 - Intro to Python', "
                "'course-v1:Org+CS101+2024', or 'Original 2024 edition'. "
                "Shown together with the version, for example: 'CS101 - Intro to Python • Version v2.0'. "
                "Leave blank if this course is the original (not a revision)."
            ),
            default="",
            scope=Scope.settings,
        )

        course_version_show_tag = Boolean(
            display_name=_("Show Version Tag to Learners"),
            help=_(
                "Enter true or false. If true (default), learners and course staff see a small "
                "'version' pill badge on the course home and courseware pages. "
                "Set to false to keep the version info in Studio only."
            ),
            scope=Scope.settings,
            default=True,
        )

except ImportError:  # pragma: no cover - allows importing package without xblock installed
    class CourseVersionMixin:  # type: ignore
        """Fallback stub when xblock is not installed (docs/tests)."""
