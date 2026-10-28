"""
Tutor plugin: course-version
============================

What it does
------------
1. Installs the ``openedx_course_version`` Django app inside the openedx
   image and registers three new course fields via ``XBLOCK_MIXINS``:

   * ``course_version_label`` (e.g. ``v2.0``) — *which version*
     (named *_label because Split Mongo reserves ``block.course_version``
     for its internal version_guid ObjectId)
   * ``course_version_of`` (e.g. ``CS101 - Intro to Python``) — *of which course*
   * ``course_version_show_tag`` (bool, default True) — show/hide the badge

   Because ``CourseMetadata.fetch_all`` lists every ``Scope.settings`` field,
   these appear automatically in **Studio → Advanced Settings** (legacy CMS
   and the Course Authoring MFE) with friendly names, examples and help text.

2. Exposes ``GET /api/course_version/v1/<course_id>`` (via edx plugin URLs)
   so frontends can render the tag without forking edx-platform.

3. Injects the version tag into the **Learning MFE**:

   * **course home** — a normal row inside the *Course Tools* sidebar list
     (same markup/icon spacing as Bookmarks, Updates, Launch tour),
   * **courseware / pages without that sidebar** — the navy
     **name • Version X** pill in the header,

   plus the same navy pill on the **learner-dashboard** course cards and on
   the **Course Authoring MFE** Advanced Settings page.

   One shared style; the tag shows only the course name and version —
   nothing else. No MFE fork needed.

Enable with::

    pip install tutor-contrib-course-version
    tutor plugins enable course-version
    tutor images build openedx mfe
    tutor local launch
"""

from __future__ import annotations

from tutor import hooks

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("COURSE_VERSION_SHOW_TAG_DEFAULT", True),
        ("COURSE_VERSION_MFE_BADGE_ENABLED", True),
        ("COURSE_VERSION_STUDIO_HELPER_ENABLED", True),
    ]
)

# ---------------------------------------------------------------------------
# openedx image: install the Django app + register the XBlock mixin
# ---------------------------------------------------------------------------

# The `openedx_course_version` Django app must be importable by *every* container
# that runs manage.py (cms, lms, cms-worker, cms-job, ...). Installing it at image
# build time with `pip install tutor-contrib-course-version` does not work: the
# package is not necessarily on PyPI, and job containers are recreated from the
# image on every `tutor local launch`, so a runtime `pip install` would be lost.
#
# Instead, declare this repository as a mounted Python directory. Tutor then
# bind-mounts it into the openedx build (mnt-<name> stage) and into the openedx
# services at run time, and runs `pip install -e /mnt/<name>` in the image:
#
#     tutor mounts add /path/to/tutor-contrib-course-version
#     tutor images build openedx
hooks.Filters.MOUNTED_DIRECTORIES.add_item(
    ("openedx", "tutor-contrib-course-version")
)

hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-common-settings",
        """
# --- tutor-contrib-course-version ---
# INSTALLED_APPS is populated automatically via the lms.djangoapp/cms.djangoapp
# entry points (see pyproject.toml). Do NOT append here or Django will raise
# "Application labels aren't unique, duplicates: openedx_course_version".
XBLOCK_MIXINS += ("openedx_course_version.mixins.CourseVersionMixin",)
""",
    )
)

# ---------------------------------------------------------------------------
# Studio (legacy CMS) course list: include the same pill on every course
# card. The listing is React (`li.course-item[data-course-key]`); we load a
# small static script from our Django app that fetches the version per course
# and inserts the shared navy pill under the course title.
# ---------------------------------------------------------------------------

STUDIO_LIST_SCRIPT = r"""
# --- tutor-contrib-course-version: studio course-list pill ---
RUN grep -q "openedx_course_version/js/studio_list.js" cms/templates/base.html \
  || sed -i 's|</body>|<script src="/static/openedx_course_version/js/studio_list.js" defer="defer"></script>\n  </body>|' cms/templates/base.html
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("openedx-dockerfile-post-git-checkout", STUDIO_LIST_SCRIPT)
)

# ---------------------------------------------------------------------------
# One shared pill style used by every surface (dashboard cards, learning
# header, studio advanced settings, legacy LMS include). Navy pill, white
# text, name • Version X — nothing else.
# ---------------------------------------------------------------------------

PILL_CSS = (
    ".course-version-tag{"
    "display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;"
    "gap:clamp(.35rem,1.4vw,.55rem);"
    "margin:clamp(.4rem,1.5vw,.65rem) 0;"
    "padding:clamp(.4rem,1.5vw,.55rem) clamp(.75rem,2.2vw,1rem);"
    "border-radius:999px;box-sizing:border-box;max-width:100%;"
    "font-family:Inter,system-ui,-apple-system,sans-serif;"
    "font-size:clamp(.8rem,1.3vw,.92rem);font-weight:600;line-height:1.35;"
    "color:#fff;background:#0a3055;border:1px solid #0a3055;"
    "box-shadow:0 2px 5px rgba(10,48,85,.28);vertical-align:middle;"
    "}"
    ".course-version-tag__name{"
    "flex:0 1 auto;min-width:4em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
    "}"
    ".course-version-tag__sep{flex:0 0 auto;opacity:.65;}"
    ".course-version-tag__version{flex:0 0 auto;white-space:nowrap;font-weight:700;}"
)

# Shared badge builder (name + version only — no icon, no staff extras).
# Injected as a prelude in each MFE patch so every surface renders identically.
PILL_BUILDER_JS = r"""
var CV_NAME_LIMIT = 34;
function cvTruncateName(s, limit) {
  s = String(s || '').trim();
  if (s.length <= limit) return s;
  var cut = s.slice(0, limit);
  var sp = cut.lastIndexOf(' ');
  if (sp > limit * 0.55) cut = cut.slice(0, sp);
  return cut.replace(/\s+$/, '') + '...';
}
function cvFullName(name, version) {
  if (name && version) return name + ' \u2022 Version ' + version;
  if (version) return 'Version ' + version;
  return name;
}
function cvBadgeEl(payload) {
  var name = String(payload.version_of || '').trim();
  var version = String(payload.version || '').trim();
  var el = document.createElement('div');
  el.setAttribute('data-course-version-tag', 'true');
  el.className = 'course-version-tag';
  el.setAttribute('role', 'status');
  el.title = cvFullName(name, version);
  if (name) {
    var n = document.createElement('span');
    n.className = 'course-version-tag__name';
    n.textContent = cvTruncateName(name, CV_NAME_LIMIT);
    el.appendChild(n);
  }
  if (name && version) {
    var sep = document.createElement('span');
    sep.className = 'course-version-tag__sep';
    sep.textContent = '\u2022';
    el.appendChild(sep);
  }
  if (version) {
    var v = document.createElement('span');
    v.className = 'course-version-tag__version';
    v.textContent = 'Version ' + version;
    el.appendChild(v);
  }
  return el;
}
"""

# ---------------------------------------------------------------------------
# Learning MFE: version tag as a Course Tools row in the course-home sidebar
# (pill fallback on courseware / pages without the sidebar).
# ---------------------------------------------------------------------------

LEARNING_BADGE_JS = r"""
# --- tutor-contrib-course-version: learning badge ---
RUN mkdir -p /openedx/app/src/course-version && cat > /openedx/app/src/course-version/CourseVersionTag.js <<'COURSE_VERSION_EOF'
// Course version tag (Learning MFE).
// Course home: <li class="small"> row inside the Course Tools sidebar list —
// same markup + icon spacing as Bookmarks / Updates / Launch tour.
// Every other page (courseware header, pages without the sidebar): the navy
// "course name • Version X" pill.
import { getConfig, subscribe, APP_READY } from '@edx/frontend-platform';
""" + PILL_BUILDER_JS + r"""
var CV_TAG_PATH = 'M0 252.118V48C0 21.49 21.49 0 48 0h204.118a48 48 0 0 1 33.941 14.059l211.882 211.882c18.745 18.745 18.745 49.137 0 67.882L293.823 497.941c-18.745 18.745-49.137 18.745-67.882 0L14.059 286.059A48 48 0 0 1 0 252.118zM112 64c-26.51 0-48 21.49-48 48s21.49 48 48 48 48-21.49 48-48-21.49-48-48-48z';
function cvIconEl() {
  var NS = 'http://www.w3.org/2000/svg';
  var svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'svg-inline--fa fa-tag fa-fw mr-2');
  svg.setAttribute('data-prefix', 'fas');
  svg.setAttribute('data-icon', 'tag');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.setAttribute('role', 'img');
  svg.setAttribute('viewBox', '0 0 512 512');
  var path = document.createElementNS(NS, 'path');
  path.setAttribute('fill', 'currentColor');
  path.setAttribute('d', CV_TAG_PATH);
  svg.appendChild(path);
  return svg;
}
function cvDisplayText(payload) {
  return cvFullName(cvTruncateName(payload.version_of, CV_NAME_LIMIT), String(payload.version || '').trim());
}
function cvItemEl(payload) {
  var li = document.createElement('li');
  li.className = 'small course-version-item';
  li.setAttribute('data-course-version-tag', 'true');
  li.title = cvFullName(String(payload.version_of || '').trim(), String(payload.version || '').trim());
  li.appendChild(cvIconEl());
  var label = document.createElement('span');
  label.className = 'course-version-item__label';
  label.textContent = cvDisplayText(payload);
  li.appendChild(label);
  return li;
}
function cvLmsBase() {
  try { return (getConfig() && getConfig().LMS_BASE_URL) || ''; } catch (e) { return ''; }
}
function cvApi(courseId) {
  return String(cvLmsBase()).replace(/\/$/, '') + '/api/course_version/v1/' + encodeURIComponent(courseId);
}
function cvCourseIdFromUrl() {
  var m = window.location.pathname.match(/\/course\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}
function cvEnsure(payload) {
  if (!payload || !payload.display) return;
  var node = document.querySelector('[data-course-version-tag]');
  var sidebar = document.querySelector('.course-outline-tab .col-md-4');

  if (!sidebar) {
    if (node && node.classList.contains('course-version-tag')) return;
    if (node) node.remove();
    var anchor = document.querySelector('.course-home-outline .page-header, .courseware-header, header.course-header, main');
    var pill = cvBadgeEl(payload);
    if (anchor && anchor.prepend) { anchor.prepend(pill); } else { document.body.prepend(pill); }
    return;
  }

  if (node && node.classList.contains('course-version-tag')) { node.remove(); node = null; }
  if (node && (node.tagName !== 'LI' || !node.classList.contains('course-version-item'))) { node.remove(); node = null; }
  var item = node || cvItemEl(payload);

  var tour = sidebar.querySelector('#courseHome-launchTourLink');
  var list = tour && tour.parentNode;
  if (list && list.tagName === 'UL') {
    var helper = sidebar.querySelector('[data-course-version-section]');
    if (helper) helper.remove();
    if (item.parentNode !== list || item.nextElementSibling !== tour) list.insertBefore(item, tour);
    return;
  }

  // No Course Tools list: own section, same markup as the other sidebar children.
  var section = sidebar.querySelector('[data-course-version-section]');
  if (!section) {
    section = document.createElement('section');
    section.className = 'mb-4';
    section.setAttribute('data-course-version-section', 'true');
    var h2 = document.createElement('h2');
    h2.className = 'h4';
    h2.textContent = 'Course Version';
    var ul = document.createElement('ul');
    ul.className = 'list-unstyled';
    section.appendChild(h2);
    section.appendChild(ul);
    sidebar.appendChild(section);
  }
  var sectionList = section.querySelector('ul');
  if (item.parentNode !== sectionList) sectionList.appendChild(item);
}
var cvCached = null;
var cvPending = false;
function cvRender() {
  if (cvCached) cvEnsure(cvCached);
}
function cvBoot() {
  var courseId = cvCourseIdFromUrl();
  if (!courseId) return;
  if (!cvLmsBase()) { setTimeout(cvBoot, 300); return; }
  if (cvCached) { cvRender(); return; }
  if (cvPending) return;
  cvPending = true;
  fetch(cvApi(courseId), { credentials: 'include' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (payload) {
      cvPending = false;
      if (payload && payload.display) { cvCached = payload; cvRender(); }
    })
    .catch(function () { cvPending = false; });
}
function cvWatchRouteChanges() {
  var last = window.location.pathname;
  new MutationObserver(function () {
    if (window.location.pathname !== last) {
      last = window.location.pathname;
      cvCached = null;
      cvPending = false;
      var old = document.querySelector('[data-course-version-tag]');
      if (old) old.remove();
      cvBoot();
      return;
    }
    cvRender();
  }).observe(document.documentElement, { childList: true, subtree: true });
}
subscribe(APP_READY, function () { cvBoot(); cvWatchRouteChanges(); });
COURSE_VERSION_EOF
# Import the badge so webpack bundles it. Idempotent.
RUN grep -q "course-version/CourseVersionTag" /openedx/app/src/index.jsx || echo "import './course-version/CourseVersionTag';" >> /openedx/app/src/index.jsx
"""

LEARNING_BADGE_CSS = r"""
# --- tutor-contrib-course-version: learning badge styles (sidebar row + pill) ---
RUN cat >> /openedx/app/src/index.scss <<'COURSE_VERSION_CSS_EOF'

""" + PILL_CSS + r"""
.course-version-item{display:inline-flex;align-items:center;color:var(--link-color, #006daa);}
.course-version-item__label{min-width:0;overflow-wrap:anywhere;}
COURSE_VERSION_CSS_EOF
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("mfe-dockerfile-pre-npm-build-learning", LEARNING_BADGE_JS + LEARNING_BADGE_CSS)
)

# ---------------------------------------------------------------------------
# MFE routing: the Learning MFE is served under /learning, so the legacy
# /course/<course_id> URL used to return an empty page. Redirect it to the
# real path (and /course with no id to the LMS dashboard) instead of showing
# nothing. Patch text is Jinja-rendered, hence {{ LMS_HOST }}.
# ---------------------------------------------------------------------------

CADDY_COURSE_ROUTE = r"""
# --- tutor-contrib-course-version: /course/<id> -> Learning MFE ---
@cv_course_prefix path /course/*
redir @cv_course_prefix /learning{uri} permanent
@cv_course_root path /course
redir @cv_course_root http://{{ LMS_HOST }}/dashboard permanent
"""

hooks.Filters.ENV_PATCHES.add_item(("mfe-caddyfile", CADDY_COURSE_ROUTE))

# ---------------------------------------------------------------------------
# Course Authoring MFE (Studio Advanced Settings): same pill (fetched live
# from the API for the course in the URL) + a soft highlight on the fields.
# ---------------------------------------------------------------------------

AUTHORING_HELPER = r"""
# --- tutor-contrib-course-version: studio advanced-settings helper ---
RUN mkdir -p /openedx/app/src/course-version && cat > /openedx/app/src/course-version/studio-version-helper.js <<'COURSE_VERSION_STUDIO_EOF'
// Same name • Version X pill above Advanced Settings (live data), plus a
// soft highlight on the three version fields.
""" + PILL_BUILDER_JS + r"""
(function () {
  function isAdvancedSettings() { return /advanced[-_]settings/i.test(location.pathname); }
  function courseIdFromUrl() {
    var m = location.pathname.match(/\/course\/([^/?#]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }
  function lmsBase() {
    var c = window.__MFE_CONFIG__ || {};
    return String(c.LMS_BASE_URL || '').replace(/\/$/, '');
  }
  function findRow(labelPart) {
    var nodes = Array.from(document.querySelectorAll('*')).filter(function (n) {
      return n.children.length === 0 && n.textContent.trim() === labelPart;
    });
    return nodes.length ? nodes[0].closest('div[class*="setting"], div[class*="row"], section, li') : null;
  }
  function inject(payload) {
    if (!payload || !payload.display) return;
    if (document.querySelector('[data-course-version-helper]')) return;
    var anchor = document.querySelector('main, #root main, .advanced-settings');
    if (!anchor) return;
    var el = cvBadgeEl(payload);
    el.setAttribute('data-course-version-helper', 'true');
    anchor.prepend(el);
  }
  function boot() {
    if (!isAdvancedSettings() || document.querySelector('[data-course-version-helper]')) return;
    var courseId = courseIdFromUrl();
    var base = lmsBase();
    if (!courseId || !base) return;
    fetch(base + '/api/course_version/v1/' + encodeURIComponent(courseId), { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(inject)
      .catch(function () {});
    ['Course Version', 'Version Of (Parent Course)', 'Show Version Tag to Learners'].forEach(function (label) {
      var row = findRow(label);
      if (row) row.classList.add('course-version-field');
    });
  }
  new MutationObserver(boot).observe(document.documentElement, { childList: true, subtree: true });
  boot();
})();
COURSE_VERSION_STUDIO_EOF
# Import the helper so webpack bundles it. Idempotent.
RUN for f in /openedx/app/src/index.jsx /openedx/app/src/index.js; do if [ -f "$f" ]; then grep -q "studio-version-helper" "$f" || echo "import './course-version/studio-version-helper';" >> "$f"; fi; done
RUN cat >> /openedx/app/src/index.scss <<'COURSE_VERSION_STUDIO_CSS_EOF'

""" + PILL_CSS + r"""
.course-version-field{outline:2px solid #7fb3e8 !important;outline-offset:4px;border-radius:8px;}
COURSE_VERSION_STUDIO_CSS_EOF
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("mfe-dockerfile-pre-npm-build-authoring", AUTHORING_HELPER)
)

# ---------------------------------------------------------------------------
# Learner Dashboard MFE: the course list. Every course card gets the same
# navy name • Version X pill under the title. One fetch per course (cached).
# ---------------------------------------------------------------------------

DASHBOARD_BADGE = r"""
# --- tutor-contrib-course-version: learner-dashboard course-card badge ---
RUN mkdir -p /openedx/app/src/course-version && cat > /openedx/app/src/course-version/CourseVersionDashboardTag.js <<'COURSE_VERSION_DASH_EOF'
// Version pill on each learner-dashboard course card (course list).
// Same navy pill as the Learning MFE: course name • Version X only.
// One fetch per course (cached).
import { getConfig, subscribe, APP_READY } from '@edx/frontend-platform';
""" + PILL_BUILDER_JS + r"""
var cvCache = {};
var cvStyleId = 'course-version-style';
function cvEnsureStyle() {
  if (document.getElementById(cvStyleId)) return;
  var s = document.createElement('style');
  s.id = cvStyleId;
  s.textContent = """ + "'" + "PLACEHOLDER" + "'" + r""";
  document.head.appendChild(s);
}
function cvLmsBase() {
  try { return (getConfig() && getConfig().LMS_BASE_URL) || ''; } catch (e) { return ''; }
}
function cvApi(courseId) {
  return String(cvLmsBase()).replace(/\/$/, '') + '/api/course_version/v1/' + encodeURIComponent(courseId);
}
function cvCourseIdFromHref(href) {
  var h = String(href || '');
  var m = h.match(/\/course\/([^/?#]+)/) || h.match(/\/courses\/([^/?#]+)\//);
  return m ? decodeURIComponent(m[1]) : null;
}
function cvInject(card, payload) {
  if (card.querySelector('[data-course-version-tag]')) return;
  cvEnsureStyle();
  var title = card.querySelector('[data-testid="CourseCardTitle"]');
  var host = (title && (title.closest('h3') || title.parentElement)) || card;
  host.insertAdjacentElement('afterend', cvBadgeEl(payload));
}
function cvProcessCard(card) {
  if (card.querySelector('[data-course-version-tag]')) return;
  var title = card.querySelector('[data-testid="CourseCardTitle"]');
  var href = title && (title.getAttribute('href') || (title.closest('a') && title.closest('a').getAttribute('href')));
  var courseId = cvCourseIdFromHref(href);
  if (!courseId) return;
  if (Object.prototype.hasOwnProperty.call(cvCache, courseId)) {
    if (cvCache[courseId]) cvInject(card, cvCache[courseId]);
    return;
  }
  if (!cvLmsBase()) { setTimeout(function () { cvProcessCard(card); }, 300); return; }
  fetch(cvApi(courseId), { credentials: 'include' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (payload) {
      cvCache[courseId] = (payload && payload.display) ? payload : null;
      if (cvCache[courseId]) cvInject(card, cvCache[courseId]);
    })
    .catch(function () { cvCache[courseId] = null; });
}
function cvScan() {
  var cards = document.querySelectorAll('[data-testid="CourseCard"]');
  for (var i = 0; i < cards.length; i++) cvProcessCard(cards[i]);
}
function cvWatch() {
  new MutationObserver(function () { cvScan(); }).observe(document.documentElement, { childList: true, subtree: true });
}
subscribe(APP_READY, function () { cvScan(); cvWatch(); });
COURSE_VERSION_DASH_EOF
# Import the badge so webpack bundles it (index.jsx or index.js). Idempotent.
RUN for f in /openedx/app/src/index.jsx /openedx/app/src/index.js; do if [ -f "$f" ]; then grep -q "CourseVersionDashboardTag" "$f" || echo "import './course-version/CourseVersionDashboardTag';" >> "$f"; fi; done
"""

# The dashboard MFE has no index.scss guarantee; inject styles via the shared
# stylesheet string baked into the JS above. Replace the PLACEHOLDER with the
# real CSS (escaped for a JS single-quoted string).
DASHBOARD_BADGE = DASHBOARD_BADGE.replace(
    "'PLACEHOLDER'",
    "'" + PILL_CSS.replace("\\", "\\\\").replace("'", "\\'") + "'",
)

hooks.Filters.ENV_PATCHES.add_item(
    ("mfe-dockerfile-pre-npm-build-learner-dashboard", DASHBOARD_BADGE)
)
