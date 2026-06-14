import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Opens a Server-Sent Events connection to /api/v1/messages/stream/ and
 * invalidates the React Query 'messages' cache whenever any message status
 * changes. The connection closes after 5 minutes (server-side) and the hook
 * automatically reconnects after a short delay.
 */
export function useMessageStream() {
  const qc = useQueryClient();

  useEffect(() => {
    let active = true;
    let retryTimer = null;

    async function connect() {
      const token = localStorage.getItem('api_key');
      if (!token) return;

      const ctrl = new AbortController();

      try {
        const res = await fetch(`${BASE_URL}/messages/stream/`, {
          headers: { Authorization: `Token ${token}` },
          signal: ctrl.signal,
        });

        if (!res.ok || !res.body) return;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';

        while (active) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split('\n');
          buf = lines.pop() ?? '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              // Any status change — invalidate the list so the table refreshes
              qc.invalidateQueries({ queryKey: ['messages'] });
            }
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') return;
        // Network error — retry after 10 s
      }

      if (active) {
        retryTimer = setTimeout(connect, 10_000);
      }
    }

    connect();

    return () => {
      active = false;
      clearTimeout(retryTimer);
    };
  }, [qc]);
}
