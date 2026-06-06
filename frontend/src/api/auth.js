import client from './client';

export const login = (email, password) =>
  client.post('/auth/login/', { email, password });

export const signup = (email, password) =>
  client.post('/auth/register/', { email, password, password_confirm: password });

export const logout = () => client.post('/auth/logout/');

export const verifyEmail = (token) =>
  client.post('/auth/verify-email/', { token });

export const requestPasswordReset = (email) =>
  client.post('/auth/password-reset/', { email });

export const confirmPasswordReset = (token, password) =>
  client.post('/auth/password-reset/confirm/', { token, password });

export const getProfile = () => client.get('/auth/me/');
export const updateProfile = (data) => client.patch('/auth/me/', data);
export const deleteAccount = () => client.delete('/auth/me/');

export const listApiKeys = () => client.get('/auth/api-keys/');
export const createApiKey = (name) => client.post('/auth/api-keys/', { name });
export const revokeApiKey = (id) => client.delete(`/auth/api-keys/${id}/`);
