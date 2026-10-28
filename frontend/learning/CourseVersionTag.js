// Course version tag.
// Course home: an <li class="small"> row inside the Course Tools sidebar list —
// same markup + icon spacing as Bookmarks / Updates / Launch tour.
// Any other page (courseware header, pages without the sidebar): the navy
// "course name • Version X" pill.
// Calls the absolute LMS base URL (cross-origin MFE -> LMS) with credentials.
import { getConfig, subscribe, APP_READY } from '@edx/frontend-platform';

var NAME_LIMIT = 34;
var TAG_PATH = 'M0 252.118V48C0 21.49 21.49 0 48 0h204.118a48 48 0 0 1 33.941 14.059l211.882 211.882c18.745 18.745 18.745 49.137 0 67.882L293.823 497.941c-18.745 18.745-49.137 18.745-67.882 0L14.059 286.059A48 48 0 0 1 0 252.118zM112 64c-26.51 0-48 21.49-48 48s21.49 48 48 48 48-21.49 48-48-21.49-48-48-48z';

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
function displayText(payload) {
  var name = truncateName(payload.version_of, NAME_LIMIT);
  var version = String(payload.version || '').trim();
  return fullName(name, version);
}
function iconEl() {
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
  path.setAttribute('d', TAG_PATH);
  svg.appendChild(path);
  return svg;
}
function itemEl(payload) {
  var li = document.createElement('li');
  li.className = 'small course-version-item';
  li.setAttribute('data-course-version-tag', 'true');
  li.title = fullName(String(payload.version_of || '').trim(), String(payload.version || '').trim());
  li.appendChild(iconEl());
  var label = document.createElement('span');
  label.className = 'course-version-item__label';
  label.textContent = displayText(payload);
  li.appendChild(label);
  return li;
}
function badgeEl(payload) {
  var name = String(payload.version_of || '').trim();
  var version = String(payload.version || '').trim();
  var el = document.createElement('div');
  el.setAttribute('data-course-version-tag', 'true');
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
function api(courseId) {
  return String(lmsBase()).replace(/\/$/, '') + '/api/course_version/v1/' + encodeURIComponent(courseId);
}
function courseIdFromUrl() {
  var m = window.location.pathname.match(/\/course\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}
function ensure(payload) {
  if (!payload || !payload.display) return;
  var node = document.querySelector('[data-course-version-tag]');
  var sidebar = document.querySelector('.course-outline-tab .col-md-4');

  if (!sidebar) {
    if (node && node.classList.contains('course-version-tag')) return;
    if (node) node.remove();
    var anchor = document.querySelector('.course-home-outline .page-header, .courseware-header, header.course-header, main');
    var pill = badgeEl(payload);
    if (anchor && anchor.prepend) { anchor.prepend(pill); } else { document.body.prepend(pill); }
    return;
  }

  if (node && node.classList.contains('course-version-tag')) { node.remove(); node = null; }
  if (node && (node.tagName !== 'LI' || !node.classList.contains('course-version-item'))) { node.remove(); node = null; }
  var item = node || itemEl(payload);

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
var cached = null;
var pending = false;
function render() {
  if (cached) ensure(cached);
}
function boot() {
  var courseId = courseIdFromUrl();
  if (!courseId) return;
  if (!lmsBase()) { setTimeout(boot, 300); return; }
  if (cached) { render(); return; }
  if (pending) return;
  pending = true;
  fetch(api(courseId), { credentials: 'include' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (payload) {
      pending = false;
      if (payload && payload.display) { cached = payload; render(); }
    })
    .catch(function () { pending = false; });
}
function watchRouteChanges() {
  var last = window.location.pathname;
  new MutationObserver(function () {
    if (window.location.pathname !== last) {
      last = window.location.pathname;
      cached = null;
      pending = false;
      var old = document.querySelector('[data-course-version-tag]');
      if (old) old.remove();
      boot();
      return;
    }
    render();
  }).observe(document.documentElement, { childList: true, subtree: true });
}
subscribe(APP_READY, function () { boot(); watchRouteChanges(); });
