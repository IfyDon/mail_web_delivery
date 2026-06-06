import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { listMessages } from '../api/messages';
import { formatDateTime } from '../utils/formatters';
import EmptyState from '../components/common/EmptyState';

const STATUSES = [
  'queued', 'sent', 'delivered', 'failed', 'permanently_failed', 'suppressed',
];

const STATUS_CONFIG = {
  delivered:         { bg: 'bg-green-100 text-green-800',  dot: 'bg-green-500',  label: 'Delivered' },
  sent:              { bg: 'bg-blue-100 text-blue-800',    dot: 'bg-blue-500',   label: 'Sent' },
  queued:            { bg: 'bg-yellow-100 text-yellow-800',dot: 'bg-yellow-500', label: 'Queued' },
  failed:            { bg: 'bg-red-100 text-red-800',      dot: 'bg-red-500',    label: 'Failed' },
  permanently_failed:{ bg: 'bg-red-100 text-red-800',      dot: 'bg-red-600',    label: 'Perm. Failed' },
  suppressed:        { bg: 'bg-gray-100 text-gray-600',    dot: 'bg-gray-400',   label: 'Suppressed' },
  bounced:           { bg: 'bg-red-100 text-red-800',      dot: 'bg-red-500',    label: 'Bounced' },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? { bg: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400', label: status };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg}`}>
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

export default function Messages() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const status   = searchParams.get('status')    ?? '';
  const domain   = searchParams.get('domain')    ?? '';
  const dateFrom = searchParams.get('date_from') ?? '';
  const dateTo   = searchParams.get('date_to')   ?? '';
  const page     = parseInt(searchParams.get('page') ?? '1', 10);

  function setParam(key, value) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value); else next.delete(key);
      next.delete('page');
      return next;
    });
  }

  function setPage(n) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (n === 1) next.delete('page'); else next.set('page', String(n));
      return next;
    });
  }

  function resetFilters() {
    setSearchParams({});
  }

  const params = {
    page,
    ...(status   ? { status }              : {}),
    ...(domain   ? { domain }              : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo   ? { date_to: dateTo }     : {}),
  };

  const { data, isLoading } = useQuery({
    queryKey: ['messages', params],
    queryFn: () => listMessages(params).then((r) => r.data),
    placeholderData: (prev) => prev,
  });

  const messages   = data?.results ?? [];
  const total      = data?.count ?? 0;
  const totalPages = Math.ceil(total / 50);
  const hasFilters = status || domain || dateFrom || dateTo;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Messages</h1>
        <span className="text-sm text-gray-400">{total.toLocaleString()} total</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Status</label>
          <select
            value={status}
            onChange={(e) => setParam('status', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_CONFIG[s]?.label ?? s}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Domain</label>
          <input
            type="text"
            value={domain}
            onChange={(e) => setParam('domain', e.target.value)}
            placeholder="e.g. example.com"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-44 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setParam('date_from', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setParam('date_to', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {hasFilters && (
          <button
            onClick={resetFilters}
            className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Clear filters
          </button>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">To</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 whitespace-nowrap">Sent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">Loading…</td>
              </tr>
            ) : messages.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  {hasFilters ? (
                    <div className="px-4 py-8 text-center text-gray-400">
                      No messages match your filters.{' '}
                      <button onClick={resetFilters} className="underline hover:text-gray-600">
                        Clear filters
                      </button>
                    </div>
                  ) : (
                    <EmptyState
                      icon="📭"
                      title="No messages yet"
                      description="Send your first email using the API and it will appear here."
                      action={
                        <code className="block text-left bg-gray-900 text-green-400 rounded-lg px-4 py-3 text-xs font-mono max-w-sm">
                          {`curl -X POST /api/v1/send \\\n  -H "Authorization: Bearer <key>"`}
                        </code>
                      }
                    />
                  )}
                </td>
              </tr>
            ) : (
              messages.map((m) => (
                <tr
                  key={m.id}
                  onClick={() => navigate(`/messages/${m.id}`)}
                  className="hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-4 py-3 text-gray-700 font-mono text-xs">{m.to_address}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{m.subject}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={m.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                    {formatDateTime(m.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Prev
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
