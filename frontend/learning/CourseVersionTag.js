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
