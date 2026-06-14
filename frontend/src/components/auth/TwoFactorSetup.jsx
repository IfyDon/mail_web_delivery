import { useState } from 'react';
import client from '../../api/client';

export default function TwoFactorSetup({ onComplete }) {
  const [step, setStep] = useState('init');
  const [qrUrl, setQrUrl] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const startSetup = async () => {
    setLoading(true);
    try {
      const { data } = await client.post('/auth/2fa/setup/');
      setQrUrl(data.qr_url);
      setBackupCodes(data.backup_codes || []);
      setStep('verify');
    } catch {
      setError('Failed to start 2FA setup.');
    } finally {
      setLoading(false);
    }
  };

  const confirmCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await client.post('/auth/2fa/verify/', { code });
      setStep('done');
      onComplete?.();
    } catch {
      setError('Invalid code. Try again.');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'init') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Two-factor authentication adds an extra layer of security to your account.
        </p>
        <button
          onClick={startSetup}
          disabled={loading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
        >
          {loading ? 'Setting up…' : 'Enable 2FA'}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  if (step === 'verify') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-700">Scan this QR code with your authenticator app:</p>
        {qrUrl && <img src={qrUrl} alt="2FA QR code" className="border rounded-md" />}
        {backupCodes.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">Backup codes (save these):</p>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-3 font-mono text-xs grid grid-cols-2 gap-1">
              {backupCodes.map((c) => <span key={c}>{c}</span>)}
            </div>
          </div>
        )}
        <form onSubmit={confirmCode} className="flex gap-2">
          <input
            type="text"
            inputMode="numeric"
            placeholder="6-digit code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            maxLength={6}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-36"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            {loading ? '…' : 'Confirm'}
          </button>
        </form>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  return (
    <p className="text-sm text-green-700 font-medium">2FA is now enabled on your account.</p>
  );
}
