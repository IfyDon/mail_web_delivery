import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useApiQuery(key, fetcher, options = {}) {
  return useQuery({
    queryKey: Array.isArray(key) ? key : [key],
    queryFn: fetcher,
    ...options,
  });
}

export function useApiMutation(mutFn, { invalidates = [], ...options } = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mutFn,
    onSuccess: (...args) => {
      invalidates.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      options.onSuccess?.(...args);
    },
    ...options,
  });
}
