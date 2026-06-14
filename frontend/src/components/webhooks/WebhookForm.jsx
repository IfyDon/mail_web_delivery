import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createWebhook } from '../../api/webhooks';

const EVENT_TYPES = [
  'delivered', 'open', 'click', 'bounce', 'complaint', 'permanently_failed',
];

export default function WebhookForm() {
  const qc = useQueryClient();
  const [url, setUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState(['delivered', 'bounce']);
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => createWebhook({ url, event_types: selectedEvents }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['webhooks'] });
      setUrl('');
      setError('');
    },
    onError: (err) => setError(err.response?.data?.url?.[0] || 'Failed.'),
  });

  const toggle = (evt) =>
    setSelectedEvents((prev) =>
      prev.includes(evt) ? prev.filter((e) => e !== evt) : [...prev, evt]
    );

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
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
              onChange={() => toggle(evt)}
              className="rounded text-indigo-600"
            />
            {evt}
          </label>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
      >
        Add webhook
      </button>
    </form>
  );
}
