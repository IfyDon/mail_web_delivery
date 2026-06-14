import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { listTemplates, deleteTemplate } from '../../api/templates';
import { formatDate } from '../../utils/formatters';

export default function TemplateList() {
  const qc = useQueryClient();

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: () => listTemplates().then((r) => r.data.results ?? r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTemplate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;
  if (templates.length === 0) return <p className="text-sm text-gray-400">No templates yet.</p>;

  return (
    <div className="divide-y divide-gray-100">
      {templates.map((t) => (
        <div key={t.id} className="py-3 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900">{t.name}</p>
            <p className="text-xs text-gray-500">{t.subject} · {formatDate(t.created_at)}</p>
          </div>
          <div className="flex gap-3">
            <Link to={`/templates/${t.id}`} className="text-xs text-indigo-600 hover:underline">
              Edit
            </Link>
            <button
              onClick={() => deleteMutation.mutate(t.id)}
              className="text-xs text-red-500 hover:underline"
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
