import { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { useStats } from '../hooks/useStats';
import { exportStats } from '../api/stats';
import client from '../api/client';
import { formatNumber } from '../utils/formatters';

const RANGES = [
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
];

const SERIES = [
  { key: 'sent',       color: '#6366f1' },
  { key: 'delivered',  color: '#22c55e' },
  { key: 'opened',     color: '#8b5cf6' },
  { key: 'clicked',    color: '#f59e0b' },
  { key: 'bounced',    color: '#f97316' },
  { key: 'complained', color: '#ef4444' },
];

export default function Analytics() {
  const [range, setRange]   = useState('7d');
  const [stream, setStream] = useState('');
  const [exporting, setExporting] = useState(false);

  const { data: streamsData } = useQuery({
    queryKey: ['streams'],
    queryFn: () => client.get('/streams/').then((r) => r.data.results ?? r.data),
    staleTime: 300_000,
  });
  const streams = streamsData ?? [];

  const { data, isLoading } = useStats(range, stream);
  const chartData = data?.daily  ?? [];
  const totals    = data?.totals ?? {};

  async function handleExport() {
    setExporting(true);
    try {
      const res = await exportStats({ date_range: range, ...(stream ? { stream } : {}) });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `stats_${range}${stream ? `_${stream}` : ''}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Analytics</h1>
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
          <button
            onClick={handleExport}
            disabled={exporting || isLoading}
            className="px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        {SERIES.map(({ key, color }) => (
          <div key={key} className="bg-white border border-gray-200 rounded-lg p-3">
            <p className="text-xs text-gray-500 capitalize">{key}</p>
            <p className="text-xl font-semibold mt-0.5" style={{ color }}>
              {isLoading ? '—' : formatNumber(totals[key] ?? 0)}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-sm font-medium text-gray-700 mb-4">Email volume</p>
        {isLoading ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : chartData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
            No data for this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              {SERIES.map(({ key, color }) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  fill={color}
                  fillOpacity={0.08}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
