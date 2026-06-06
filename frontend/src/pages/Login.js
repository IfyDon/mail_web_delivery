import LoginForm from '../components/auth/LoginForm';

export default function Login() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 w-full max-w-sm">
        <h1 className="text-xl font-semibold text-gray-900 mb-6 text-center">
          Sign in to WebMail
        </h1>
        <LoginForm />
      </div>
    </div>
  );
}
