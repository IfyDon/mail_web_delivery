import { useState } from 'react';

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
      className={`shrink-0 text-xs px-2 py-0.5 rounded border transition-colors ${
        copied
          ? 'border-green-300 bg-green-50 text-green-700'
          : 'border-gray-300 bg-white text-gray-500 hover:bg-gray-50'
      }`}
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

const CHECK_ICON = {
  true:    { symbol: '✓', cls: 'text-green-600' },
  false:   { symbol: '✗', cls: 'text-red-500'   },
  unknown: { symbol: '?', cls: 'text-gray-400'  },
};

export default function DnsRecordDisplay({ domain }) {
  if (!domain) return null;

  // dns_check may be returned by the verify endpoint: { spf: bool, dkim: bool, dmarc: bool }
  const dns = domain.dns_check ?? {};

  const records = [
    {
      label: 'SPF',
      type:  'TXT',
      host:  domain.name,
      value: 'v=spf1 include:amazonses.com ~all',
      check: dns.spf,
    },
    {
      label: 'DKIM',
      type:  'TXT',
      host:  `webmail._domainkey.${domain.name}`,
      value: domain.dkim_public_key ?? '(generated — fetch domain detail to see the key)',
      check: dns.dkim,
    },
    {
      label: 'DMARC',
      type:  'TXT',
      host:  `_dmarc.${domain.name}`,
      value: `v=DMARC1; p=quarantine; rua=mailto:dmarc@${domain.name}`,
      check: dns.dmarc,
    },
  ];

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        DNS records to publish
      </p>
      {records.map((r) => {
        const icon = r.check === true
          ? CHECK_ICON.true
          : r.check === false
          ? CHECK_ICON.false
          : CHECK_ICON.unknown;

        return (
          <div
            key={r.label}
            className="bg-white border border-gray-200 rounded-md p-3 space-y-2"
          >
            {/* Row 1: label + type + check status */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-indigo-600">{r.label}</span>
                <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                  {r.type}
                </span>
              </div>
              {r.check !== undefined && (
                <span className={`text-xs font-medium ${icon.cls}`}>
                  {icon.symbol} {r.check ? 'Detected' : 'Not detected'}
                </span>
              )}
            </div>

            {/* Row 2: host */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 w-10 shrink-0">Host</span>
              <code className="flex-1 text-xs font-mono text-gray-700 bg-gray-50 border border-gray-100 rounded px-2 py-1 break-all">
                {r.host}
              </code>
              <CopyButton text={r.host} />
            </div>

            {/* Row 3: value */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 w-10 shrink-0">Value</span>
              <code className="flex-1 text-xs font-mono text-gray-700 bg-gray-50 border border-gray-100 rounded px-2 py-1 break-all">
                {r.value}
              </code>
              <CopyButton text={r.value} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
