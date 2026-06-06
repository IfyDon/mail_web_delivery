import client from './client';

export const listSuppressions = (params) =>
  client.get('/suppressions/', { params });

export const createSuppression = (data) =>
  client.post('/suppressions/', data);

export const deleteSuppression = (email) =>
  client.delete(`/suppressions/${encodeURIComponent(email)}/`);
