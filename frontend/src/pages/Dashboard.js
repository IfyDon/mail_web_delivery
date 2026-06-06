import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { getStats } from '../api/stats';
import client from '../api/client';
import { listMessages } from '../api/messages';
import { formatNumber, formatDateTime } from '../utils/formatters';
import AlertBanner from '../components/common/AlertBanner';

const METRICS = [
  { key: 'sent',       label: 'Sent',       color: 'text-blue-600',   hex: '#6366f1', link: '/messages' },
  { key: 'delivered',  label: 'Delivered',  color: 'text-green-600',  hex: '#22c55e', link: '/messages?status=delivered' },
  { key: 'opened',     label: 'Opened',     color: 'text-indigo-600', hex: '#8b5cf6', link: '/analytics' },
  { key: 'clicked',    label: 'Clicked',    color: 'text-purple-600', hex: '#f59e0b', link: '/analytics' },
  { key: 'bounced',    label: 'Bounced',    color: 'text-orange-500', hex: '#f97316', link: '/messages?status=bounced' },
  { key: 'complained', label: 'Complained', color: 'text-red-600',    hex: '#ef4444', link: '/suppressions' },
];

const RANGES = [
  { label: '7d',  value: '7d' },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
];

const CHART_SERIES = METRICS.filter((m) =>
  ['sent', 'delivered', 'opened', 'clicked'].includes(m.key)
);

const NOTIF_DEFAULTS = { bounce_warn: 5, bounce_alert: 10, complaint_warn: 0.05, complaint_alert: 0.1 };

function getNotifPrefs() {
  try { return { ...NOTIF_DEFAULTS, ...JSON.parse(localStorage.getItem('wm_notif_prefs') || '{}') }; }
  catch { return { ...NOTIF_DEFAULTS }; }
}

function healthColor(rate, warnThreshold, dangerThreshold) {
  if (rate >= dangerThreshold) return 'red';
  if (rate >= warnThreshold)   return 'amber';
  return 'green';
}

const HEALTH_STYLES = {
  green: { badge: 'bg-green-100 text-green-800', label: 'Healthy' },
  amber: { badge: 'bg-amber-100 text-amber-800', label: 'Warning' },
  red:   { badge: 'bg-red-100 text-red-800',     label: 'Danger'  },
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-medium text-gray-700 mb-2">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 text-gray-600">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: entry.color }} />
          <span className="capitalize">{entry.name}:</span>
          <span className="font-medium text-gray-900">{entry.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [range, setRange]   = useState('7d');
  const [stream, setStream] = useState('');

  const { data: streamsData } = useQuery({
    queryKey: ['streams'],
    queryFn: () => client.get('/streams/').then((r) => r.data.results ?? r.data),
    staleTime: 300_000,
  });
  const streams = streamsData ?? [];

  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', range, stream],
    queryFn: () => getStats({ date_range: range, ...(stream ? { stream } : {}) }).then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: messagesData, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', 'recent'],
    queryFn: () => listMessages({ page: 1, page_size: 10 }).then((r) => r.data),
    staleTime: 30_000,
  });

  const totals   = statsData?.totals        ?? {};
  const daily    = statsData?.daily         ?? [];
  const messages = messagesData?.results    ?? [];
  const bounceRate    = statsData?.bounce_rate    ?? 0;
  const complaintRate = statsData?.complaint_rate ?? 0;

  const prefs = getNotifPrefs();
  const bounceColor    = healthColor(bounceRate,    prefs.bounce_warn,    prefs.bounce_alert);
  const complaintColor = healthColor(complaintRate, prefs.complaint_warn, prefs.complaint_alert);
  const overallColor   = bounceColor === 'red' || complaintColor === 'red' ? 'red'
                       : bounceColor === 'amber' || complaintColor === 'amber' ? 'amber'
                       : 'green';

  return (
    <div className="space-y-6">

      {/* Header + filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <div className="flex flex-wrap items-center gap-2">
          {/* Stream filter */}
          <select
            value={stream}
            onChange={(e) => setStream(e.target.value)}
            className="border border-gray-300 rounded-md px-2 py-1 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All streams</option>
            {streams.map((s) => (
              <option key={s.id} value={s.slug ?? s.name}>{s.name}</option>
            ))}
          </select>
          {/* Date range */}
          <div className="flex gap-1 bg-gray-100 rounded-md p-1">
            {RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => setRange(r.value)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  range === r.value
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {METRICS.map(({ key, label, color, link }) => (
          <Link
            key={key}
            to={link}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all block"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${color}`}>
              {statsLoading ? '—' : formatNumber(totals[key] ?? 0)}
            </p>
          </Link>
        ))}
      </div>

      {/* Sending health card */}
      <div className={`rounded-lg border p-4 ${
        overallColor === 'red'   ? 'border-red-300 bg-red-50' :
        overallColor === 'amber' ? 'border-amber-300 bg-amber-50' :
        'border-green-300 bg-green-50'
      }`}>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium text-gray-800">Sending health</p>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${HEALTH_STYLES[overallColor].badge}`}>
            {HEALTH_STYLES[overallColor].label}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: 'Bounce rate',    rate: bounceRate,    color: bounceColor,    warn: prefs.bounce_warn,    danger: prefs.bounce_alert    },
            { label: 'Complaint rate', rate: complaintRate, color: complaintColor, warn: prefs.complaint_warn, danger: prefs.complaint_alert },
          ].map(({ label, rate, color }) => (
            <div key={label}>
              <p className="text-xs text-gray-500">{label}</p>
              <p className={`text-lg font-bold ${
                color === 'red' ? 'text-red-600' : color === 'amber' ? 'text-amber-600' : 'text-green-700'
              }`}>
                {statsLoading ? '—' : `${rate}%`}
              </p>
            </div>
          ))}
        </div>
        {overallColor === 'red' && (
          <div className="mt-3">
            <AlertBanner type="error">
              Your bounce rate exceeds the safe threshold.{' '}
              <Link to="/suppressions" className="underline font-medium">
                Review your suppression list →
              </Link>
            </AlertBanner>
          </div>
        )}
      </div>

      {/* Area chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <p className="text-sm font-medium text-gray-700 mb-4">Volume over time</p>
        {statsLoading ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : daily.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
            No data for this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={daily} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
              <defs>
                {CHART_SERIES.map(({ key, hex }) => (
                  <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={hex} stopOpacity={0.18} />
                    <stop offset="95%" stopColor={hex} stopOpacity={0.02} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {CHART_SERIES.map(({ key, hex }) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={hex}
                  strokeWidth={2}
                  fill={`url(#grad-${key})`}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Recent messages */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <p className="text-sm font-medium text-gray-700">Recent messages</p>
          <Link to="/messages" className="text-xs text-indigo-600 hover:underline">View all →</Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-2.5">To</th>
              <th className="px-4 py-2.5">Subject</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Sent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {messagesLoading ? (
              <tr><td colSpan={4} className="px-4 py-5 text-center text-gray-400">Loading…</td></tr>
            ) : messages.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-5 text-center text-gray-400">
                  No messages yet. Send your first email via the API.
                </td>
              </tr>
            ) : (
              messages.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-700">{m.to_address}</td>
                  <td className="px-4 py-2.5 text-gray-600 max-w-xs truncate">{m.subject}</td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(m.status)}`}>
                      {m.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap text-xs">
                    {formatDateTime(m.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
}
