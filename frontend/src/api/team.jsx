import client from './client';

export const listTeam = () => client.get('/team/');
export const inviteMember = (data) => client.post('/team/', data);
export const updateMember = (id, data) => client.patch(`/team/${id}/`, data);
export const removeMember = (id) => client.delete(`/team/${id}/`);
