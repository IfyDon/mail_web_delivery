import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';
import { formatNumber } from '../utils/formatters';

const listStreams   = () => client.get('/streams/').then((r) => r.data.results ?? r.data);
const createStream  = (data) => client.post('/streams/', data);
const deleteStream  = (id) => client.delete(`/streams/${id}/`);

const STREAM_HELP = {
  transactional: 'Order confirmations, password resets, account notifications — highest deliverability priority.',
  promotional:   'Newsletters and marketing campaigns — isolated from transactional IP pools.',
};

// Postmark thresholds: bounce ≥10% danger, ≥5% warn; complaint ≥0.1% danger, ≥0.05% warn
function rateColor(rate, warn, danger) {
  if (rate === null || rate === undefined) return null;
  if (rate >= danger) return 'red';
  if (rate >= warn)   return 'amber';
  return 'green';
}

const BADGE = {
  green: 'bg-green-100 text-green-800',
  amber: 'bg-amber-100 text-amber-800',
  red:   'bg-red-100 text-red-800',
};

function RateBadge({ label, rate, warn, danger }) {
  if (rate === null || rate === undefined) return <span className="text-gray-400 text-xs">—</span>;
  const color = rateColor(rate, warn, danger);
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${BADGE[color]}`}
      title={color === 'red' ? 'Sending may be suspended if this rate is not reduced.' : undefined}
    >
      {rate}% {label}
    </span>
  );
}

export default function Streams() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName]   = useState('');
  const [newType, setNewType]   = useState('transactional');
  const [formError, setFormError] = useState('');

  const { data: streams = [], isLoading } = useQuery({
    queryKey: ['streams'],
    queryFn: listStreams,
  });

  const createMutation = useMutation({
    mutationFn: () => createStream({ name: newName, stream_type: newType }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['streams'] });
      setShowForm(false);
      setNewName('');
      setNewType('transactional');
      setFormError('');
    },
    onError: (err) => setFormError(err.response?.data?.detail ?? 'Failed to create stream.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStream,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['streams'] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Streams</h1>
        <button
          onClick={() => { setShowForm((v) => !v); setFormError(''); }}
          className="bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-md hover:bg-indigo-700"
        >
          {showForm ? 'Cancel' : '+ Create stream'}
        </button>
      </div>

      <p className="text-sm text-gray-500 max-w-xl">
        Streams isolate transactional and promotional email flows onto different IP pools,
        protecting your sender reputation.
      </p>

      {/* Create form */}
      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-gray-700">New stream</p>
          <div className="flex flex-wrap gap-3">
            <input
              type="text"
              placeholder="Stream name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-48"
            />
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="border border-gray-300 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="transactional">Transactional</option>
              <option value="promotional">Promotional</option>
            </select>
            <button
              onClick={() => createMutation.mutate()}
              disabled={!newName || createMutation.isPending}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
            >
              {createMutation.isPending ? 'Creating…' : 'Create'}
            </button>
          </div>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : streams.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-6 text-sm text-gray-400">
          No streams found. Streams are created automatically when you send your first email,
          or you can create one above.
        </div>
      ) : (
        <div className="space-y-3">
          {streams.map((s) => {
            const bounceRate    = s.bounce_rate    ?? null;
            const complaintRate = s.complaint_rate ?? null;
            const bColor = rateColor(bounceRate,    5,    10);
            const cColor = rateColor(complaintRate, 0.05, 0.1);

            return (
              <div
                key={s.id}
                className={`bg-white border rounded-lg p-5 ${
                  bColor === 'red' || cColor === 'red'
                    ? 'border-red-300'
                    : bColor === 'amber' || cColor === 'amber'
                    ? 'border-amber-300'
                    : 'border-gray-200'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 capitalize">{s.name}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-mono">
                      {s.slug ?? s.name}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      s.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {s.is_active !== false ? 'Active' : 'Paused'}
                    </span>
                    {bounceRate !== null && (
                      <RateBadge label="bounce" rate={bounceRate} warn={5} danger={10} />
                    )}
                    {complaintRate !== null && (
                      <RateBadge label="complaint" rate={complaintRate} warn={0.05} danger={0.1} />
                    )}
                  </div>
                  <button
                    onClick={() => {
                      if (window.confirm(`Archive stream "${s.name}"?`)) {
                        deleteMutation.mutate(s.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                    className="text-xs text-red-500 hover:underline disabled:opacity-40"
                  >
                    Archive
                  </button>
                </div>

                <p className="text-sm text-gray-500 mb-3">
                  {STREAM_HELP[s.name?.toLowerCase()] ?? s.description ?? ''}
                </p>

                {(bColor === 'red' || cColor === 'red') && (
                  <p className="mb-3 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded px-3 py-1.5">
                    Sending may be suspended if this rate is not reduced. Review your suppression list.
                  </p>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    { label: 'Sent (30d)',       value: s.sent_30d    ?? s.stats?.sent      ?? '—' },
                    { label: 'Delivered (30d)',   value: s.delivered_30d ?? s.stats?.delivered ?? '—' },
                    { label: 'Bounce rate',      value: bounceRate    !== null ? `${bounceRate}%`    : '—' },
                    { label: 'Complaint rate',   value: complaintRate !== null ? `${complaintRate}%` : '—' },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <p className="text-xs text-gray-400">{label}</p>
                      <p className="text-lg font-semibold text-gray-800">
                        {typeof value === 'number' ? formatNumber(value) : value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
