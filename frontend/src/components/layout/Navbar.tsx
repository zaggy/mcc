import { Bell, LogOut, User } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { useNavigate } from "react-router-dom";

export default function Navbar() {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-6">
      <div />
      <div className="flex items-center gap-4">
        <button
          className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
