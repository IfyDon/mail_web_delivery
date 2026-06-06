import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMessage, resendMessage } from '../api/messages';
import { formatDateTime, statusBadge } from '../utils/formatters';

const EVENT_ICONS = {
  delivered:   { icon: '✓', color: 'text-green-600' },
  open:        { icon: '👁', color: 'text-indigo-600' },
  click:       { icon: '🔗', color: 'text-purple-600' },
  bounce:      { icon: '↩', color: 'text-orange-500' },
  complaint:   { icon: '⚠', color: 'text-red-500'   },
  unsubscribe: { icon: '✗', color: 'text-gray-500'   },
};

export default function MessageDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [bodyTab, setBodyTab]         = useState('html');
  const [headersOpen, setHeadersOpen] = useState(false);
  const [resendDone, setResendDone]   = useState(false);

  const { data: message, isLoading, isError } = useQuery({
    queryKey: ['message', id],
    queryFn: () => getMessage(id).then((r) => r.data),
  });

  const resendMutation = useMutation({
    mutationFn: () => resendMessage(id),
    onSuccess: () => {
      setResendDone(true);
      qc.invalidateQueries({ queryKey: ['message', id] });
      qc.invalidateQueries({ queryKey: ['messages'] });
    },
  });

  if (isLoading) return <div className="text-sm text-gray-400 p-4">Loading…</div>;
  if (isError || !message) {
    return (
      <div className="text-sm text-red-600 p-4">
        Message not found.{' '}
        <button onClick={() => navigate('/messages')} className="underline">Back</button>
      </div>
    );
  }

  const events  = message.events ?? [];
  const headers = message.headers ?? message.raw_headers ?? null;
  const isPermanentlyFailed = message.status === 'permanently_failed';

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 truncate max-w-lg">
          {message.subject}
        </h1>
        <div className="flex items-center gap-3 shrink-0">
          {isPermanentlyFailed && (
            <button
              onClick={() => resendMutation.mutate()}
              disabled={resendMutation.isPending || resendDone}
              className="bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {resendDone ? 'Re-queued ✓' : resendMutation.isPending ? 'Resending…' : 'Resend'}
            </button>
          )}
          <button
            onClick={() => navigate('/messages')}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← Back
          </button>
        </div>
      </div>

      {/* Metadata card */}
      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100 text-sm">
        {[
          { label: 'To',     value: message.to_address },
          { label: 'From',   value: message.from_address },
          { label: 'Status', value: (
            <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(message.status)}`}>
              {message.status}
            </span>
          )},
          { label: 'Stream', value: message.stream ?? '—' },
          { label: 'Domain', value: message.domain ?? '—' },
          { label: 'Sent',   value: message.created_at ? formatDateTime(message.created_at) : '—' },
          { label: 'ID',     value: <code className="text-xs font-mono text-gray-500">{message.id}</code> },
        ].map(({ label, value }) => (
          <div key={label} className="flex gap-4 px-4 py-2.5">
            <span className="text-gray-500 w-16 shrink-0">{label}</span>
            <span className="text-gray-800 break-all">{value}</span>
          </div>
        ))}
      </div>

      {/* Event timeline */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <p className="text-sm font-medium text-gray-700">Event timeline</p>
        </div>
        {events.length === 0 ? (
          <p className="px-4 py-5 text-sm text-gray-400">No events recorded yet.</p>
        ) : (
          <ol className="divide-y divide-gray-100">
            {events.map((ev, i) => {
              const { icon, color } = EVENT_ICONS[ev.type] ?? { icon: '·', color: 'text-gray-400' };
              return (
                <li key={i} className="flex items-start gap-3 px-4 py-3">
                  <span className={`mt-0.5 text-base w-5 text-center shrink-0 ${color}`}>{icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800 capitalize">{ev.type}</span>
                      <span className="text-xs text-gray-400">{formatDateTime(ev.timestamp)}</span>
                    </div>
                    {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                      <dl className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                        {Object.entries(ev.metadata).map(([k, v]) => (
                          <div key={k} className="flex gap-1 text-xs text-gray-500 col-span-2">
                            <dt className="font-medium shrink-0">{k}:</dt>
                            <dd className="truncate">{String(v)}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      {/* Body preview with HTML / plain-text tab toggle */}
      {(message.html_body || message.text_body) && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700">Email preview</p>
            <div className="flex gap-1 bg-gray-100 rounded p-0.5">
              {['html', 'text'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setBodyTab(tab)}
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    bodyTab === tab ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
                  }`}
                >
                  {tab === 'html' ? 'HTML' : 'Plain text'}
                </button>
              ))}
            </div>
          </div>
          {bodyTab === 'html' && message.html_body ? (
            <iframe
              srcDoc={message.html_body}
              sandbox="allow-same-origin"
              title="Email body"
              className="w-full border-0"
              style={{ height: 400 }}
            />
          ) : (
            <pre className="px-4 py-4 text-xs text-gray-700 whitespace-pre-wrap font-mono overflow-auto max-h-96">
              {message.text_body || '(no plain-text body)'}
            </pre>
          )}
        </div>
      )}

      {/* Raw headers (collapsible) */}
      {headers && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setHeadersOpen((o) => !o)}
            className="w-full flex items-center justify-between px-4 py-3 border-b border-gray-100 text-left"
          >
            <p className="text-sm font-medium text-gray-700">Raw headers</p>
            <span className="text-xs text-gray-400">{headersOpen ? '▲ Hide' : '▼ Show'}</span>
          </button>
          {headersOpen && (
            <pre className="px-4 py-4 text-xs text-gray-600 font-mono whitespace-pre-wrap overflow-auto max-h-64">
              {typeof headers === 'object' ? JSON.stringify(headers, null, 2) : headers}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
