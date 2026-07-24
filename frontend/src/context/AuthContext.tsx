import { createContext, useContext, useState, type ReactNode } from "react";
import type { UserRead } from "../api/types";

interface AuthContextValue {
  user: UserRead | null;
  isAuthenticated: boolean;
  login: (token: string, user: UserRead) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function loadStoredUser(): UserRead | null {
  const raw = localStorage.getItem("bidops_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserRead;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(loadStoredUser());

  const login = (token: string, newUser: UserRead) => {
    localStorage.setItem("bidops_token", token);
    localStorage.setItem("bidops_user", JSON.stringify(newUser));
    setUser(newUser);
  };

  const logout = () => {
    localStorage.removeItem("bidops_token");
    localStorage.removeItem("bidops_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
