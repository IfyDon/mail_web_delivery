import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import TwoFactorSetup from '../components/auth/TwoFactorSetup';
import client from '../api/client';
import {
  getProfile, updateProfile, deleteAccount,
  listApiKeys, createApiKey, revokeApiKey,
} from '../api/auth';
import { listTeam, inviteMember, updateMember, removeMember } from '../api/team';
import { formatDate, formatDateTime } from '../utils/formatters';

// ── Profile ────────────────────────────────────────────────────────────────────

function ProfilePanel({ user }) {
  const qc = useQueryClient();
  const [firstName, setFirstName] = useState(user?.first_name ?? '');
  const [lastName, setLastName]   = useState(user?.last_name  ?? '');
  const [status, setStatus]       = useState(null);

  useEffect(() => {
    setFirstName(user?.first_name ?? '');
    setLastName(user?.last_name   ?? '');
  }, [user]);

  const mutation = useMutation({
    mutationFn: () => updateProfile({ first_name: firstName, last_name: lastName }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] });
      setStatus({ ok: true, msg: 'Profile updated.' });
    },
    onError: (err) =>
      setStatus({ ok: false, msg: err.response?.data?.detail || 'Failed to update profile.' }),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setStatus(null);
    mutation.mutate();
  };

  return (
    <div className="space-y-5">
      {status && (
        <p className={`text-sm px-3 py-2 rounded ${status.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
          {status.msg}
        </p>
      )}

      <div className="grid grid-cols-2 gap-4 max-w-sm">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">First name</label>
          <input
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Last name</label>
          <input
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      <div className="max-w-sm space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Email address</label>
          <div className="flex items-center gap-2">
            <span className="flex-1 border border-gray-200 bg-gray-50 rounded-md px-3 py-2 text-sm text-gray-700">
              {user?.email}
            </span>
            <span
              className={`shrink-0 inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                user?.is_verified
                  ? 'bg-green-100 text-green-700'
                  : 'bg-yellow-100 text-yellow-700'
              }`}
            >
              {user?.is_verified ? 'Verified' : 'Unverified'}
            </span>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Member since</label>
          <span className="text-sm text-gray-700">
            {user?.created_at ? formatDate(user.created_at) : '—'}
          </span>
        </div>

        {user?.quota && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Monthly usage</label>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="h-2 rounded-full bg-indigo-500"
                  style={{ width: `${Math.min(user.quota.usage_percentage, 100)}%` }}
                />
              </div>
              <span className="text-xs text-gray-600 shrink-0">
                {user.quota.emails_sent_this_month.toLocaleString()} / {user.quota.monthly_limit.toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>

      <button
        onClick={handleSubmit}
        disabled={mutation.isPending}
        className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
      >
        {mutation.isPending ? 'Saving…' : 'Save changes'}
      </button>
    </div>
  );
}

// ── Change Password ────────────────────────────────────────────────────────────

function ChangePasswordForm() {
  const [current, setCurrent] = useState('');
  const [next, setNext]       = useState('');
  const [confirm, setConfirm] = useState('');
  const [status, setStatus]   = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus(null);
    if (next !== confirm) { setStatus({ ok: false, msg: 'New passwords do not match.' }); return; }
    setLoading(true);
    try {
      await client.post('/auth/password/change/', {
        current_password: current,
        new_password: next,
      });
      setStatus({ ok: true, msg: 'Password updated.' });
      setCurrent(''); setNext(''); setConfirm('');
    } catch (err) {
      setStatus({ ok: false, msg: err.response?.data?.detail || 'Failed to update password.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-sm">
      {status && (
        <p className={`text-sm px-3 py-2 rounded ${status.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
          {status.msg}
        </p>
      )}
      {[
        { label: 'Current password', val: current, set: setCurrent },
        { label: 'New password',     val: next,    set: setNext,    min: 8 },
        { label: 'Confirm new',      val: confirm, set: setConfirm },
      ].map(({ label, val, set, min }) => (
        <div key={label}>
          <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
          <input
            type="password"
            required
            minLength={min}
            value={val}
            onChange={(e) => set(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      ))}
      <button
        type="submit"
        disabled={loading}
        className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
      >
        {loading ? 'Updating…' : 'Update password'}
      </button>
    </form>
  );
}

// ── API Keys ───────────────────────────────────────────────────────────────────

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={copy}
      className={`shrink-0 px-3 py-1 rounded text-xs font-medium border transition-colors ${
        copied
          ? 'border-green-300 bg-green-50 text-green-700'
          : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50'
      }`}
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function ApiKeysPanel() {
  const qc = useQueryClient();
  const [name, setName]     = useState('');
  const [newKey, setNewKey] = useState(null);
  const [error, setError]   = useState('');

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => listApiKeys().then((r) => r.data.results ?? r.data),
  });

  const createMutation = useMutation({
    mutationFn: () => createApiKey(name),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['api-keys'] });
      setNewKey(res.data.key);
      setName('');
      setError('');
    },
    onError: (err) =>
      setError(err.response?.data?.name?.[0] || 'Failed to create key.'),
  });

  const revokeMutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  return (
    <div className="space-y-5">
      {newKey && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm font-medium text-green-800 mb-2">
            New key created — copy it now. It won't be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 font-mono text-xs bg-white border border-green-200 rounded px-3 py-2 break-all">
              {newKey}
            </code>
            <CopyButton text={newKey} />
          </div>
          <button
            onClick={() => setNewKey(null)}
            className="mt-2 text-xs text-green-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Generate a new key</p>
        <form
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }}
          className="flex gap-2 max-w-sm"
        >
          <input
            type="text"
            placeholder="Key name (e.g. Production)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            Generate
          </button>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Last used</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            ) : keys.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">No API keys yet.</td></tr>
            ) : (
              keys.map((k) => (
                <tr key={k.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{k.name}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {k.last_used_at ? formatDateTime(k.last_used_at) : 'Never'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      k.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {k.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {k.is_active && (
                      <button
                        onClick={() => {
                          if (window.confirm(`Revoke key "${k.name}"?`)) revokeMutation.mutate(k.id);
                        }}
                        className="text-red-500 hover:underline text-xs"
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
        <p className="font-medium text-gray-700 mb-1">Using your API key</p>
        <p className="mb-2">Include the key in every request as a Bearer token:</p>
        <code className="block bg-white border border-gray-200 rounded px-3 py-2 text-xs font-mono">
          Authorization: Bearer wm_xxxxxxxxxxxxxxxx
        </code>
      </div>
    </div>
  );
}

// ── Notifications ──────────────────────────────────────────────────────────────

const NOTIF_DEFAULTS = {
  bounce_warn:     5,
  bounce_alert:    10,
  complaint_warn:  0.05,
  complaint_alert: 0.1,
  quota_warn:      80,
};

const NOTIF_KEY = 'wm_notif_prefs';

function NotificationsPanel() {
  const [prefs, setPrefs] = useState(() => {
    try {
      return { ...NOTIF_DEFAULTS, ...JSON.parse(localStorage.getItem(NOTIF_KEY) || '{}') };
    } catch {
      return { ...NOTIF_DEFAULTS };
    }
  });
  const [saved, setSaved] = useState(false);

  const update = (key, val) => {
    const parsed = parseFloat(val);
    if (!Number.isNaN(parsed)) setPrefs((p) => ({ ...p, [key]: parsed }));
  };

  const save = () => {
    localStorage.setItem(NOTIF_KEY, JSON.stringify(prefs));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const reset = () => {
    setPrefs({ ...NOTIF_DEFAULTS });
    localStorage.removeItem(NOTIF_KEY);
  };

  const Field = ({ label, helpText, stateKey, suffix = '%', step = '0.01', min = '0' }) => (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-0.5">{label}</label>
      {helpText && <p className="text-xs text-gray-400 mb-1">{helpText}</p>}
      <div className="flex items-center gap-2 max-w-[12rem]">
        <input
          type="number"
          min={min}
          step={step}
          value={prefs[stateKey]}
          onChange={(e) => update(stateKey, e.target.value)}
          className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <span className="text-sm text-gray-500 shrink-0">{suffix}</span>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">
        Alert thresholds control the colour indicators shown on your Dashboard.
        These preferences are stored locally in your browser.
      </p>

      <div className="space-y-1">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Bounce rate</p>
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
          <Field
            label="Warning threshold (amber)"
            helpText="Dashboard card turns amber above this rate."
            stateKey="bounce_warn"
            step="0.5"
            min="0"
          />
          <Field
            label="Alert threshold (red)"
            helpText="Dashboard card turns red and shows a banner above this rate."
            stateKey="bounce_alert"
            step="0.5"
            min="0"
          />
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Complaint rate</p>
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
          <Field
            label="Warning threshold (amber)"
            stateKey="complaint_warn"
            step="0.01"
            min="0"
          />
          <Field
            label="Alert threshold (red)"
            stateKey="complaint_alert"
            step="0.01"
            min="0"
          />
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Monthly quota</p>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <Field
            label="Usage warning level"
            helpText="Show a warning on the profile tab when usage exceeds this percentage."
            stateKey="quota_warn"
            step="5"
            min="0"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          {saved ? 'Saved!' : 'Save preferences'}
        </button>
        <button
          onClick={reset}
          className="text-sm text-gray-500 hover:text-gray-700 underline"
        >
          Reset to defaults
        </button>
      </div>
    </div>
  );
}

// ── Team Panel ─────────────────────────────────────────────────────────────────

const ROLE_BADGE = {
  admin:  'bg-indigo-100 text-indigo-800',
  viewer: 'bg-gray-100 text-gray-700',
  owner:  'bg-purple-100 text-purple-800',
};

function TeamPanel() {
  const qc = useQueryClient();
  const [showModal, setShowModal]     = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole]   = useState('viewer');
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Invite colleagues to access this account without sharing credentials.
        </p>
        <button
          onClick={() => { setShowModal(true); setInviteError(''); }}
          className="bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-md hover:bg-indigo-700 shrink-0 ml-4"
        >
          Invite teammate
        </button>
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden">
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
                            onClick={() => {
                              setInviteEmail(m.email);
                              setInviteRole(m.role);
                              inviteMutation.mutate();
                            }}
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

      <div className="text-xs text-gray-400 space-y-1">
        <p><strong>Admin</strong> — full access except deleting the account or transferring ownership.</p>
        <p><strong>Viewer</strong> — read-only access to stats, messages, and suppressions.</p>
        <p>Invitation links expire after 48 hours.</p>
      </div>

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

// ── Data & Privacy ─────────────────────────────────────────────────────────────

function PrivacyPanel() {
  const navigate  = useNavigate();
  const { logout } = useAuth();
  const [confirm, setConfirm]   = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError]       = useState('');

  const handleDelete = async () => {
    if (confirm !== 'DELETE') {
      setError('Type DELETE exactly to confirm.');
      return;
    }
    setDeleting(true);
    setError('');
    try {
      await deleteAccount();
      logout();
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete account. Please try again.');
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-medium text-gray-800 mb-1">Data export</p>
        <p className="text-sm text-gray-500 mb-3">
          Request a full export of your account data including messages, suppressions, and stats.
          Exports are prepared within 24 hours and delivered to your registered email address.
        </p>
        <a
          href="mailto:support@webmail.app?subject=Data%20Export%20Request"
          className="inline-flex items-center px-4 py-2 rounded-md text-sm font-medium border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
        >
          Request data export
        </a>
      </div>

      <div className="border-t border-gray-200 pt-8">
        <p className="text-sm font-semibold text-red-700 mb-1">Delete account</p>
        <p className="text-sm text-gray-500 mb-4">
          Permanently deletes your account, all API keys, messages, templates, and analytics data.
          This action cannot be undone.
        </p>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-3 max-w-sm">
          <p className="text-xs text-red-700 font-medium">
            Type <strong>DELETE</strong> to confirm account deletion.
          </p>
          <input
            type="text"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="DELETE"
            className="w-full border border-red-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 bg-white"
          />
          {error && <p className="text-xs text-red-700">{error}</p>}
          <button
            onClick={handleDelete}
            disabled={deleting || confirm !== 'DELETE'}
            className="w-full bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-40"
          >
            {deleting ? 'Deleting…' : 'Permanently delete my account'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Settings Page ─────────────────────────────────────────────────────────

const TABS = [
  { key: 'profile',       label: 'Profile' },
  { key: 'security',      label: 'Security' },
  { key: 'password',      label: 'Password' },
  { key: 'api-keys',      label: 'API Keys' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'team',          label: 'Team' },
  { key: 'privacy',       label: 'Data & Privacy' },
];

export default function Settings() {
  const { user } = useAuth();
  const [tab, setTab] = useState('profile');

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => getProfile().then((r) => r.data),
    initialData: user,
  });

  const TAB_TITLES = {
    profile:       'Profile',
    security:      'Two-factor authentication (2FA)',
    password:      'Change password',
    'api-keys':    'API Keys',
    notifications: 'Alert preferences',
    team:          'Team members',
    privacy:       'Data & Privacy',
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-xl font-semibold text-gray-900">Account settings</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200 overflow-x-auto">
        <div className="flex gap-5 min-w-max">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`pb-2 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                tab === t.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <p className="text-sm font-medium text-gray-800 mb-5">{TAB_TITLES[tab]}</p>

        {tab === 'profile' && <ProfilePanel user={profile} />}

        {tab === 'security' && <TwoFactorSetup />}

        {tab === 'password' && <ChangePasswordForm />}

        {tab === 'api-keys' && <ApiKeysPanel />}

        {tab === 'notifications' && <NotificationsPanel />}

        {tab === 'team' && <TeamPanel />}

        {tab === 'privacy' && <PrivacyPanel />}
      </div>
    </div>
  );
}
