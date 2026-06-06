import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './hooks/useAuth';
import PrivateRoute from './components/common/PrivateRoute';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Domains from './pages/Domains';
import Templates from './pages/Templates';
import Messages from './pages/Messages';
import Analytics from './pages/Analytics';
import Webhooks from './pages/Webhooks';
import Suppressions from './pages/Suppressions';
import ApiKeys from './pages/ApiKeys';
import Billing from './pages/Billing';
import Settings from './pages/Settings';
import TemplateEdit from './pages/TemplateEdit';
import MessageDetail from './pages/MessageDetail';
import Streams from './pages/Streams';
import Team from './pages/Team';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route element={<PrivateRoute />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/domains" element={<Domains />} />
              <Route path="/templates" element={<Templates />} />
              <Route path="/templates/:id" element={<TemplateEdit />} />
              <Route path="/messages" element={<Messages />} />
              <Route path="/messages/:id" element={<MessageDetail />} />
              <Route path="/streams" element={<Streams />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/webhooks" element={<Webhooks />} />
              <Route path="/suppressions" element={<Suppressions />} />
              <Route path="/api-keys" element={<ApiKeys />} />
              <Route path="/billing" element={<Billing />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/settings/team" element={<Team />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
