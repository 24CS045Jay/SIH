import { createContext, useContext, useState, ReactNode } from "react";
import { User } from "../types";
import { TOKEN_KEY, USER_KEY } from "../api/client";

interface AuthContextValue {
  user: User | null;
  token: string;
  onLogin: (user: User, token: string) => void;
  onLogout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  });
  const [token, setToken] = useState<string>(() => localStorage.getItem(TOKEN_KEY) ?? "");

  function onLogin(nextUser: User, nextToken: string) {
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    localStorage.setItem(TOKEN_KEY, nextToken);
    setUser(nextUser);
    setToken(nextToken);
  }

  function onLogout() {
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setToken("");
  }

  return (
    <AuthContext.Provider value={{ user, token, onLogin, onLogout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
