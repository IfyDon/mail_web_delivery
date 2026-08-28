// Dashboard dark/light theme toggle.
// Loaded as a blocking <script src> (not inline) because the CSP's
// script-src is 'self' with no 'unsafe-inline' and no script nonce —
// an inline <script> here would be silently dropped by the browser.
(function () {
  try {
    var stored = localStorage.getItem('wm_theme');
    var dark = stored ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (dark) document.documentElement.classList.add('dark');
  } catch (e) {}

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var isDark = document.documentElement.classList.toggle('dark');
      try { localStorage.setItem('wm_theme', isDark ? 'dark' : 'light'); } catch (e) {}
    });
  });
})();
