# course-version

**Course Version plugin for Open edX (Tutor ≥ 19 / Ulmo).**

Staff set *which version of which course* once in **Studio → Advanced Settings**;
learners and staff then see it on:

* the **course list** (Learner Dashboard cards) — navy pill,
* the **course home** (Learning MFE) — a normal row inside the **Course Tools**
  sidebar list,
* the **courseware** page (Learning MFE) — navy pill in the header,
* **Studio** — pill above Advanced Settings + a pill on every course card of
  the course list.

No edx-platform fork required. Works for both the **legacy CMS** and the
**Course Authoring MFE**.

---

## The badge

One navy pill everywhere (dashboard course cards, course home, Studio
advanced settings) showing **only the course name and version**:

```
Course Name • Version v2.0
```

| Property | Value |
|---|---|
| `background-color` | `#0a3055` |
| `border-color` | `#0a3055` |
| `color` | `#fff` |
| `border-radius` | `999px` (pill) |

**Responsive & accessible:**

* Fluid sizing with CSS `clamp()` for font-size, padding, margin, gap —
  shrinks gracefully from desktop to mobile.
* `max-width:100%` + `box-sizing:border-box` → never overflows its container.
* `flex-wrap:wrap` → content wraps to a second line instead of clipping.
* The **version segment never shrinks** (`white-space:nowrap`), so **the
  version is always fully visible**.
* Hovering the pill shows the **full, untruncated** label.

**Long names truncate, version always shows:**

* The course name is cut to **34 characters + `...`** (trimmed to a word
  boundary), and also ellipsizes via CSS when the container is tight.
* The version part is appended after a `•` and is **never** truncated.

```
Introduction to Very Long Course Na… • Version v2.0
```

The same pill + markup + CSS is used on every surface — no staff-only
extras, no icons; just the name and the version.

### Course home: a Course Tools row (not a pill)

On the course home the tag is **not** a pill: it is rendered as a regular
`<li class="small">` inside the **Course Tools** sidebar list, right above
*Launch tour*, so it matches the *Bookmarks* / *Updates* rows exactly:

| Piece | Value |
|---|---|
| Markup | `<li class="small course-version-item">` inside the existing `<ul class="list-unstyled">` |
| Icon | tag glyph with `svg-inline--fa fa-tag fa-fw mr-2` (same spacing as the other rows) |
| Text | `Course Name • Version v2.0`, name truncated to 34 chars, version never truncated |
| Colour | `var(--link-color, #006daa)` — the same link colour as the other rows |
| Tooltip | full, untruncated label (`title`) |

Placement is idempotent and self-healing: the row is inserted before
`#courseHome-launchTourLink`, and a `MutationObserver` re-inserts it (from the
cached API payload — no extra request) if React re-renders the sidebar.

Fallbacks, in order:

1. Sidebar exists but the **Course Tools** list does not (no tools configured)
   → its own `<section class="mb-4"><h2 class="h4">Course Version</h2>…`,
   i.e. the same markup as the neighbouring sidebar children.
2. No sidebar at all (courseware, child course) → the navy pill prepended to
   the header, as on every other page.

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
`true`). In **Studio → Advanced Settings** the same navy **tag pill** shown to
learners is displayed at the top of the page, and the three rows get a soft
highlight (see `frontend/authoring/`).

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

| Location | MFE / surface | How it renders |
|---|---|---|
| **Course list** (dashboard cards) | `learner-dashboard` | Scans every `[data-testid="CourseCard"]`, reads the course id from the title link, fetches the API **once per course (cached)** and appends the same navy pill under the title. |
| **Course home** | `learning` | One API call for the current course; the tag is inserted as an `<li class="small">` row in the **Course Tools** sidebar list (re-inserted from cache if React re-renders). |
| **Courseware** (and any page without that sidebar) | `learning` | Same call; the navy pill is prepended to the courseware/page header. |
| **Course list** (legacy CMS) | `cms` | `studio_list.js` (injected into `cms/templates/base.html`) scans `.course-item[data-course-key]`, fetches the **same-origin** API once per course and inserts the pill under each course title. |
| **Studio → Advanced Settings** | `authoring` | The same pill (live data for the course in the URL) sits above the settings list; the three version fields get a soft highlight. |

The API is mounted on **both** project types (`LMS` and `CMS`), so the Studio
course list can call `/api/course_version/v1/…` same-origin — no CORS needed.

Legacy LMS pages can reuse the markup via
`openedx_course_version/templates/openedx_course_version/tag.html` +
`static/openedx_course_version/css/tag.css` (same style).

### Which URL shows it

The Learning MFE is served under `/learning`; this plugin adds an
`mfe-caddyfile` redirect so the old path never returns a blank page:

| URL | Result |
|---|---|
| `apps.<LMS_HOST>/learning/course/<course_id>` | Course home (Learning MFE) — **the Course Tools row** |
| `apps.<LMS_HOST>/course/<course_id>` | `301` → the URL above |
| `apps.<LMS_HOST>/course` | `301` → `http://<LMS_HOST>/dashboard` (the MFE has no route without a course id) |
| `LMS_HOST/courses/<course_id>/` | Legacy **LMS** course home — the MFE, and therefore this row, is *not* used there |

Example on a default Tutor install:

```bash
curl -sI http://apps.local.openedx.io/course/course-v1:OpenedX+DemoX+DemoCourse
# HTTP/1.1 301 Moved Permanently
# Location: /learning/course/course-v1:OpenedX+DemoX+DemoCourse
```

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
  `XBLOCK_MIXINS` registration, `MOUNTED_DIRECTORIES`, and the patches that
  inject the badge scripts + styles into the MFEs, add
  `studio_list.js` to `cms/templates/base.html`, and add the
  `mfe-caddyfile` `/course/<id>` → `/learning/course/<id>` redirect.
* `openedx_course_version/mixins.py` — `CourseVersionMixin` (the 3 XBlock
  fields).
* `openedx_course_version/views.py` + `urls.py` + `apps.py` — REST endpoint
  auto-mounted at `/api/course_version/` through `edx_django_utils` plugin URLs
  (**both** on `LMS` and on `CMS`, so Studio can fetch same-origin).
* `openedx_course_version/utils.py` — pure `build_tag_label()` /
  `should_display_tag()` / `version_payload()` (unit-tested).
* `frontend/learning/CourseVersionTag.js` — the Learning MFE script (Course
  Tools row + header-pill fallback) injected into `frontend-app-learning` at
  image build time (also imported from `index.jsx`).
* `frontend/authoring/studio-version-helper.{js,css}` — the version tag pill +
  field highlight injected into `frontend-app-course-authoring` (Studio →
  Advanced Settings).
* `openedx_course_version/static/openedx_course_version/js/studio_list.js` —
  pill for the legacy CMS course list (loaded from `cms/templates/base.html`).
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

After a rebuild (note the order — `tutor config save` **first**, see
*Notes / limits*):

```bash
tutor config save && tutor images build mfe
tutor local dc up -d --force-recreate mfe

# routing: /course/<id> must redirect into the MFE
curl -sI http://apps.local.openedx.io/course/course-v1:OpenedX+DemoX+DemoCourse
#   HTTP/1.1 301 ... Location: /learning/course/course-v1:OpenedX%2BDemoX%2BDemoCourse

# the bundle must contain the sidebar row
curl -s http://apps.local.openedx.io/learning/ | grep -o 'app\.[a-f0-9]*\.js'
docker exec tutor_local-mfe-1 sh -c 'grep -c course-version-item /openedx/dist/learning/app.*.js'

# the API must say display:true
curl -s http://local.openedx.io/api/course_version/v1/course-v1:OpenedX%2BDemoX%2BDemoCourse
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
* Always run `tutor config save` **before** `tutor images build`: the plugin
  patches are rendered into `env/plugins/mfe/build/mfe/Dockerfile` (and into
  the MFE `Caddyfile`) by `config save`. Skip it and the build reuses the
  previous Dockerfile — every patch layer comes back `CACHED` and the old code
  keeps running.
* The MFE `Caddyfile` is bind-mounted
  (`env/plugins/mfe/apps/mfe/Caddyfile:ro`), so a **routing-only** change
  needs `tutor config save` + `tutor local dc up -d --force-recreate mfe`,
  not an image rebuild.
* `apps.<LMS_HOST>/course` with no course id cannot render anything (the MFE
  routes are `/course/:courseId/…`), so the plugin redirects it to the LMS
  dashboard instead of serving an empty page.

## License

AGPL-3.0 (see `pyproject.toml`).
