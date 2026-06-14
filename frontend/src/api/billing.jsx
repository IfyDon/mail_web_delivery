import client from './client';

export const getBillingOverview = () => client.get('/billing/');
export const getInvoices = () => client.get('/billing/invoices/');
export const createCheckoutSession = (planSlug) =>
  client.post('/billing/checkout/', { plan_slug: planSlug });
export const createPortalSession = () => client.post('/billing/portal/', {});
