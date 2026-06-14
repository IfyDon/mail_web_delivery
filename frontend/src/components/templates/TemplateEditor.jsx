import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { createTemplate, updateTemplate } from '../../api/templates';
import TestEmailButton from './TestEmailButton';

export default function TemplateEditor({ initial, onSaved }) {
  const isNew = !initial?.id;
  const [form, setForm] = useState({
    name:      initial?.name      ?? '',
    subject:   initial?.subject   ?? '',
    html_body: initial?.html_body ?? '',
    text_body: initial?.text_body ?? '',
  });
  const [htmlTab, setHtmlTab] = useState('editor'); // 'editor' | 'preview'
  const [saved, setSaved]     = useState(false);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (initial) {
      setForm({
        name:      initial.name,
        subject:   initial.subject,
        html_body: initial.html_body ?? '',
        text_body: initial.text_body ?? '',
      });
    }
  }, [initial]);

  const saveMutation = useMutation({
    mutationFn: () =>
      isNew ? createTemplate(form) : updateTemplate(initial.id, form),
    onSuccess: (res) => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      onSaved?.(res.data);
    },
    onError: (err) =>
      setError(err.response?.data?.detail || 'Save failed.'),
  });

  const set = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <div className="space-y-5">
      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-2 rounded-md">
          {error}
        </p>
      )}

      {/* Name + Subject */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Template name
          </label>
          <input
            value={form.name}
            onChange={set('name')}
            placeholder="Welcome email"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Subject line
          </label>
          <input
            value={form.subject}
            onChange={set('subject')}
            placeholder="Welcome to {{ company_name }}"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>
      </div>

      {/* HTML editor + live preview */}
      <div>
        {/* Tab bar */}
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-medium text-gray-600">HTML body</label>
          <div className="flex gap-1 bg-gray-100 rounded p-0.5">
            {['editor', 'preview'].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setHtmlTab(t)}
                className={`px-3 py-0.5 rounded text-xs font-medium capitalize transition-colors ${
                  htmlTab === t
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Split pane on md+, stacked on mobile */}
        <div className="flex gap-3" style={{ minHeight: 320 }}>
          {/* Editor column — always rendered so value stays in sync */}
          <div
            className={`flex-1 ${htmlTab === 'preview' ? 'hidden md:flex' : 'flex'} flex-col`}
          >
            <textarea
              value={form.html_body}
              onChange={set('html_body')}
              spellCheck={false}
              className="flex-1 w-full border border-gray-300 rounded-md px-3 py-2 text-xs font-mono resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder={'<h1>Hello {{ name }}</h1>\n<p>Welcome aboard!</p>'}
              style={{ minHeight: 320 }}
            />
          </div>

          {/* Preview column */}
          <div
            className={`flex-1 ${htmlTab === 'editor' ? 'hidden md:flex' : 'flex'} flex-col`}
          >
            <div className="flex-1 border border-gray-200 rounded-md overflow-hidden bg-white">
              {form.html_body.trim() ? (
                <iframe
                  srcDoc={form.html_body}
                  sandbox="allow-same-origin"
                  title="Email preview"
                  className="w-full h-full border-0"
                  style={{ minHeight: 320 }}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-gray-400"
                     style={{ minHeight: 320 }}>
                  Preview will appear here as you type
                </div>
              )}
            </div>
          </div>
        </div>

        <p className="mt-1 text-xs text-gray-400">
          Use <code className="bg-gray-100 px-1 rounded">{`{{ variable }}`}</code> for template
          variables. Preview renders the raw HTML without substitution.
        </p>
      </div>

      {/* Plain-text body */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Plain-text body
          <span className="ml-1 text-gray-400 font-normal">(optional — shown in email clients that block HTML)</span>
        </label>
        <textarea
          value={form.text_body}
          onChange={set('text_body')}
          rows={4}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-xs font-mono resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder={'Hello {{ name }},\n\nWelcome aboard!'}
        />
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-4 pt-1">
        <button
          type="button"
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="bg-indigo-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60 transition-colors"
        >
          {saveMutation.isPending ? 'Saving…' : isNew ? 'Create template' : 'Save changes'}
        </button>

        {saved && (
          <span className="text-sm text-green-600 font-medium">Saved!</span>
        )}

        {!isNew && <TestEmailButton templateId={initial.id} />}
      </div>
    </div>
  );
}
