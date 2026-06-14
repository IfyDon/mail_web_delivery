import SignupForm from '../components/auth/SignupForm';

export default function Signup() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 w-full max-w-sm">
        <h1 className="text-xl font-semibold text-gray-900 mb-6 text-center">
          Create your account
        </h1>
        <SignupForm />
      </div>
    </div>
  );
}
