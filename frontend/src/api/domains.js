import client from './client';

export const listDomains = () => client.get('/domains/');
export const createDomain = (name) => client.post('/domains/', { name });
export const getDomain = (id) => client.get(`/domains/${id}/`);
export const deleteDomain = (id) => client.delete(`/domains/${id}/`);
export const verifyDomain = (id) => client.post(`/domains/${id}/verify/`);
