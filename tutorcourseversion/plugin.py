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

3. Injects a small, dependency-free badge into the **Learning MFE** and the
   same version **tag pill** (plus a field highlight) at the top of the
   **Course Authoring MFE Advanced Settings** page via
   ``mfe-dockerfile-pre-npm-build-*`` patches — no MFE fork needed.

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
# Learning MFE: floating version pill (learners + staff see the same tag;
# staff additionally get an "Edit in Studio" link).
# ---------------------------------------------------------------------------

LEARNING_BADGE_JS = r"""
# --- tutor-contrib-course-version: learning badge ---
RUN mkdir -p /openedx/app/src/course-version && cat > /openedx/app/src/course-version/CourseVersionTag.js <<'COURSE_VERSION_EOF'
// Dependency-free badge: version pill for course-home + courseware.
// Indigo-styled, bigger. Long course names truncate to NAME_LIMIT chars with
// '...'; the version segment never shrinks so it is ALWAYS shown.
// Calls the absolute LMS base URL (cross-origin MFE -> LMS) with credentials.
import { getConfig, subscribe, APP_READY } from '@edx/frontend-platform';

var NAME_LIMIT = 34;

function lmsBase() {
  try { return (getConfig() && getConfig().LMS_BASE_URL) || ''; } catch (e) { return ''; }
}
function studioBase() {
  try { return (getConfig() && getConfig().STUDIO_BASE_URL) || ''; } catch (e) { return ''; }
}
function api(courseId) {
  return String(lmsBase()).replace(/\/$/, '') + '/api/course_version/v1/' + encodeURIComponent(courseId);
}
function courseIdFromUrl() {
  var m = window.location.pathname.match(/\/course\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}
function truncateName(s, limit) {
  s = String(s || '').trim();
  if (s.length <= limit) return s;
  var cut = s.slice(0, limit);
  var sp = cut.lastIndexOf(' ');
  if (sp > limit * 0.55) cut = cut.slice(0, sp);
  return cut.replace(/\s+$/, '') + '...';
}
function fullName(name, version) {
  if (name && version) return name + ' \u2022 Version ' + version;
  if (version) return 'Version ' + version;
  return name;
}
function badgeEl(payload) {
  var name = String(payload.version_of || '').trim();
  var version = String(payload.version || '').trim();
  var el = document.createElement('div');
  el.setAttribute('data-course-version-tag', 'true');
  el.className = 'course-version-tag' + (payload.is_staff ? ' is-staff' : '');
  el.setAttribute('role', 'status');
  el.title = fullName(name, version);
  var icon = document.createElement('span');
  icon.className = 'course-version-tag__icon';
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = '\u25a3';
  el.appendChild(icon);
  if (name) {
    var n = document.createElement('span');
    n.className = 'course-version-tag__name';
    n.textContent = truncateName(name, NAME_LIMIT);
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
  if (payload.is_staff) {
    var a = document.createElement('a');
    a.className = 'course-version-tag__edit';
    a.href = String(studioBase()).replace(/\/$/, '') + '/course/' + payload.course_id;
    a.textContent = 'Edit in Studio';
    a.title = 'Visible to all learners. Click to edit the version in Studio.';
    el.appendChild(a);
  }
  return el;
}
function mount(payload) {
  if (!payload || !payload.display) return;
  if (document.querySelector('[data-course-version-tag]')) return;
  var anchor = document.querySelector('.course-home-outline .page-header, .courseware-header, header.course-header, main');
  var el = badgeEl(payload);
  if (anchor && anchor.prepend) { anchor.prepend(el); } else { document.body.prepend(el); }
}
function boot() {
  var courseId = courseIdFromUrl();
  if (!courseId) return;
  if (!lmsBase()) { setTimeout(boot, 300); return; }
  fetch(api(courseId), { credentials: 'include' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(mount)
    .catch(function () {});
}
function watchRouteChanges() {
  var last = window.location.pathname;
  new MutationObserver(function () {
    if (window.location.pathname !== last) {
      last = window.location.pathname;
      var old = document.querySelector('[data-course-version-tag]');
      if (old) old.remove();
      boot();
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
}
subscribe(APP_READY, function () { boot(); watchRouteChanges(); });
COURSE_VERSION_EOF
# Import the badge so webpack bundles it. Idempotent.
RUN grep -q "course-version/CourseVersionTag" /openedx/app/src/index.jsx || echo "import './course-version/CourseVersionTag';" >> /openedx/app/src/index.jsx
"""

LEARNING_BADGE_CSS = r"""
# --- tutor-contrib-course-version: learning badge styles (Indigo, bigger) ---
RUN cat >> /openedx/app/src/index.scss <<'COURSE_VERSION_CSS_EOF'

.course-version-tag{display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:clamp(.35rem,1.4vw,.55rem);margin:clamp(.6rem,2vw,.85rem) 0;padding:clamp(.5rem,1.8vw,.7rem) clamp(.8rem,2.6vw,1.15rem);border-radius:clamp(.5rem,1.4vw,.7rem);box-sizing:border-box;max-width:100%;font-family:Inter,system-ui,-apple-system,sans-serif;font-size:clamp(.83rem,1.4vw,.97rem);font-weight:600;line-height:1.35;color:#fff;background:#0a3055;border:1px solid #0a3055;box-shadow:0 2px 5px rgba(10,48,85,.28);vertical-align:middle;}
.course-version-tag__icon{flex:0 0 auto;font-size:1.05em;line-height:1;opacity:.9;}
.course-version-tag__name{flex:0 1 auto;min-width:4em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.course-version-tag__sep{flex:0 0 auto;opacity:.65;}
.course-version-tag__version{flex:0 0 auto;white-space:nowrap;font-weight:700;}
.course-version-tag.is-staff{border-color:#0a3055;background:#0a3055;}
.course-version-tag__edit{flex:0 0 auto;white-space:nowrap;font-size:.83em;font-weight:700;text-decoration:underline;color:#fff;}
COURSE_VERSION_CSS_EOF
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("mfe-dockerfile-pre-npm-build-learning", LEARNING_BADGE_JS + LEARNING_BADGE_CSS)
)

# ---------------------------------------------------------------------------
# Course Authoring MFE (Studio Advanced Settings): version tag + highlight.
# The three fields already render automatically; this adds the same navy tag
# pill learners see (at the top of the page) + a soft highlight around the
# fields — no explainer card.
# ---------------------------------------------------------------------------

AUTHORING_HELPER = r"""
# --- tutor-contrib-course-version: studio advanced-settings helper ---
RUN mkdir -p /openedx/app/src/course-version && cat > /openedx/app/src/course-version/studio-version-helper.js <<'COURSE_VERSION_STUDIO_EOF'
// Adds the course version tag pill above the Advanced Settings list, and
// highlights the three version fields.
(function () {
  function isAdvancedSettings() { return /advanced[-_]settings/i.test(location.pathname); }
  function findRow(labelPart) {
    var nodes = Array.from(document.querySelectorAll('*')).filter(function (n) {
      return n.children.length === 0 && n.textContent.trim() === labelPart;
    });
    return nodes.length ? nodes[0].closest('div[class*="setting"], div[class*="row"], section, li') : null;
  }
  function boot() {
    if (!isAdvancedSettings() || document.querySelector('[data-course-version-helper]')) return;
    var anchor = document.querySelector('main, #root main, .advanced-settings');
    if (!anchor) return;
    var tag = document.createElement('span');
    tag.setAttribute('data-course-version-helper', 'true');
    tag.className = 'course-version-tag';
    tag.innerHTML =
      '<span class="course-version-tag__icon">▣</span>' +
      '<span class="course-version-tag__name">CS101 - Intro to Python</span>' +
      '<span class="course-version-tag__sep">•</span>' +
      '<span class="course-version-tag__version">Version v2.0</span>';
    anchor.prepend(tag);
    ['Course Version', 'Version Of (Parent Course)', 'Show Version Tag to Learners'].forEach(function (label) {
      var row = findRow(label);
      if (row) row.classList.add('course-version-field');
    });
  }
  new MutationObserver(boot).observe(document.documentElement, { childList: true, subtree: true });
  boot();
})();
COURSE_VERSION_STUDIO_EOF
RUN cat >> /openedx/app/src/index.scss <<'COURSE_VERSION_STUDIO_CSS_EOF'

/* Course version tag pill + field highlight for course version. */
.course-version-tag{display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:clamp(.35rem,1.4vw,.55rem);margin:clamp(.6rem,2vw,.85rem) 0;padding:clamp(.5rem,1.8vw,.7rem) clamp(.8rem,2.6vw,1.15rem);border-radius:clamp(.5rem,1.4vw,.7rem);box-sizing:border-box;max-width:100%;font-family:Inter,system-ui,-apple-system,sans-serif;font-size:clamp(.83rem,1.4vw,.97rem);font-weight:600;line-height:1.35;color:#fff;background:#0a3055;border:1px solid #0a3055;box-shadow:0 2px 5px rgba(10,48,85,.28);vertical-align:middle;}
.course-version-tag__icon{flex:0 0 auto;font-size:1.05em;line-height:1;opacity:.9;}
.course-version-tag__name{flex:0 1 auto;min-width:4em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.course-version-tag__sep{flex:0 0 auto;opacity:.65;}
.course-version-tag__version{flex:0 0 auto;white-space:nowrap;font-weight:700;}
.course-version-field{outline:2px solid #7fb3e8 !important;outline-offset:4px;border-radius:8px;}
COURSE_VERSION_STUDIO_CSS_EOF
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("mfe-dockerfile-pre-npm-build-course-authoring", AUTHORING_HELPER)
)

# ---------------------------------------------------------------------------
# Learner Dashboard MFE (course list): show the version pill on each course card.
# The dashboard renders many [data-testid="CourseCard"] cards; each title link's
# href ends in /course/<course_id> (learning MFE) or /courses/<id>/ (legacy LMS).
# We scan the DOM, fetch the version per course (cached), and append the pill.
# ---------------------------------------------------------------------------

DASHBOARD_BADGE = r"""
# --- tutor-contrib-course-version: learner-dashboard course-card badge ---
RUN mkdir -p /openedx/app/src/course-version && cat > /openedx/app/src/course-version/CourseVersionDashboardTag.js <<'COURSE_VERSION_DASH_EOF'
// Version pill on each learner-dashboard course card (course list).
// Indigo-styled, bigger. Long course names truncate with '...'; the version
// segment never shrinks so it is ALWAYS shown. One fetch per course (cached).
import { getConfig, subscribe, APP_READY } from '@edx/frontend-platform';

var NAME_LIMIT = 34;
var STYLE_ID = 'course-version-style';
var cache = {};

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  var css = ['.course-version-tag{display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:clamp(.35rem,1.4vw,.55rem);margin:clamp(.6rem,2vw,.85rem) 0;padding:clamp(.5rem,1.8vw,.7rem) clamp(.8rem,2.6vw,1.15rem);border-radius:clamp(.5rem,1.4vw,.7rem);box-sizing:border-box;max-width:100%;font-family:Inter,system-ui,-apple-system,sans-serif;font-size:clamp(.83rem,1.4vw,.97rem);font-weight:600;line-height:1.35;color:#fff;background:#0a3055;border:1px solid #0a3055;box-shadow:0 2px 5px rgba(10,48,85,.28);vertical-align:middle;}',
    '.course-version-tag__icon{flex:0 0 auto;font-size:1.05em;line-height:1;opacity:.9;}',
    '.course-version-tag__name{flex:0 1 auto;min-width:4em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
    '.course-version-tag__sep{flex:0 0 auto;opacity:.65;}',
    '.course-version-tag__version{flex:0 0 auto;white-space:nowrap;font-weight:700;}',
    '.course-version-tag.is-staff{border-color:#0a3055;background:#0a3055;}'].join('');
  var s = document.createElement('style');
  s.id = STYLE_ID;
  s.textContent = css;
  document.head.appendChild(s);
}
function lmsBase() {
  try { return (getConfig() && getConfig().LMS_BASE_URL) || ''; } catch (e) { return ''; }
}
function api(courseId) {
  return String(lmsBase()).replace(/\/$/, '') + '/api/course_version/v1/' + encodeURIComponent(courseId);
}
function courseIdFromHref(href) {
  var h = String(href || '');
  var m = h.match(/\/course\/([^/?#]+)/) || h.match(/\/courses\/([^/?#]+)\//);
  return m ? decodeURIComponent(m[1]) : null;
}
function truncateName(s, limit) {
  s = String(s || '').trim();
  if (s.length <= limit) return s;
  var cut = s.slice(0, limit);
  var sp = cut.lastIndexOf(' ');
  if (sp > limit * 0.55) cut = cut.slice(0, sp);
  return cut.replace(/\s+$/, '') + '...';
}
function fullName(name, version) {
  if (name && version) return name + ' \u2022 Version ' + version;
  if (version) return 'Version ' + version;
  return name;
}
function badgeEl(payload) {
  var name = String(payload.version_of || '').trim();
  var version = String(payload.version || '').trim();
  var el = document.createElement('div');
  el.setAttribute('data-course-version-tag', 'true');
  el.className = 'course-version-tag' + (payload.is_staff ? ' is-staff' : '');
  el.setAttribute('role', 'status');
  el.title = fullName(name, version);
  var icon = document.createElement('span');
  icon.className = 'course-version-tag__icon';
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = '\u25a3';
  el.appendChild(icon);
  if (name) {
    var n = document.createElement('span');
    n.className = 'course-version-tag__name';
    n.textContent = truncateName(name, NAME_LIMIT);
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
function inject(card, payload) {
  if (card.querySelector('[data-course-version-tag]')) return;
  ensureStyle();
  var title = card.querySelector('[data-testid="CourseCardTitle"]');
  var host = (title && (title.closest('h3') || title.parentElement)) || card;
  host.insertAdjacentElement('afterend', badgeEl(payload));
}
function processCard(card) {
  if (card.querySelector('[data-course-version-tag]')) return;
  var title = card.querySelector('[data-testid="CourseCardTitle"]');
  var href = title && (title.getAttribute('href') || (title.closest('a') && title.closest('a').getAttribute('href')));
  var courseId = courseIdFromHref(href);
  if (!courseId) return;
  if (Object.prototype.hasOwnProperty.call(cache, courseId)) {
    if (cache[courseId]) inject(card, cache[courseId]);
    return;
  }
  if (!lmsBase()) { setTimeout(function () { processCard(card); }, 300); return; }
  fetch(api(courseId), { credentials: 'include' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (payload) {
      cache[courseId] = (payload && payload.display) ? payload : null;
      if (cache[courseId]) inject(card, cache[courseId]);
    })
    .catch(function () { cache[courseId] = null; });
}
function scan() {
  var cards = document.querySelectorAll('[data-testid="CourseCard"]');
  for (var i = 0; i < cards.length; i++) processCard(cards[i]);
}
function watch() {
  new MutationObserver(function () { scan(); }).observe(document.documentElement, { childList: true, subtree: true });
}
subscribe(APP_READY, function () { ensureStyle(); scan(); watch(); });
COURSE_VERSION_DASH_EOF
# Import the badge so webpack bundles it (index.jsx or index.js). Idempotent.
RUN for f in /openedx/app/src/index.jsx /openedx/app/src/index.js; do if [ -f "$f" ]; then grep -q "CourseVersionDashboardTag" "$f" || echo "import './course-version/CourseVersionDashboardTag';" >> "$f"; fi; done
"""

hooks.Filters.ENV_PATCHES.add_item(
    ("mfe-dockerfile-pre-npm-build-learner-dashboard", DASHBOARD_BADGE)
)

