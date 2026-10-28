// Studio course list: same name • Version X pill on each course card.
// Scans .course-item[data-course-key], fetches the same-origin API once per
// course (cached) and inserts the pill under the course title.
(function () {
  'use strict';

  var NAME_LIMIT = 34;
  var STYLE_ID = 'course-version-style';
  var cache = {};

  var PILL_CSS =
    '.course-version-tag{display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;' +
    'gap:clamp(.35rem,1.4vw,.55rem);margin:clamp(.4rem,1.5vw,.65rem) 0;' +
    'padding:clamp(.4rem,1.5vw,.55rem) clamp(.75rem,2.2vw,1rem);border-radius:999px;' +
    'box-sizing:border-box;max-width:100%;font-family:Inter,system-ui,-apple-system,sans-serif;' +
    'font-size:clamp(.8rem,1.3vw,.92rem);font-weight:600;line-height:1.35;color:#fff;background:#0a3055;' +
    'border:1px solid #0a3055;box-shadow:0 2px 5px rgba(10,48,85,.28);vertical-align:middle;}' +
    '.course-version-tag__name{flex:0 1 auto;min-width:4em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}' +
    '.course-version-tag__sep{flex:0 0 auto;opacity:.65;}' +
    '.course-version-tag__version{flex:0 0 auto;white-space:nowrap;font-weight:700;}';

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = PILL_CSS;
    document.head.appendChild(s);
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

  function api(courseKey) {
    return '/api/course_version/v1/' + encodeURIComponent(courseKey);
  }

  function inject(item, payload) {
    if (item.querySelector('[data-course-version-tag]')) return;
    ensureStyle();
    var title = item.querySelector('h3.course-title');
    if (title) {
      title.insertAdjacentElement('afterend', badgeEl(payload));
    } else {
      item.appendChild(badgeEl(payload));
    }
  }

  function processItem(item) {
    if (item.querySelector('[data-course-version-tag]')) return;
    var key = item.getAttribute('data-course-key');
    if (!key) return;
    if (Object.prototype.hasOwnProperty.call(cache, key)) {
      if (cache[key]) inject(item, cache[key]);
      return;
    }
    fetch(api(key), { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (payload) {
        cache[key] = (payload && payload.display) ? payload : null;
        if (cache[key]) inject(item, cache[key]);
      })
      .catch(function () { cache[key] = null; });
  }

  function scan() {
    var items = document.querySelectorAll('.course-item[data-course-key]');
    for (var i = 0; i < items.length; i++) processItem(items[i]);
  }

  scan();
  new MutationObserver(function () { scan(); }).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
