import client from './client';

export const listContactEngagement = (params = {}) =>
  client.get('/contacts/engagement/', { params });
