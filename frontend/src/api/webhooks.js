import client from './client';

export const listWebhooks = () => client.get('/webhooks/');
export const createWebhook = (data) => client.post('/webhooks/', data);
export const updateWebhook = (id, data) => client.patch(`/webhooks/${id}/`, data);
export const deleteWebhook = (id) => client.delete(`/webhooks/${id}/`);
export const testWebhook = (id) => client.post(`/webhooks/${id}/test/`);
export const getWebhookLogs = (id) => client.get(`/webhooks/${id}/logs/`);
export const retryWebhook = (id) => client.post(`/webhooks/${id}/retry/`);
