/* Adds the course version pill (course name • Version X) above the Advanced
 * Settings list, and highlights the three version fields. Same navy pill as
 * the learner-dashboard course cards.
 * Injected into frontend-app-course-authoring by the Tutor
 * `mfe-dockerfile-pre-npm-build-authoring` patch (no MFE fork).
 */
import { getConfig, subscribe, APP_READY } from '@edx/frontend-platform';

var NAME_LIMIT = 34;

function truncateName(s, limit) {
  s = String(s || '').trim();
  if (s.length <= limit) return s;
  var cut = s.slice(0, limit);
  var sp = cut.lastIndexOf(' ');
  if (sp > limit * 0.55) cut = cut.slice(0, sp);
  return cut.replace(/\s+$/, '') + '...';
}
function fullName(name, version) {
  if (name && version) return name + ' • Version ' + version;
  if (version) return 'Version ' + version;
  return name;
}
function badgeEl(payload) {
  var name = String(payload.version_of || '').trim();
  var version = String(payload.version || '').trim();
  var el = document.createElement('div');
  el.setAttribute('data-course-version-tag', 'true');
  el.setAttribute('data-course-version-helper', 'true');
  el.className = 'course-version-tag';
  el.setAttribute('role', 'status');
  el.title = fullName(name, version);
  if (name) {
    var n = document.createElement('span');
    n.className = 'course-version-tag__name';
    n.textContent = truncateName(name, NAME_LIMIT);
    el.appendChild(n);
  }
  if (name && version) {
    var sep = document.createElement('span');
    sep.className = 'course-version-tag__sep';
    sep.textContent = '•';
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
function lmsBase() {
  try { return (getConfig() && getConfig().LMS_BASE_URL) || ''; } catch (e) { return ''; }
}
function courseIdFromUrl() {
  var m = window.location.pathname.match(/\/course\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
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
  anchor.prepend(badgeEl(payload));
}
function boot() {
  if (!/advanced[-_]settings/i.test(window.location.pathname)) return;
  if (document.querySelector('[data-course-version-helper]')) return;
  var courseId = courseIdFromUrl();
  var base = lmsBase();
  if (!courseId || !base) return;
  fetch(String(base).replace(/\/$/, '') + '/api/course_version/v1/' + encodeURIComponent(courseId), { credentials: 'include' })
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
