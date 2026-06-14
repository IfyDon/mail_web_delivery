import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listWebhooks, createWebhook, deleteWebhook, testWebhook,
  updateWebhook, getWebhookLogs, retryWebhook,
} from '../api/webhooks';
import { formatDateTime, formatRelative } from '../utils/formatters';
import EmptyState from '../components/common/EmptyState';

const EVENT_TYPES = [
  'delivered', 'open', 'click', 'bounce', 'complaint', 'permanently_failed',
];

function statusCode(code) {
  if (!code) return <span className="text-gray-400">—</span>;
  const ok = code >= 200 && code < 300;
  return (
    <span className={`font-mono text-xs font-semibold ${ok ? 'text-green-700' : 'text-red-600'}`}>
      {code}
    </span>
  );
}

function DispatchLog({ webhookId }) {
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['webhook-logs', webhookId],
    queryFn: () => getWebhookLogs(webhookId).then((r) => r.data),
    staleTime: 30_000,
  });

  const qc = useQueryClient();
  const retryMutation = useMutation({
    mutationFn: () => retryWebhook(webhookId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhook-logs', webhookId] }),
  });

  if (isLoading) return <p className="px-4 py-3 text-xs text-gray-400">Loading logs…</p>;
  if (logs.length === 0) return <p className="px-4 py-3 text-xs text-gray-400">No dispatch history yet.</p>;

  const hasFailure = logs.some((l) => !l.succeeded);

  return (
    <div className="border-t border-gray-100 bg-gray-50">
      <div className="flex items-center justify-between px-4 py-2">
        <p className="text-xs font-medium text-gray-600">Last {logs.length} dispatches</p>
        {hasFailure && (
          <button
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
            className="text-xs text-indigo-600 hover:underline disabled:opacity-40"
          >
            {retryMutation.isPending ? 'Retrying…' : 'Retry last failed'}
          </button>
        )}
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-gray-400 uppercase tracking-wide border-b border-gray-200">
            <th className="px-4 py-1.5">Time</th>
            <th className="px-4 py-1.5">Event</th>
            <th className="px-4 py-1.5">Status</th>
            <th className="px-4 py-1.5">Attempts</th>
            <th className="px-4 py-1.5">Response (truncated)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {logs.map((log) => (
            <tr key={log.id} className={log.succeeded ? '' : 'bg-red-50'}>
              <td className="px-4 py-1.5 text-gray-500 whitespace-nowrap">
                {formatDateTime(log.last_attempted_at ?? log.created_at)}
              </td>
              <td className="px-4 py-1.5 text-gray-700">{log.event_type}</td>
              <td className="px-4 py-1.5">{statusCode(log.response_status)}</td>
              <td className="px-4 py-1.5 text-gray-600">{log.attempts}</td>
              <td className="px-4 py-1.5 font-mono text-gray-500 max-w-xs truncate">
                {log.response_body ? log.response_body.slice(0, 200) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Webhooks() {
  const qc = useQueryClient();
  const [url, setUrl]               = useState('');
  const [selectedEvents, setSelectedEvents] = useState(['delivered', 'bounce']);
  const [error, setError]           = useState('');
  const [tested, setTested]         = useState(null);
  const [expanded, setExpanded]     = useState(null);

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => listWebhooks().then((r) => r.data.results ?? r.data),
  });

  const createMutation = useMutation({
    mutationFn: () => createWebhook({ url, event_types: selectedEvents }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['webhooks'] });
      setUrl('');
      setError('');
    },
    onError: (err) => setError(err.response?.data?.url?.[0] ?? 'Failed to add webhook.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWebhook,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks'] }),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }) => updateWebhook(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks'] }),
  });

  const testMutation = useMutation({
    mutationFn: testWebhook,
    onSuccess: (_, id) => {
      setTested(id);
      setTimeout(() => setTested(null), 3000);
    },
  });

  const toggleEvent = (evt) =>
    setSelectedEvents((prev) =>
      prev.includes(evt) ? prev.filter((e) => e !== evt) : [...prev, evt]
    );

  const toggleExpanded = (id) => setExpanded((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Webhooks</h1>

      {/* Add form */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <p className="text-sm font-medium text-gray-700">Add endpoint</p>
        <form
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }}
          className="space-y-3"
        >
          <input
            type="url"
            placeholder="https://your-server.com/webhook"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
          <div className="flex flex-wrap gap-3">
            {EVENT_TYPES.map((evt) => (
              <label key={evt} className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedEvents.includes(evt)}
                  onChange={() => toggleEvent(evt)}
                  className="rounded text-indigo-600"
                />
                {evt}
              </label>
            ))}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            Add webhook
          </button>
        </form>
      </div>

      {/* Webhook list */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden divide-y divide-gray-100">
        {isLoading ? (
          <p className="px-4 py-6 text-center text-gray-400 text-sm">Loading…</p>
        ) : webhooks.length === 0 ? (
          <EmptyState
            icon="🔔"
            title="No webhooks configured"
            description="Add a webhook URL to receive real-time event notifications for every delivery, open, click, bounce, and complaint."
          />
        ) : (
          webhooks.map((w) => {
            const isOpen = expanded === w.id;
            return (
              <div key={w.id}>
                {/* Row */}
                <div className="flex flex-wrap items-center gap-3 px-4 py-3">
                  {/* URL + events */}
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-xs text-gray-800 truncate">{w.url}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{(w.event_types || []).join(', ')}</p>
                  </div>

                  {/* Status badge */}
                  <span className={`shrink-0 inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                    w.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {w.is_active ? 'Active' : 'Inactive'}
                  </span>

                  {/* Last attempted */}
                  <span className="shrink-0 text-xs text-gray-400 whitespace-nowrap">
                    {w.last_attempted_at ? formatDateTime(w.last_attempted_at) : 'Never fired'}
                  </span>

                  {/* Actions */}
                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      onClick={() => testMutation.mutate(w.id)}
                      disabled={testMutation.isPending || !w.is_active}
                      className="text-indigo-600 hover:underline text-xs disabled:opacity-40"
                    >
                      {tested === w.id ? 'Sent ✓' : 'Test'}
                    </button>
                    <button
                      onClick={() => toggleActiveMutation.mutate({ id: w.id, is_active: !w.is_active })}
                      disabled={toggleActiveMutation.isPending}
                      className="text-gray-500 hover:text-gray-800 text-xs disabled:opacity-40"
                    >
                      {w.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => toggleExpanded(w.id)}
                      className="text-xs text-gray-500 hover:text-gray-800"
                    >
                      {isOpen ? 'Hide logs ▲' : 'Show logs ▼'}
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(w.id)}
                      className="text-red-500 hover:underline text-xs"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {/* Expandable dispatch log */}
                {isOpen && <DispatchLog webhookId={w.id} />}
              </div>
            );
          })
        )}
      </div>

      <p className="text-xs text-gray-400 px-1">
        Failed deliveries are retried up to 10 times with exponential backoff.
      </p>
    </div>
  );
}
