(function () {
  var STORAGE_KEY = 'wm_cookie_consent';

  function show() {
    var el = document.getElementById('cookie-banner');
    if (el) el.classList.remove('hidden');
  }

  function hide() {
    var el = document.getElementById('cookie-banner');
    if (el) el.classList.add('hidden');
  }

  function persist(prefs) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        ts: Date.now(),
        strictly_necessary: true,
        performance: !!prefs.performance,
        functional: !!prefs.functional,
        targeting: !!prefs.targeting,
      }));
    } catch (_) {}
    hide();
  }

  function getPrefs() {
    return {
      performance: (document.getElementById('cb-performance') || {}).checked !== false,
      functional:  (document.getElementById('cb-functional')  || {}).checked !== false,
      targeting:   !!(document.getElementById('cb-targeting')  || {}).checked,
    };
  }

  function init() {
    try {
      if (localStorage.getItem(STORAGE_KEY)) return;
    } catch (_) {}
    show();

    var reject = document.getElementById('cb-reject');
    var save   = document.getElementById('cb-save');
    var accept = document.getElementById('cb-accept');

    if (reject) reject.addEventListener('click', function () {
      var cb = document.getElementById('cb-performance');
      var cb2 = document.getElementById('cb-functional');
      var cb3 = document.getElementById('cb-targeting');
      if (cb)  cb.checked  = false;
      if (cb2) cb2.checked = false;
      if (cb3) cb3.checked = false;
      persist({ performance: false, functional: false, targeting: false });
    });

    if (save) save.addEventListener('click', function () {
      persist(getPrefs());
    });

    if (accept) accept.addEventListener('click', function () {
      var cb = document.getElementById('cb-performance');
      var cb2 = document.getElementById('cb-functional');
      var cb3 = document.getElementById('cb-targeting');
      if (cb)  cb.checked  = true;
      if (cb2) cb2.checked = true;
      if (cb3) cb3.checked = true;
      persist({ performance: true, functional: true, targeting: true });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
