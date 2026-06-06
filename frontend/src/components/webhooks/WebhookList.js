import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listWebhooks, deleteWebhook, testWebhook } from '../../api/webhooks';

export default function WebhookList() {
  const qc = useQueryClient();

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => listWebhooks().then((r) => r.data.results ?? r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWebhook,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks'] }),
  });

  const testMutation = useMutation({ mutationFn: testWebhook });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;
  if (webhooks.length === 0) return <p className="text-sm text-gray-400">No webhooks configured.</p>;

  return (
    <div className="divide-y divide-gray-100">
      {webhooks.map((w) => (
        <div key={w.id} className="py-3 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-mono text-gray-800 truncate">{w.url}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {(w.event_types || []).join(', ')}
            </p>
          </div>
          <div className="flex gap-3 shrink-0">
            <button
              onClick={() => testMutation.mutate(w.id)}
              className="text-xs text-indigo-600 hover:underline"
            >
              Test
            </button>
            <button
              onClick={() => deleteMutation.mutate(w.id)}
              className="text-xs text-red-500 hover:underline"
            >
              Remove
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
