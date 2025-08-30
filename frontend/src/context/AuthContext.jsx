import React, { createContext, useState, useEffect, useContext } from "react";
import { me, login as apiLogin, logout as apiLogout } from "../api/apiClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 앱이 처음 로드될 때 토큰 유효성을 검사합니다.
    const checkUser = async () => {
      try {
        const userData = await me();
        setUser(userData);
      } catch (error) {
        // 유효한 토큰이 없으면 사용자는 null 상태를 유지합니다.
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    checkUser();
  }, []);

  const login = async (credentials) => {
    await apiLogin(credentials);
    const userData = await me();
    setUser(userData);
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };
  
  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth는 반드시 AuthProvider 안에서 사용해야 합니다.");
  }
  return context;
};
