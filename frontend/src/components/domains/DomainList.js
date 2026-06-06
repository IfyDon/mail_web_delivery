import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDomains, verifyDomain, deleteDomain } from '../../api/domains';
import { statusBadge } from '../../utils/formatters';

export default function DomainList() {
  const qc = useQueryClient();

  const { data: domains = [], isLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: () => listDomains().then((r) => r.data.results ?? r.data),
  });

  const verifyMutation = useMutation({
    mutationFn: verifyDomain,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['domains'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDomain,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['domains'] }),
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;
  if (domains.length === 0) return <p className="text-sm text-gray-400">No domains yet.</p>;

  return (
    <div className="divide-y divide-gray-100">
      {domains.map((d) => (
        <div key={d.id} className="py-3 flex items-center justify-between">
          <div>
            <p className="text-sm font-mono text-gray-800">{d.name}</p>
            <span
              className={`inline-flex mt-0.5 px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(
                d.verification_status
              )}`}
            >
              {d.verification_status}
            </span>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => verifyMutation.mutate(d.id)}
              className="text-xs text-indigo-600 hover:underline"
            >
              Verify
            </button>
            <button
              onClick={() => deleteMutation.mutate(d.id)}
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
