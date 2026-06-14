import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTeam, inviteMember, updateMember, removeMember } from '../api/team';
import { formatDate } from '../utils/formatters';

const ROLE_BADGE = {
  admin:  'bg-indigo-100 text-indigo-800',
  viewer: 'bg-gray-100 text-gray-700',
  owner:  'bg-purple-100 text-purple-800',
};

export default function Team() {
  const qc = useQueryClient();
  const [showModal, setShowModal]   = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [inviteError, setInviteError] = useState('');

  const { data: members = [], isLoading } = useQuery({
    queryKey: ['team'],
    queryFn: () => listTeam().then((r) => r.data),
  });

  const inviteMutation = useMutation({
    mutationFn: () => inviteMember({ email: inviteEmail, role: inviteRole }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['team'] });
      setShowModal(false);
      setInviteEmail('');
      setInviteRole('viewer');
      setInviteError('');
    },
    onError: (err) =>
      setInviteError(err.response?.data?.detail ?? 'Failed to send invitation.'),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }) => updateMember(id, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team'] }),
  });

  const removeMutation = useMutation({
    mutationFn: removeMember,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team'] }),
  });

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Team</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Invite colleagues to access this account without sharing credentials.
          </p>
        </div>
        <button
          onClick={() => { setShowModal(true); setInviteError(''); }}
          className="bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-md hover:bg-indigo-700"
        >
          Invite teammate
        </button>
      </div>

      {/* Members table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Invited</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            ) : members.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  No team members yet. Invite a colleague to get started.
                </td>
              </tr>
            ) : (
              members.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-800">{m.email}</td>
                  <td className="px-4 py-3">
                    {/* Role selector — owner row is read-only */}
                    {m.role === 'owner' ? (
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_BADGE.owner}`}>
                        Owner
                      </span>
                    ) : (
                      <select
                        value={m.role}
                        onChange={(e) => roleMutation.mutate({ id: m.id, role: e.target.value })}
                        disabled={roleMutation.isPending}
                        className="text-xs border border-gray-200 rounded px-1.5 py-0.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                      >
                        <option value="admin">Admin</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {m.is_pending ? (
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Pending
                      </span>
                    ) : (
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Active
                      </span>
                    )}
                    {m.is_expired && (
                      <span className="ml-1 inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                        Expired
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {m.invited_at ? formatDate(m.invited_at) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {m.role !== 'owner' && (
                      <div className="flex gap-3">
                        {m.is_pending && (
                          <button
                            onClick={() => inviteMutation.mutate() /* resend */}
                            className="text-xs text-indigo-600 hover:underline"
                          >
                            Resend
                          </button>
                        )}
                        <button
                          onClick={() => {
                            if (window.confirm(`Remove ${m.email} from team?`)) {
                              removeMutation.mutate(m.id);
                            }
                          }}
                          disabled={removeMutation.isPending}
                          className="text-xs text-red-500 hover:underline disabled:opacity-40"
                        >
                          {m.is_pending ? 'Cancel' : 'Remove'}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-gray-400 space-y-1 px-1">
        <p><strong>Admin</strong> — full access except deleting the account or transferring ownership.</p>
        <p><strong>Viewer</strong> — read-only access to stats, messages, and suppressions.</p>
        <p>Invitation links expire after 48 hours.</p>
      </div>

      {/* Invite modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm space-y-4">
            <h2 className="text-base font-semibold text-gray-900">Invite teammate</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Email address</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@example.com"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="viewer">Viewer — read-only</option>
                  <option value="admin">Admin — full access</option>
                </select>
              </div>
            </div>
            {inviteError && <p className="text-sm text-red-600">{inviteError}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowModal(false); setInviteError(''); }}
                className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => inviteMutation.mutate()}
                disabled={!inviteEmail || inviteMutation.isPending}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-40"
              >
                {inviteMutation.isPending ? 'Sending…' : 'Send invitation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
