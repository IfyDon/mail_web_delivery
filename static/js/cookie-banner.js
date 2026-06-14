function cookieBanner() {
  return {
    visible: false,
    prefs: { performance: true, functional: true, targeting: false },
    init() {
      try { if (!localStorage.getItem('wm_cookie_consent')) this.visible = true; }
      catch (_) { this.visible = true; }
    },
    acceptAll() {
      this.prefs = { performance: true, functional: true, targeting: true };
      this._persist();
    },
    reject() {
      this.prefs = { performance: false, functional: false, targeting: false };
      this._persist();
    },
    save() { this._persist(); },
    _persist() {
      try {
        localStorage.setItem('wm_cookie_consent', JSON.stringify({
          ts: Date.now(), strictly_necessary: true, ...this.prefs,
        }));
      } catch (_) {}
      this.visible = false;
    },
  };
}
