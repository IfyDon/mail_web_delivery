import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { sendTestEmail } from '../../api/templates';

export default function TestEmailButton({ templateId }) {
  const [recipient, setRecipient] = useState('');
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: () => sendTestEmail(templateId, recipient),
    onSuccess: () => { setOpen(false); setRecipient(''); },
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-sm text-indigo-600 hover:underline"
      >
        Send test email
      </button>
    );
  }

  return (
    <div className="flex gap-2 items-center">
      <input
        type="email"
        placeholder="recipient@example.com"
        value={recipient}
        onChange={(e) => setRecipient(e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-56"
      />
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || !recipient}
        className="bg-indigo-600 text-white px-3 py-1.5 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
      >
        {mutation.isPending ? 'Sending…' : 'Send'}
      </button>
      <button onClick={() => setOpen(false)} className="text-sm text-gray-400 hover:text-gray-600">
        Cancel
      </button>
      {mutation.isSuccess && <span className="text-sm text-green-600">Sent!</span>}
      {mutation.isError && <span className="text-sm text-red-600">Failed.</span>}
    </div>
  );
}
