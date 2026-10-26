/* Adds a friendly "Course version" explainer + live pill preview above the
 * Advanced Settings list, and highlights the three version fields.
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
    var card = document.createElement('div');
    card.setAttribute('data-course-version-helper', 'true');
    card.className = 'course-version-helper';
    card.innerHTML =
      '<h3>Course version</h3>' +
      '<p>Tell learners <strong>which version of which course</strong> this is. ' +
      'Fill <em>Course Version</em> (e.g. <code>v2.0</code>) and ' +
      '<em>Version Of (Parent Course)</em> (e.g. <code>CS101 - Intro to Python</code>). ' +
      'Both learners and staff will see it as a pill badge on the course pages.</p>' +
      '<div class="course-version-helper__preview"><span class="course-version-tag">' +
      '<span class="course-version-tag__icon">▣</span>' +
      '<span class="course-version-tag__text">CS101 - Intro to Python • Version v2.0</span>' +
      '</span></div>';
    anchor.prepend(card);
    ['Course Version', 'Version Of (Parent Course)', 'Show Version Tag to Learners'].forEach(function (label) {
      var row = findRow(label);
      if (row) row.classList.add('course-version-field');
    });
  }
  new MutationObserver(boot).observe(document.documentElement, { childList: true, subtree: true });
  boot();
})();
