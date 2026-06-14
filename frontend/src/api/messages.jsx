import client from './client';

export const listMessages = (params) => client.get('/messages/', { params });
export const getMessage = (id) => client.get(`/messages/${id}/`);
export const resendMessage = (id) => client.post(`/messages/${id}/resend/`);
export const sendMessage = (data) => client.post('/send/', data);
export const sendBatch = (messages) => client.post('/send/batch/', { messages });
