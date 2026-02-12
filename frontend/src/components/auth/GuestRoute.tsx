import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";

export default function GuestRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);

  if (isLoggedIn) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
