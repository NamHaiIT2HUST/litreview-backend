import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE } from '../utils/apiConfig';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('litreview_auth_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('litreview_auth_token'));

  useEffect(() => {
    if (user) {
      localStorage.setItem('litreview_auth_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('litreview_auth_user');
    }
  }, [user]);

  useEffect(() => {
    if (token) {
      localStorage.setItem('litreview_auth_token', token);
    } else {
      localStorage.removeItem('litreview_auth_token');
    }
  }, [token]);

  const login = async (username, password) => {
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.');
      }
      setToken(data.access_token);
      setUser(data.user);
      return data;
    } catch (err) {
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.message.includes('Load failed')) {
        throw new Error('Không thể kết nối đến máy chủ Backend (FastAPI). Vui lòng đảm bảo server backend đang chạy.');
      }
      throw err;
    }
  };

  const register = async (username, password, role = 'user') => {
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.');
      }
      setToken(data.access_token);
      setUser(data.user);
      return data;
    } catch (err) {
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.message.includes('Load failed')) {
        throw new Error('Không thể kết nối đến máy chủ Backend (FastAPI). Vui lòng đảm bảo server backend đang chạy.');
      }
      throw err;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
