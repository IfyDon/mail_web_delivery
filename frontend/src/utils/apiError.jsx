/**
 * Extract a human-readable message from an API error response.
 * Handles both our custom envelope  { errors: [{field, message}] }
 * and plain DRF formats  { detail } / { field: ["msg"] }.
 */
export function parseApiError(err, fallback = 'Something went wrong. Please try again.') {
  const data = err?.response?.data;
  if (!data) return fallback;

  // Custom exception handler envelope
  if (Array.isArray(data.errors) && data.errors.length > 0) {
    const msg = data.errors[0].message;
    if (msg?.toLowerCase().includes('already exists')) {
      return 'This item already exists.';
    }
    return msg || fallback;
  }

  // Plain DRF { detail: "..." }
  if (typeof data.detail === 'string') return data.detail;

  // Plain DRF field errors { fieldName: ["msg", ...] }
  for (const val of Object.values(data)) {
    if (Array.isArray(val) && val.length > 0) return String(val[0]);
    if (typeof val === 'string') return val;
  }

  return fallback;
}

/** Specialised version that makes the "already exists" message domain-specific. */
export function parseDomainError(err) {
  const data = err?.response?.data;
  const msg = Array.isArray(data?.errors) ? data.errors[0]?.message : null;
  if (msg?.toLowerCase().includes('already exists')) {
    return 'This domain is already registered. Each domain can only belong to one account.';
  }
  return parseApiError(err, 'Failed to add domain.');
}
