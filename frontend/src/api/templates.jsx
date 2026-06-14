import client from './client';

export const listTemplates = () => client.get('/templates/');
export const createTemplate = (data) => client.post('/templates/', data);
export const getTemplate = (id) => client.get(`/templates/${id}/`);
export const updateTemplate = (id, data) => client.put(`/templates/${id}/`, data);
export const deleteTemplate = (id) => client.delete(`/templates/${id}/`);
export const sendTestEmail = (id, recipient) =>
  client.post(`/templates/${id}/test/`, { recipient });
