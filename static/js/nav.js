(function() {
  function id(s) { return document.getElementById(s); }

  /* ── Theme ─────────────────────────────────────────────── */
  function applyTheme(dark) {
    var t = dark ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('wm_theme', t); } catch(e) {}
    var sun  = id('theme-icon-sun'),  moon  = id('theme-icon-moon'),  lbl  = id('theme-label');
    var msun = id('mob-theme-icon-sun'), mmoon = id('mob-theme-icon-moon'), mlbl = id('mob-theme-label');
    if (sun)   sun.style.display  = dark ? '' : 'none';
    if (moon)  moon.style.display = dark ? 'none' : '';
    if (lbl)   lbl.textContent    = dark ? 'Light' : 'Dark';
    if (msun)  msun.style.display  = dark ? '' : 'none';
    if (mmoon) mmoon.style.display = dark ? 'none' : '';
    if (mlbl)  mlbl.textContent    = dark ? 'Light' : 'Dark';
  }

  // Sync icons with current theme on load
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark');

  function toggleTheme() { applyTheme(document.documentElement.getAttribute('data-theme') !== 'dark'); }
  var tb = id('theme-btn'), mtb = id('mob-theme-btn');
  if (tb)  tb.addEventListener('click', toggleTheme);
  if (mtb) mtb.addEventListener('click', toggleTheme);

  /* ── Desktop Product dropdown ───────────────────────────── */
  var wrap = id('prod-wrap'), menu = id('prod-menu'), btn = id('prod-btn'), chev = id('prod-chevron');
  var prodOpen = false;
  function openProd()  { prodOpen = true;  menu.style.display = ''; chev.style.transform = 'rotate(180deg)'; btn.setAttribute('aria-expanded','true'); }
  function closeProd() { prodOpen = false; menu.style.display = 'none'; chev.style.transform = ''; btn.setAttribute('aria-expanded','false'); }

  if (wrap) {
    wrap.addEventListener('mouseenter', openProd);
    wrap.addEventListener('mouseleave', closeProd);
    btn.addEventListener('click', function(e) { e.stopPropagation(); prodOpen ? closeProd() : openProd(); });
    document.addEventListener('click', function(e) { if (menu && !wrap.contains(e.target)) closeProd(); });
    document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeProd(); });
  }

  /* ── Mobile hamburger ───────────────────────────────────── */
  var mobileMenu = id('mobile-menu'), mobileBtn = id('mobile-btn');
  var hamIcon = id('icon-hamburger'), closeIcon = id('icon-close');
  var mobileOpen = false;
  if (mobileBtn) {
    mobileBtn.addEventListener('click', function() {
      mobileOpen = !mobileOpen;
      mobileMenu.style.display = mobileOpen ? '' : 'none';
      if (hamIcon)   hamIcon.style.display   = mobileOpen ? 'none' : '';
      if (closeIcon) closeIcon.style.display = mobileOpen ? '' : 'none';
    });
  }

  /* ── Mobile Product sub-menu ────────────────────────────── */
  var mobProdBtn = id('mob-prod-btn'), mobProdMenu = id('mob-prod-menu'), mobChev = id('mob-prod-chevron');
  var mobProdOpen = false;
  if (mobProdBtn) {
    mobProdBtn.addEventListener('click', function() {
      mobProdOpen = !mobProdOpen;
      mobProdMenu.style.display = mobProdOpen ? '' : 'none';
      if (mobChev) mobChev.style.transform = mobProdOpen ? 'rotate(180deg)' : '';
    });
  }

  /* ── Highlight.js ───────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function() {
    if (window.hljs) hljs.highlightAll();
  });
})();
