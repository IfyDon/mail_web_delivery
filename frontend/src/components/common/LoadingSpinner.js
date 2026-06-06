export default function LoadingSpinner({ className = 'h-8 w-8' }) {
  return (
    <div className={`animate-spin rounded-full border-2 border-gray-200 border-t-indigo-600 ${className}`} />
  );
}
