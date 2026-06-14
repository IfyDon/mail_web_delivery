import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getBillingOverview,
  getInvoices,
  createCheckoutSession,
  createPortalSession,
} from '../api/billing';
import { formatNumber, formatDate } from '../utils/formatters';

export default function Billing() {
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const [portalLoading, setPortalLoading] = useState(false);

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['billing-overview'],
    queryFn: () => getBillingOverview().then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: invoices = [] } = useQuery({
    queryKey: ['billing-invoices'],
    queryFn: () => getInvoices().then((r) => r.data),
    staleTime: 120_000,
  });

  const subscription = overview?.subscription ?? null;
  const usage = overview?.usage ?? { sent: 0, limit: 1000, percent: 0 };
  const plans = overview?.plans ?? [];
  const currentSlug = subscription?.plan?.slug ?? 'free';

  const pct = usage.percent;
  const barColor =
    pct >= 95 ? 'bg-red-500' :
    pct >= 80 ? 'bg-orange-400' :
    'bg-indigo-500';

  async function handleUpgrade(planSlug) {
    setCheckoutLoading(planSlug);
    try {
      const res = await createCheckoutSession(planSlug);
      window.location.href = res.data.checkout_url;
    } catch (err) {
      console.error('Checkout error:', err);
      setCheckoutLoading(null);
    }
  }

  async function handleManage() {
    setPortalLoading(true);
    try {
      const res = await createPortalSession();
      window.location.href = res.data.portal_url;
    } catch (err) {
      console.error('Portal error:', err);
      setPortalLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Billing</h1>
        {subscription?.stripe_subscription_id && (
          <button
            onClick={handleManage}
            disabled={portalLoading}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40"
          >
            {portalLoading ? 'Redirecting…' : 'Manage subscription'}
          </button>
        )}
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {overviewLoading ? (
          <div className="col-span-3 text-sm text-gray-400 py-6 text-center">Loading…</div>
        ) : (
          plans.map((plan) => {
            const isCurrent = plan.slug === currentSlug;
            const isFree = plan.slug === 'free';
            return (
              <div
                key={plan.slug}
                className={`bg-white border rounded-lg p-5 space-y-3 ${
                  isCurrent ? 'border-indigo-400 ring-1 ring-indigo-400' : 'border-gray-200'
                }`}
              >
                {isCurrent && (
                  <span className="inline-flex text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                    Current plan
                  </span>
                )}
                <p className="font-semibold text-gray-900">{plan.name}</p>
                <p className="text-2xl font-bold text-gray-800">
                  {plan.price_monthly === '0.00' ? '$0' : `$${plan.price_monthly}`}
                  {plan.price_monthly !== '0.00' && (
                    <span className="text-sm font-normal text-gray-500">/mo</span>
                  )}
                </p>
                <p className="text-sm text-gray-500">
                  {plan.email_limit
                    ? `${formatNumber(plan.email_limit)} emails / mo`
                    : 'Unlimited emails'}
                </p>
                {plan.features?.length > 0 && (
                  <ul className="text-xs text-gray-500 space-y-1">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-1.5">
                        <span className="text-green-500">✓</span> {f}
                      </li>
                    ))}
                  </ul>
                )}
                <button
                  disabled={isCurrent || isFree || checkoutLoading === plan.slug}
                  onClick={() => !isCurrent && !isFree && handleUpgrade(plan.slug)}
                  className={`w-full border rounded-md py-1.5 text-sm font-medium transition-colors ${
                    isCurrent
                      ? 'border-gray-200 text-gray-400 cursor-default'
                      : isFree
                      ? 'border-gray-200 text-gray-400 cursor-default'
                      : 'border-indigo-600 text-indigo-600 hover:bg-indigo-50 disabled:opacity-40'
                  }`}
                >
                  {isCurrent
                    ? 'Current plan'
                    : checkoutLoading === plan.slug
                    ? 'Redirecting…'
                    : 'Upgrade'}
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Usage */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-3">
        <p className="text-sm font-medium text-gray-700">Usage this billing period</p>
        {overviewLoading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : (
          <>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">
                <span className="font-semibold text-gray-900">{formatNumber(usage.sent)}</span>
                {usage.limit
                  ? ` of ${formatNumber(usage.limit)} emails sent`
                  : ' emails sent'}
              </span>
              {usage.limit > 0 && (
                <span className={`font-medium text-sm ${pct >= 80 ? 'text-orange-600' : 'text-gray-500'}`}>
                  {pct}%
                </span>
              )}
            </div>
            {usage.limit > 0 && (
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${barColor}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            )}
            {pct >= 80 && pct < 100 && (
              <p className="text-xs text-orange-600">
                Approaching monthly limit — consider upgrading to avoid interruption.
              </p>
            )}
            {pct >= 100 && (
              <p className="text-xs text-red-600 font-medium">
                Monthly limit reached — new sends are blocked. Please upgrade.
              </p>
            )}
            {subscription?.current_period_end && (
              <p className="text-xs text-gray-400">
                Resets on {formatDate(subscription.current_period_end)}
              </p>
            )}
          </>
        )}
      </div>

      {/* Invoice history */}
      {invoices.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700">Invoice history</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-2">Date</th>
                <th className="px-4 py-2">Amount</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {invoices.map((inv) => (
                <tr key={inv.stripe_invoice_id}>
                  <td className="px-4 py-2.5 text-gray-600">
                    {inv.created_at ? formatDate(inv.created_at) : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-gray-800 font-medium">
                    {inv.amount_display}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      inv.status === 'paid'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {inv.pdf_url && (
                      <a
                        href={inv.pdf_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-indigo-600 hover:underline"
                      >
                        PDF
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
