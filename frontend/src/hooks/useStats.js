import { useQuery } from '@tanstack/react-query';
import { getStats } from '../api/stats';

export function useStats(range = '7d', stream = '') {
  return useQuery({
    queryKey: ['stats', range, stream],
    queryFn: () =>
      getStats({ date_range: range, ...(stream ? { stream } : {}) }).then((r) => r.data),
    staleTime: 60_000,
  });
}
