import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listContactEngagement } from '../api/contacts';

const SCORE_LABEL = (score) => {
  if (score >= 20) return { label: 'Hot',      color: 'text-green-600 dark:text-green-400' };
  if (score >= 5)  return { label: 'Warm',     color: 'text-yellow-600 dark:text-yellow-400' };
  if (score >= 0)  return { label: 'Neutral',  color: 'text-gray-500' };
  return             { label: 'At risk',   color: 'text-red-500' };
};

function fmt(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function Contacts() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['contacts-engagement', page],
    queryFn: () => listContactEngagement({ page }).then(r => r.data),
    keepPreviousData: true,
    staleTime: 60_000,
  });

  const results = data?.results ?? [];
  const count   = data?.count ?? 0;
  const pageSize = 50;
  const totalPages = Math.max(1, Math.ceil(count / pageSize));

  return (
    <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-head)' }}>
              Contacts
            </h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Engagement scores for every contact you've emailed, sorted by score.
            </p>
          </div>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {count.toLocaleString()} contact{count !== 1 ? 's' : ''}
          </span>
        </div>

        {isError && (
          <div className="rounded-lg border border-red-300 bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400 mb-4">
            Failed to load contacts.
          </div>
        )}

        <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border)' }}>
          <table className="min-w-full text-sm">
            <thead>
              <tr style={{ background: 'var(--bg-table-head)', borderBottom: '1px solid var(--border)' }}>
                {['Email', 'Score', 'Opens', 'Clicks', 'Bounces', 'Complaints', 'Last Open', 'Last Click'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-semibold text-xs uppercase tracking-wide"
                      style={{ color: 'var(--text-muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && results.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                    No contacts yet. Send your first email to start tracking engagement.
                  </td>
                </tr>
              )}
              {results.map(c => {
                const { label, color } = SCORE_LABEL(c.score);
                return (
                  <tr key={c.email}
                      className="border-t transition-colors hover:opacity-90"
                      style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}>
                    <td className="px-4 py-3 font-medium" style={{ color: 'var(--text-head)' }}>
                      {c.email}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${color}`}>{c.score}</span>
                      <span className={`ml-1.5 text-xs ${color}`}>({label})</span>
                    </td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-body)' }}>{c.open_count}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-body)' }}>{c.click_count}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-body)' }}>{c.bounce_count}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-body)' }}>{c.complaint_count}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-muted)' }}>{fmt(c.last_open)}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-muted)' }}>{fmt(c.last_click)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40"
              style={{ borderColor: 'var(--border)', color: 'var(--text-body)' }}>
              Previous
            </button>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40"
              style={{ borderColor: 'var(--border)', color: 'var(--text-body)' }}>
              Next
            </button>
          </div>
        )}
    </div>
  );
}
