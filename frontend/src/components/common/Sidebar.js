import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listSuppressions } from '../../api/suppressions';
import { listWebhooks } from '../../api/webhooks';

const SENDING = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/messages',  label: 'Messages' },
  { to: '/streams',   label: 'Streams' },
  { to: '/templates', label: 'Templates' },
];

const CONFIG = [
  { to: '/domains',      label: 'Domains' },
  { to: '/webhooks',     label: 'Webhooks',     failedBadge: true },
  { to: '/suppressions', label: 'Suppressions', countBadge: true },
  { to: '/api-keys',     label: 'API Keys' },
  { to: '/billing',      label: 'Billing' },
  { to: '/settings',     label: 'Settings' },
];

function NavItem({ to, label, badge }) {
  return (
    <NavLink
      to={to}
      end={to === '/settings'}
      className={({ isActive }) =>
        `flex items-center justify-between px-5 py-2 text-sm transition-colors ${
          isActive
            ? 'bg-indigo-600 text-white'
            : 'text-gray-300 hover:bg-gray-800 hover:text-white'
        }`
      }
    >
      <span>{label}</span>
      {badge}
    </NavLink>
  );
}

export default function Sidebar() {
  const { data: suppressionsData } = useQuery({
    queryKey: ['suppressions-count'],
    queryFn: () => listSuppressions({ page: 1 }).then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: false,
  });

  const { data: webhooksData } = useQuery({
    queryKey: ['webhooks-list'],
    queryFn: () => listWebhooks().then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: false,
  });

  const suppressionCount = suppressionsData?.total ?? suppressionsData?.count ?? 0;

  const webhooksList = Array.isArray(webhooksData)
    ? webhooksData
    : (webhooksData?.results ?? []);
  const failedWebhooks = webhooksList.filter(
    (w) => w.last_dispatch_failed === true || w.failed_count > 0
  ).length;

  function renderBadge(item) {
    if (item.countBadge && suppressionCount > 0) {
      return (
        <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full text-xs font-bold bg-gray-600 text-gray-100 min-w-[1.25rem]">
          {suppressionCount > 999 ? '999+' : suppressionCount}
        </span>
      );
    }
    if (item.failedBadge && failedWebhooks > 0) {
      return (
        <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full text-xs font-bold bg-red-500 text-white min-w-[1.25rem]">
          {failedWebhooks}
        </span>
      );
    }
    return null;
  }

  return (
    <aside className="w-56 bg-gray-900 text-white flex flex-col shrink-0">
      <div className="px-5 py-4 text-base font-semibold tracking-tight border-b border-gray-700">
        WebMail
      </div>
      <nav className="flex-1 py-3 overflow-y-auto">
        <p className="px-5 pt-1 pb-2 text-xs font-semibold text-gray-500 uppercase tracking-widest">
          Sending
        </p>
        <div className="space-y-0.5 mb-3">
          {SENDING.map((item) => (
            <NavItem key={item.to} to={item.to} label={item.label} badge={renderBadge(item)} />
          ))}
        </div>

        <div className="mx-5 border-t border-gray-700 mb-3" />

        <p className="px-5 pb-2 text-xs font-semibold text-gray-500 uppercase tracking-widest">
          Config
        </p>
        <div className="space-y-0.5">
          {CONFIG.map((item) => (
            <NavItem key={item.to} to={item.to} label={item.label} badge={renderBadge(item)} />
          ))}
        </div>
      </nav>
    </aside>
  );
}
