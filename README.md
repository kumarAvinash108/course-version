# course-version

**Course Version plugin for Open edX (Tutor ≥ 19 / Ulmo).**

Staff set *which version of which course* once in **Studio → Advanced Settings**;
learners and staff then see a responsive, Indigo-styled **pill tag** on:

* the **course list** (Learner Dashboard cards), and
* the **course home** + **courseware** pages (Learning MFE).

No edx-platform fork required. Works for both the **legacy CMS** and the
**Course Authoring MFE**.

---

## The badge

A solid navy pill (Indigo theme) with white text:

| Property | Value |
|---|---|
| `background-color` | `#0a3055` |
| `border-color` | `#0a3055` |
| `color` | `#fff` |

**Responsive & accessible:**

* Fluid sizing with CSS `clamp()` for font-size, padding, margin, gap and
  border-radius — shrinks gracefully from desktop to mobile.
* `max-width:100%` + `box-sizing:border-box` → never overflows its container.
* `flex-wrap:wrap` → content wraps to a second line instead of clipping.
* The **version segment never shrinks** (`flex-shrink:0; white-space:nowrap`),
  so **the version is always fully visible**.

**Long names truncate, version always shows:**

* The course name is cut to **34 characters + `...`** (trimmed to a word
  boundary), and also ellipsizes via CSS when the container is tight.
* The version part is appended after a `•` and is **never** truncated.
* Hovering the pill shows the **full, untruncated** label.

```
▣ Introduction to Very Long Course Na… • Version v2.0
```

Staff also get a white **Edit in Studio** link that deep-links into the course.

---

## What the user sees

### 1. Studio → Advanced Settings

Three new settings appear automatically (they are real `CourseBlock`
`Scope.settings` fields, so both the legacy CMS page and the Course Authoring
MFE list them):

| Field | Type | Example | Help shown in Studio |
|---|---|---|---|
| **Course Version** | String | `v2.0` | *Which version is this course? … Leave blank to hide.* |
| **Version Of (Parent Course)** | String | `CS101 - Intro to Python` | *Which course is this a version of? … Leave blank if original.* |
| **Show Version Tag to Learners** | Boolean | `true` | *If true (default), learners and staff see the badge.* |

All three are **optional** (String fields default to `""`, the Boolean to
`true`). The Course Authoring MFE additionally gets a **helper card** with a
live pill preview and a soft highlight around the three rows
(see `frontend/authoring/`).

### 2. API

Data comes from `GET /api/course_version/v1/<course_id>`:

```json
{
  "course_id": "course-v1:Org+CS101+2026",
  "version": "v2.0",
  "version_of": "CS101 - Intro to Python",
  "show_tag": true,
  "display": true,
  "tag_label": "CS101 - Intro to Python • Version v2.0",
  "is_staff": false
}
```

`display` is `true` only when the tag is enabled **and** at least one text
field is set — so an empty course simply shows no pill.

---

## Where the tag appears

| Location | MFE | How it renders |
|---|---|---|
| **Course list** (dashboard cards) | `learner-dashboard` | Scans every `[data-testid="CourseCard"]`, reads the course id from the title link, fetches the API **once per course (cached)** and appends the pill under the title. |
| **Course home** + **courseware** | `learning` | One API call for the current course; the pill is prepended to the page/courseware header. |

Legacy LMS pages can reuse the markup via
`openedx_course_version/templates/openedx_course_version/tag.html` +
`static/openedx_course_version/css/tag.css`.

---

## Install

From a local checkout (recommended):

```bash
pip install -e /path/to/course-version
tutor plugins enable course-version
tutor mounts add /path/to/course-version
tutor images build openedx mfe
tutor local launch
```

Then:

1. Open Studio → your course → **Advanced Settings**.
2. Fill **Course Version** (e.g. `v2.0`) and **Version Of** (e.g. `CS101`).
3. Save. Open the course list and the course as a learner/staff — the pill
   appears on the dashboard cards and the course pages.

> **Remember to rebuild the images after changing the plugin**, then restart:
> `tutor images build openedx mfe && tutor local reboot`. The badge lives in
> the **mfe** image and the Django app in the **openedx** image.

### How the app gets into the openedx image

The plugin declares the repository in the `MOUNTED_DIRECTORIES` filter, so
`tutor mounts add` bind-mounts it into the openedx build *and* into every
openedx service at run time (cms, lms, workers and the `cms-job`/`lms-job`
containers used by `tutor local launch`). Tutor runs
`pip install -e /mnt/tutor-contrib-course-version` while building the image.

This is required because job containers are recreated from the image on every
launch: an app that is only `pip install`ed inside a running container (or one
that is missing because the image was never rebuilt) makes
`cms reindex_studio` / `cms reindex_course` fail with
`ModuleNotFoundError: No module named 'openedx_course_version'`.

Note that `pyproject.toml` deliberately declares **no** dependencies: the same
distribution is installed into the openedx venv, and `tutor`/`tutor-mfe` would
drag `kubernetes` and `mypy` into it.

---

## How it works (files)

* `tutorcourseversion/plugin.py` — the Tutor plugin: config defaults,
  `XBLOCK_MIXINS` registration, `MOUNTED_DIRECTORIES`, and the MFE Dockerfile
  patches that inject the two badge scripts + styles.
* `openedx_course_version/mixins.py` — `CourseVersionMixin` (the 3 XBlock
  fields).
* `openedx_course_version/views.py` + `urls.py` + `apps.py` — REST endpoint
  auto-mounted at `/api/course_version/` through `edx_django_utils` plugin URLs.
* `openedx_course_version/utils.py` — pure `build_tag_label()` /
  `should_display_tag()` / `version_payload()` (unit-tested).
* `frontend/learning/CourseVersionTag.js` — badge source injected into
  `frontend-app-learning` at image build time (also imported from `index.jsx`).
* `frontend/authoring/studio-version-helper.{js,css}` — helper card +
  highlight injected into `frontend-app-course-authoring`.
* *(inline in the plugin)* — the **learner-dashboard** badge
  (`CourseVersionDashboardTag.js`) is written + imported by the
  `mfe-dockerfile-pre-npm-build-learner-dashboard` patch.
* `tests/test_version_label.py` — `pytest tests/` (no edx needed).

### Cross-origin note

The MFEs (`apps.local.openedx.io`) and the LMS (`local.openedx.io`) are
different origins, so the badges call the **absolute** LMS base URL
(`getConfig().LMS_BASE_URL`) with `credentials: 'include'`. The platform's CORS
config already allows the MFE origin (with credentials), so the request
authenticates correctly. A relative `/api/...` path would hit the MFE's own
server instead of the LMS.

---

## Verify

```bash
pytest tests/ -q
python3 -c "import ast; ast.parse(open('tutorcourseversion/plugin.py').read())"
node --check frontend/learning/CourseVersionTag.js
node --check frontend/authoring/studio-version-helper.js
tutor plugins enable course-version && tutor config save
```

---

## Notes / limits

* Changing a version is just editing Advanced Settings and saving — the
  modulestore version history is untouched; this plugin **labels**, not branches.
* To hide the badge for one course, clear both text fields or set
  **Show Version Tag to Learners** to `false`.
* The field is named `course_version_label` (not `course_version`) because
  Split Mongo already reserves `block.course_version` for its internal
  `version_guid`.
* Rebuild the **mfe** image whenever you change badge styling/behaviour;
  rebuild the **openedx** image whenever you change the Django app/mixin.

## License

AGPL-3.0 (see `pyproject.toml`).
