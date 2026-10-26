/* Adds the course version tag pill above the Advanced Settings list, and
 * highlights the three version fields.
 * Injected into frontend-app-course-authoring by the Tutor
 * `mfe-dockerfile-pre-npm-build-course-authoring` patch (no MFE fork).
 */
(function () {
  function isAdvancedSettings() { return /advanced[-_]settings/i.test(window.location.pathname); }
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
