import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listSuppressions } from '../../api/suppressions';
import { listWebhooks } from '../../api/webhooks';

const SENDING = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/messages',  label: 'Messages' },
  { to: '/contacts',  label: 'Contacts' },
  { to: '/streams',   label: 'Streams' },
  { to: '/templates', label: 'Templates' },
];

const CONFIG = [
  { to: '/domains',      label: 'Domains' },
  { to: '/webhooks',     label: 'Webhooks',     failedBadge: true },
  { to: '/suppressions', label: 'Suppressions', countBadge:  true },
  { to: '/api-keys',     label: 'API Keys' },
  { to: '/billing',      label: 'Billing' },
  { to: '/settings',     label: 'Settings' },
];

function NavItem({ to, label, badge }) {
  return (
    <NavLink
      to={to}
      end={to === '/settings'}
      style={({ isActive }) => isActive
        ? { background: 'var(--nav-active-bg)', color: 'var(--nav-active-text)' }
        : { color: 'var(--text-nav)' }
      }
      className={({ isActive }) =>
        `flex items-center justify-between px-4 py-2 mx-2 rounded-lg text-sm font-medium transition-all duration-150 ${
          isActive ? '' : 'hover:opacity-90'
        }`
      }
      onMouseEnter={e => {
        if (!e.currentTarget.getAttribute('aria-current')) {
          e.currentTarget.style.background = 'var(--nav-hover-bg)';
          e.currentTarget.style.color = 'var(--nav-hover-text)';
        }
      }}
      onMouseLeave={e => {
        if (!e.currentTarget.getAttribute('aria-current')) {
          e.currentTarget.style.background = '';
          e.currentTarget.style.color = 'var(--text-nav)';
        }
      }}
    >
      <span>{label}</span>
      {badge}
    </NavLink>
  );
}

export default function Sidebar() {
  const { data: suppressionsData } = useQuery({
    queryKey: ['suppressions-count'],
    queryFn: () => listSuppressions({ page: 1 }).then(r => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: false,
  });

  const { data: webhooksData } = useQuery({
    queryKey: ['webhooks-list'],
    queryFn: () => listWebhooks().then(r => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: false,
  });

  const suppressionCount = suppressionsData?.total ?? suppressionsData?.count ?? 0;
  const webhooksList = Array.isArray(webhooksData) ? webhooksData : (webhooksData?.results ?? []);
  const failedWebhooks = webhooksList.filter(
    w => w.last_dispatch_failed === true || w.failed_count > 0
  ).length;

  function badge(item) {
    if (item.countBadge && suppressionCount > 0) {
      return (
        <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full text-xs font-bold min-w-[1.25rem]"
              style={{ background: 'var(--nav-active-bg)', color: 'var(--nav-active-text)', opacity: 0.85 }}>
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
    <aside className="w-56 flex flex-col shrink-0 transition-colors duration-200"
           style={{ background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border)' }}>

      {/* Logo */}
      <div className="px-4 py-4 flex items-center gap-2.5 border-b"
           style={{ borderColor: 'var(--border)' }}>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 shrink-0">
          <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
        </span>
        <span className="text-base font-bold tracking-tight" style={{ color: 'var(--text-head)' }}>
          WebMail
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto space-y-0.5">
        <p className="px-4 pt-2 pb-1.5 text-xs font-semibold uppercase tracking-widest"
           style={{ color: 'var(--sidebar-label)' }}>
          Sending
        </p>
        <div className="space-y-0.5 mb-2">
          {SENDING.map(item => (
            <NavItem key={item.to} to={item.to} label={item.label} badge={badge(item)} />
          ))}
        </div>

        <div className="mx-4 my-2 border-t" style={{ borderColor: 'var(--sidebar-divider)' }} />

        <p className="px-4 pb-1.5 text-xs font-semibold uppercase tracking-widest"
           style={{ color: 'var(--sidebar-label)' }}>
          Config
        </p>
        <div className="space-y-0.5">
          {CONFIG.map(item => (
            <NavItem key={item.to} to={item.to} label={item.label} badge={badge(item)} />
          ))}
        </div>
      </nav>
    </aside>
  );
}
