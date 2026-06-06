import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createDomain } from '../../api/domains';

export default function AddDomainForm() {
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => createDomain(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['domains'] });
      setName('');
      setError('');
    },
    onError: (err) =>
      setError(err.response?.data?.name?.[0] || 'Failed to add domain.'),
  });

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
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
        disabled={mutation.isPending}
        className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
      >
        Add
      </button>
      {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
    </form>
  );
}
