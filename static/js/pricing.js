function usageCalc() {
  function sliderToEmails(v) {
    if (v >= 100) return Infinity;
    var min = Math.log10(1000);
    var max = Math.log10(500001);
    return Math.round(Math.pow(10, min + (v / 100) * (max - min)));
  }
  function fmt(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000)    return Math.round(n / 1000) + 'K';
    return String(n);
  }
  var plans = [
    { max: 1000,     name: 'Developer',  cardId: 'plan-developer',  price: 'Free',        color: 'text-gray-700',   border: 'border-gray-300',  desc: 'Up to 1,000 emails free forever.' },
    { max: 50000,    name: 'Startup',    cardId: 'plan-startup',    price: '$29 / month', color: 'text-indigo-600', border: 'border-indigo-400', desc: 'Up to 50,000 emails per month.' },
    { max: Infinity, name: 'Enterprise', cardId: 'plan-enterprise', price: 'Custom',       color: 'text-gray-700',   border: 'border-gray-400',  desc: 'Unlimited sends — volume pricing for high senders.' },
  ];

  var allCardIds = plans.map(function(p) { return p.cardId; });

  function highlightCard(activeId) {
    allCardIds.forEach(function(id) {
      var el = document.getElementById(id);
      if (!el) return;
      var badge = el.querySelector('.your-plan-badge');
      if (id === activeId) {
        el.classList.add('ring-4', 'ring-emerald-400', 'ring-offset-2', 'shadow-2xl');
        if (badge) {
          badge.classList.remove('opacity-0', 'scale-0');
          badge.classList.add('opacity-100', 'scale-100');
        }
      } else {
        el.classList.remove('ring-4', 'ring-emerald-400', 'ring-offset-2', 'shadow-2xl');
        if (badge) {
          badge.classList.add('opacity-0', 'scale-0');
          badge.classList.remove('opacity-100', 'scale-100');
        }
      }
    });
  }

  return {
    sliderVal: 10,
    emailsLabel: '1K',
    planName: 'Developer', planPrice: 'Free',
    planColor: 'text-gray-700', planBorder: 'border-2 border-gray-300',
    planDesc: 'Up to 1,000 emails free forever.',
    compute: function() {
      var emails = sliderToEmails(parseInt(this.sliderVal));
      this.emailsLabel = emails === Infinity ? 'Unlimited' : fmt(emails);
      var plan = plans.find(function(p) { return emails <= p.max; }) || plans[plans.length - 1];
      this.planName   = plan.name;
      this.planPrice  = plan.price;
      this.planColor  = plan.color;
      this.planBorder = 'border-2 ' + plan.border;
      this.planDesc   = plan.desc;
      highlightCard(plan.cardId);
    },
    init: function() { this.compute(); },
  };
}
