import { createContext, type ReactNode } from 'react';

export interface AuthContextValue {
  user: { id: string; name: string; email: string };
  loading: false;
}

export const AuthContext = createContext<AuthContextValue>({
  user: { id: 'local', name: 'Kaushik', email: 'local@taskyn' },
  loading: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <AuthContext.Provider value={{ user: { id: 'local', name: 'Kaushik', email: 'local@taskyn' }, loading: false }}>
      {children}
    </AuthContext.Provider>
  );
}
