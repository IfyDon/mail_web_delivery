import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getTemplate } from '../api/templates';
import TemplateEditor from '../components/templates/TemplateEditor';

export default function TemplateEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const { data: template, isLoading } = useQuery({
    queryKey: ['template', id],
    queryFn: () => getTemplate(id).then((r) => r.data),
    enabled: !isNew,
  });

  if (!isNew && isLoading) {
    return (
      <div className="text-sm text-gray-400 p-4">Loading template…</div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">
          {isNew ? 'New template' : (template?.name ?? 'Edit template')}
        </h1>
        <button
          onClick={() => navigate('/templates')}
          className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          ← Back to templates
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <TemplateEditor
          initial={isNew ? undefined : template}
          onSaved={() => navigate('/templates')}
        />
      </div>
    </div>
  );
}
