import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";

export default function ProtectedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
