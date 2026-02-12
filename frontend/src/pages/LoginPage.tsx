import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const navigate = useNavigate();
  const { isLoading, error, requires2fa, login, verify2fa, clearError } =
    useAuthStore();
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [twoFactorCode, setTwoFactorCode] = useState("");

  // Redirect if already logged in after successful auth
  if (isLoggedIn) {
    navigate("/", { replace: true });
    return null;
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    await login(username, password);
  };

  const handle2fa = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    await verify2fa(twoFactorCode);
  };

  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Mission Control Center</CardTitle>
        <CardDescription>
          {requires2fa
            ? "Enter your two-factor authentication code"
            : "Sign in to your account"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive-foreground">
            {error}
          </div>
        )}

        {!requires2fa ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        ) : (
          <form onSubmit={handle2fa} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="code">Authentication Code</Label>
              <Input
                id="code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="000000"
                value={twoFactorCode}
                onChange={(e) => setTwoFactorCode(e.target.value)}
                required
                autoFocus
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Verifying..." : "Verify"}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
