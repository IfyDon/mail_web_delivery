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

export const confirmPasswordReset = (uid, token, newPassword) =>
  client.post('/auth/password-reset/confirm/', { uid, token, new_password: newPassword });

export const getProfile = () => client.get('/auth/me/');
export const updateProfile = (data) => client.patch('/auth/me/', data);
export const deleteAccount = () => client.delete('/auth/me/');

export const listApiKeys = () => client.get('/accounts/api-keys/');
export const createApiKey = (name) => client.post('/accounts/api-keys/', { name });
export const revokeApiKey = (id) => client.post(`/accounts/api-keys/${id}/revoke/`);
