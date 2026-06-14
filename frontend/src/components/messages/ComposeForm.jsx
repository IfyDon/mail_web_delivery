import React, { useState } from 'react';
import axios from 'axios';

const STREAM_OPTIONS = [
  { value: 'transactional', label: 'Transactional' },
  { value: 'promotional', label: 'Promotional' },
];

const INITIAL_STATE = {
  to: '',
  from_address: '',
  subject: '',
  html_body: '',
  text_body: '',
  stream: 'transactional',
  track_opens: true,
  track_clicks: true,
  schedule_enabled: false,
  send_at: '',
};

export default function ComposeForm({ onSuccess, onCancel }) {
  const [form, setForm] = useState(INITIAL_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const buildPayload = () => {
    const payload = {
      to: form.to,
      from: form.from_address,
      subject: form.subject,
      html_body: form.html_body,
      text_body: form.text_body,
      stream: form.stream,
      track_opens: form.track_opens,
      track_clicks: form.track_clicks,
    };
    if (form.schedule_enabled && form.send_at) {
      payload.send_at = new Date(form.send_at).toISOString();
    }
    return payload;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const resp = await axios.post('/api/v1/send', buildPayload(), {
        headers: { Authorization: `Token ${token}` },
      });
      setResult(resp.data);
      if (onSuccess) onSuccess(resp.data);
    } catch (err) {
      const msg =
        err.response?.data?.errors?.[0]?.message ||
        err.response?.data?.message ||
        err.response?.data?.detail ||
        'Failed to send email.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-6">
        <h3 className="text-lg font-semibold text-green-800">
          {result.status === 'scheduled' ? 'Email Scheduled' : 'Email Queued'}
        </h3>
        <p className="mt-1 text-sm text-green-700">
          Message ID: <span className="font-mono">{result.message_id}</span>
        </p>
        <p className="mt-1 text-sm text-green-700">
          Status: <span className="font-medium capitalize">{result.status}</span>
        </p>
        <button
          type="button"
          onClick={() => { setResult(null); setForm(INITIAL_STATE); }}
          className="mt-4 text-sm text-green-700 underline hover:text-green-900"
        >
          Send another
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* To */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
        <input
          type="email"
          name="to"
          value={form.to}
          onChange={handleChange}
          required
          placeholder="recipient@example.com"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* From */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
        <input
          type="email"
          name="from_address"
          value={form.from_address}
          onChange={handleChange}
          required
          placeholder="sender@yourdomain.com"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">Must use a verified sending domain.</p>
      </div>

      {/* Subject */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
        <input
          type="text"
          name="subject"
          value={form.subject}
          onChange={handleChange}
          required
          maxLength={998}
          placeholder="Your email subject"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* HTML Body */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">HTML Body</label>
        <textarea
          name="html_body"
          value={form.html_body}
          onChange={handleChange}
          rows={6}
          placeholder="<p>Hello, world!</p>"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Text Body */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Plain Text Body <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          name="text_body"
          value={form.text_body}
          onChange={handleChange}
          rows={3}
          placeholder="Hello, world!"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Stream */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Stream</label>
        <select
          name="stream"
          value={form.stream}
          onChange={handleChange}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {STREAM_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Tracking toggles */}
      <div className="flex gap-6">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            name="track_opens"
            checked={form.track_opens}
            onChange={handleChange}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          Track opens
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            name="track_clicks"
            checked={form.track_clicks}
            onChange={handleChange}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          Track clicks
        </label>
      </div>

      {/* Scheduled send */}
      <div className="rounded-md border border-gray-200 bg-gray-50 p-4 space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            name="schedule_enabled"
            checked={form.schedule_enabled}
            onChange={handleChange}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          Schedule for later
        </label>

        {form.schedule_enabled && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Send at (your local time)
            </label>
            <input
              type="datetime-local"
              name="send_at"
              value={form.send_at}
              onChange={handleChange}
              required={form.schedule_enabled}
              min={new Date(Date.now() + 60_000).toISOString().slice(0, 16)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              The email will be queued and sent at the scheduled time (UTC).
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {loading
            ? 'Sending…'
            : form.schedule_enabled
            ? 'Schedule Email'
            : 'Send Email'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
