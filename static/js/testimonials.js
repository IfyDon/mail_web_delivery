(function () {
  var TOTAL = 5;
  var active = 0;

  function init() {
    var track = document.getElementById('testimonials-track');
    var dotsWrap = document.getElementById('testimonials-dots');
    var prevBtn = document.getElementById('testimonials-prev');
    var nextBtn = document.getElementById('testimonials-next');

    if (!track) return; // carousel not on this page

    // Build dots — p-2 -m-2 expands tap target to 48px without altering visual size
    for (var i = 0; i < TOTAL; i++) {
      var dot = document.createElement('button');
      dot.className = 'p-2 -m-2';
      dot.setAttribute('aria-label', 'Go to testimonial ' + (i + 1));
      var inner = document.createElement('span');
      inner.className = 'block h-2 rounded-full transition-all duration-300';
      dot.appendChild(inner);
      dotsWrap.appendChild(dot);
      (function (idx) {
        dot.addEventListener('click', function () { goTo(idx); });
      }(i));
    }

    function goTo(n) {
      active = n;
      track.style.transform = 'translateX(-' + (active * 100) + '%)';
      var dots = dotsWrap.querySelectorAll('button');
      dots.forEach(function (d, i) {
        var inner = d.querySelector('span');
        if (inner) inner.className = 'block h-2 rounded-full transition-all duration-300 ' +
          (i === active ? 'bg-indigo-600 w-6' : 'bg-gray-300 w-2');
      });
    }

    prevBtn.addEventListener('click', function () { goTo((active - 1 + TOTAL) % TOTAL); });
    nextBtn.addEventListener('click', function () { goTo((active + 1) % TOTAL); });

    goTo(0); // set initial dot state
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
