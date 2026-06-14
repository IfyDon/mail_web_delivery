// Anti-FOUC: apply saved theme before anything paints
(function(){
  var t = localStorage.getItem('wm_theme') ||
          (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', t);
})();

// Alpine store init — must run before alpine.js loads
document.addEventListener('alpine:init', function() {
  Alpine.store('theme', {
    dark: document.documentElement.getAttribute('data-theme') === 'dark',
    toggle: function() {
      this.dark = !this.dark;
      var t = this.dark ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', t);
      try { localStorage.setItem('wm_theme', t); } catch(e) {}
    }
  });
});
