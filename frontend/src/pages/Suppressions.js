import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSuppressions, deleteSuppression, createSuppression } from '../api/suppressions';
import { formatDate } from '../utils/formatters';

const REASON_STYLES = {
  bounce:      'bg-orange-100 text-orange-800',
  complaint:   'bg-red-100 text-red-800',
  unsubscribe: 'bg-gray-100 text-gray-700',
  manual:      'bg-blue-100 text-blue-800',
};

export default function Suppressions() {
  const qc = useQueryClient();
  const [page, setPage]         = useState(1);
  const [reasonFilter, setReasonFilter] = useState('');
  const [emailSearch, setEmailSearch]   = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmail, setNewEmail]         = useState('');
  const [newReason, setNewReason]       = useState('manual');
  const [addError, setAddError]         = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['suppressions', page, reasonFilter, emailSearch],
    queryFn: () =>
      listSuppressions({
        page,
        ...(reasonFilter ? { type: reasonFilter } : {}),
        ...(emailSearch  ? { email: emailSearch }  : {}),
      }).then((r) => r.data),
    placeholderData: (prev) => prev,
  });

  const suppressions = data?.suppressions ?? data?.results ?? [];
  const total = data?.total ?? data?.count ?? 0;
  const totalPages = Math.ceil(total / 50);

  const deleteMutation = useMutation({
    mutationFn: (email) => deleteSuppression(email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['suppressions'] }),
  });

  const addMutation = useMutation({
    mutationFn: () => createSuppression({ email: newEmail, type: newReason, reason: newReason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['suppressions'] });
      setShowAddModal(false);
      setNewEmail('');
      setNewReason('manual');
      setAddError('');
    },
    onError: (err) => setAddError(err.response?.data?.detail ?? 'Failed to add suppression.'),
  });

  function handleSearchChange(e) {
    setEmailSearch(e.target.value);
    setPage(1);
  }

  function handleReasonChange(e) {
    setReasonFilter(e.target.value);
    setPage(1);
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold text-gray-900">Suppressions</h1>
          {total > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
              {total}
            </span>
          )}
        </div>
        <button
          onClick={() => { setShowAddModal(true); setAddError(''); }}
          className="bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-md hover:bg-indigo-700"
        >
          + Add manually
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search email…"
          value={emailSearch}
          onChange={handleSearchChange}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-56"
        />
        <select
          value={reasonFilter}
          onChange={handleReasonChange}
          className="border border-gray-300 rounded-md px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All reasons</option>
          <option value="bounce">Bounce</option>
          <option value="complaint">Complaint</option>
          <option value="unsubscribe">Unsubscribe</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3">Added</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            ) : suppressions.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  {emailSearch || reasonFilter ? 'No matching suppressions.' : 'Suppression list is empty.'}
                </td>
              </tr>
            ) : (
              suppressions.map((s, i) => {
                const email = s.email;
                const reason = s.reason ?? s.type ?? '—';
                return (
                  <tr key={`${email}-${i}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-700 font-mono text-xs">{email}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        REASON_STYLES[reason] ?? 'bg-gray-100 text-gray-700'
                      }`}>
                        {reason}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(s.created_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => deleteMutation.mutate(email)}
                        disabled={deleteMutation.isPending}
                        className="text-red-500 hover:underline text-xs disabled:opacity-40"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Prev
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Add manually modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm space-y-4">
            <h2 className="text-base font-semibold text-gray-900">Add suppression</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Email address</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Reason</label>
                <select
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="manual">Manual</option>
                  <option value="bounce">Bounce</option>
                  <option value="complaint">Complaint</option>
                  <option value="unsubscribe">Unsubscribe</option>
                </select>
              </div>
            </div>
            {addError && <p className="text-sm text-red-600">{addError}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowAddModal(false); setAddError(''); }}
                className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => addMutation.mutate()}
                disabled={!newEmail || addMutation.isPending}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-40"
              >
                {addMutation.isPending ? 'Adding…' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
