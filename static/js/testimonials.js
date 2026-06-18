function testimonials() {
  return {
    active: 0,
    total: 3,
    next: function() { this.active = (this.active + 1) % this.total; },
    prev: function() { this.active = (this.active - 1 + this.total) % this.total; },
  };
}
