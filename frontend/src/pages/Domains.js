import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDomains, createDomain, verifyDomain, deleteDomain } from '../api/domains';
import DnsRecordDisplay from '../components/domains/DnsRecordDisplay';
import { statusBadge } from '../utils/formatters';
import EmptyState from '../components/common/EmptyState';
import { parseDomainError } from '../utils/apiError';

const STATUS_HELP = {
  pending:  'Publish the DNS records below, then click Verify.',
  verified: 'All DNS records detected. This domain is ready to send from.',
  failed:   'One or more DNS records could not be found. Check the records below.',
};

export default function Domains() {
  const qc = useQueryClient();
  const [name, setName]         = useState('');
  const [addError, setAddError] = useState('');
  const [expanded, setExpanded] = useState(null); // domain id

  const { data: domains = [], isLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: () => listDomains().then((r) => r.data.results ?? r.data),
  });

  const addMutation = useMutation({
    mutationFn: () => createDomain(name),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['domains'] });
      // Auto-expand the new domain so the user sees its DNS records immediately
      setExpanded(res.data.id);
      setName('');
      setAddError('');
    },
    onError: (err) => setAddError(parseDomainError(err)),
  });

  const verifyMutation = useMutation({
    mutationFn: verifyDomain,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['domains'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDomain,
    onSuccess: (_, id) => {
      if (expanded === id) setExpanded(null);
      qc.invalidateQueries({ queryKey: ['domains'] });
    },
  });

  const toggle = (id) => setExpanded((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Domains</h1>

      {/* Add domain form */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-sm font-medium text-gray-700 mb-3">Add sending domain</p>
        <form
          onSubmit={(e) => { e.preventDefault(); addMutation.mutate(); }}
          className="flex gap-2"
        >
          <input
            type="text"
            placeholder="mail.yourdomain.com"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
          <button
            type="submit"
            disabled={addMutation.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            Add
          </button>
        </form>
        {addError && <p className="mt-2 text-sm text-red-600">{addError}</p>}
      </div>

      {/* Domain list */}
      {isLoading ? (
        <p className="text-sm text-gray-400 px-1">Loading…</p>
      ) : domains.length === 0 ? (
        <EmptyState
          icon="🌐"
          title="No domains added"
          description="Add a sending domain to start delivering emails from your own address. DNS records will be generated automatically."
        />
      ) : (
        <div className="space-y-3">
          {domains.map((d) => {
            const isOpen = expanded === d.id;
            return (
              <div
                key={d.id}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden"
              >
                {/* Domain header row */}
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-mono text-sm text-gray-800 truncate">
                      {d.domain}
                    </span>
                    <span
                      className={`inline-flex shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(
                        d.verification_status
                      )}`}
                    >
                      {d.verification_status}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      onClick={() => verifyMutation.mutate(d.id)}
                      disabled={verifyMutation.isPending && verifyMutation.variables === d.id}
                      className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                    >
                      Verify
                    </button>
                    <button
                      onClick={() => toggle(d.id)}
                      className={`text-xs font-medium transition-colors ${
                        isOpen ? 'text-indigo-600' : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      DNS records {isOpen ? '▲' : '▼'}
                    </button>
                    <button
                      onClick={() => {
                        if (window.confirm(`Remove domain "${d.domain}"?`)) {
                          deleteMutation.mutate(d.id);
                        }
                      }}
                      className="text-xs text-red-500 hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {/* Status help text */}
                {STATUS_HELP[d.verification_status] && (
                  <p className="px-4 pb-2 text-xs text-gray-500">
                    {STATUS_HELP[d.verification_status]}
                  </p>
                )}

                {/* Expandable DNS panel */}
                {isOpen && (
                  <div className="border-t border-gray-100 px-4 py-4 bg-gray-50">
                    <DnsRecordDisplay domain={d} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
