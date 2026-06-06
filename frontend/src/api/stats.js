import client from './client';

export const getStats = (params) => client.get('/stats/', { params });

export const exportStats = (params) =>
  client.get('/stats/export/', { params, responseType: 'blob' });
