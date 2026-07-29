import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/auth';
import apiClient from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const { data } = await authApi.me();
          setUser(data);
        } catch (error) {
          console.error("Failed to fetch user session", error);
          localStorage.removeItem('access_token');
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (email, password) => {
    const { data } = await authApi.login(email, password);
    localStorage.setItem('access_token', data.access_token);
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
    
    const userRes = await authApi.me();
    setUser(userRes.data);
    return userRes.data;
  };

  const signup = async (userData) => {
    return await authApi.signup(userData);
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (e) {
      console.error(e);
    } finally {
      localStorage.removeItem('access_token');
      delete apiClient.defaults.headers.common['Authorization'];
      setUser(null);
      window.location.href = '/login';
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
