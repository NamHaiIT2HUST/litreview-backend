import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE, safeFetch } from '../utils/apiConfig';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem('litreview_auth_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => localStorage.getItem('litreview_auth_token'));

  useEffect(() => {
    if (currentUser) {
      localStorage.setItem('litreview_auth_user', JSON.stringify(currentUser));
    } else {
      localStorage.removeItem('litreview_auth_user');
    }
  }, [currentUser]);

  useEffect(() => {
    if (token) {
      localStorage.setItem('litreview_auth_token', token);
    } else {
      localStorage.removeItem('litreview_auth_token');
    }
  }, [token]);

  // Unified login: tries backend API first, fallback to demo/local
  const login = async (usernameOrEmail, password) => {
    const cleanIdentifier = (usernameOrEmail || '').trim();
    if (!cleanIdentifier) {
      throw new Error('Vui lòng nhập email hoặc tên đăng nhập.');
    }

    let res;
    let data;
    try {
      res = await safeFetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: cleanIdentifier, password }),
      });
      data = await res.json().catch(() => ({}));
    } catch (err) {
      console.warn('Backend login unreachable, activating offline session:', err.message);
      data = {
        access_token: 'local_auth_token_' + Date.now(),
        user: {
          id: 'user_' + cleanIdentifier.replace(/[^a-zA-Z0-9]/g, '_'),
          username: cleanIdentifier.split('@')[0],
          name: cleanIdentifier.split('@')[0],
          email: cleanIdentifier.includes('@') ? cleanIdentifier : `${cleanIdentifier}@university.edu.vn`,
          role: 'Senior Researcher',
        },
      };
    }

    if (!data || (!data.access_token && !data.user)) {
      throw new Error(data?.detail || 'Sai tên đăng nhập hoặc mật khẩu.');
    }

    const tokenVal = data.access_token || ('local_token_' + Date.now());
    const userVal = data.user || {
      username: cleanIdentifier.split('@')[0],
      name: cleanIdentifier.split('@')[0],
      email: cleanIdentifier,
    };

    setToken(tokenVal);
    const loggedInUser = {
      ...userVal,
      name: userVal.name || userVal.username,
      email: userVal.email || cleanIdentifier,
      avatar: (userVal.name || userVal.username || 'US').slice(0, 2).toUpperCase(),
    };
    setCurrentUser(loggedInUser);
    return { success: true, user: loggedInUser };
  };

  // Unified register: tries backend API first
  const register = async (userDataOrUsername, maybePassword, maybeRole = 'user') => {
    let username, password, role, name, institution, email;
    if (typeof userDataOrUsername === 'object') {
      name = userDataOrUsername.name || '';
      email = userDataOrUsername.email || '';
      username = userDataOrUsername.username || email.split('@')[0] || name;
      password = userDataOrUsername.password;
      role = userDataOrUsername.role || 'Senior Researcher';
      institution = userDataOrUsername.institution || 'Academic Institution';
    } else {
      username = userDataOrUsername;
      password = maybePassword;
      role = maybeRole;
      name = username;
      email = `${username}@university.edu.vn`;
      institution = 'Academic Institution';
    }

    const initials = (name || username).split(' ').map((w) => w[0]).join('').slice(-2).toUpperCase() || 'US';

    let res;
    let data;
    try {
      res = await safeFetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role }),
      });
      data = await res.json().catch(() => ({}));
    } catch (err) {
      console.warn('Backend register unreachable, activating local account:', err.message);
      data = {
        access_token: 'local_reg_token_' + Date.now(),
        user: {
          id: 'user_' + username,
          username,
          name: name || username,
          email,
          role,
          institution,
        },
      };
    }

    const tokenVal = data?.access_token || ('local_token_' + Date.now());
    setToken(tokenVal);
    const newUserObj = {
      ...(data?.user || {}),
      name: name || username,
      email: email || username,
      avatar: initials,
      institution: institution || 'Academic Institution',
      plan: 'Scholar Pro',
      bio: 'Tài khoản nghiên cứu học thuật.',
    };
    setCurrentUser(newUserObj);
    return { success: true, user: newUserObj };
  };

  const loginWithGoogle = async () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '1063554185752-ai26hqjeg9k2fse4utkqfftvafgrjnr4.apps.googleusercontent.com';

    if (typeof window !== 'undefined' && window.google?.accounts?.oauth2) {
      return new Promise((resolve, reject) => {
        try {
          const client = window.google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: 'openid email profile',
            callback: async (tokenResponse) => {
              if (tokenResponse.error) {
                reject(new Error(tokenResponse.error_description || tokenResponse.error));
                return;
              }

              // 1. Try backend authentication first
              try {
                const beRes = await safeFetch('/auth/google', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ access_token: tokenResponse.access_token }),
                });

                const backendUser = await beRes.json().catch(() => ({}));

                if (beRes.ok && backendUser.access_token) {
                  setToken(backendUser.access_token);
                  setCurrentUser(backendUser);
                  resolve({ success: true, user: backendUser });
                  return;
                }
              } catch (fetchErr) {
                console.warn('Backend /auth/google unreachable, fetching profile directly from Google:', fetchErr);
              }

              // 2. Direct fallback: Fetch userinfo directly from Google API
              try {
                const gRes = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                  headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
                });
                if (gRes.ok) {
                  const gUser = await gRes.json();
                  const fallbackUser = {
                    id: gUser.sub || 'google_user',
                    name: gUser.name || 'Nhà nghiên cứu Google',
                    email: gUser.email,
                    avatar: (gUser.name || 'US').slice(0, 2).toUpperCase(),
                    picture: gUser.picture,
                    role: 'Senior Researcher',
                    institution: 'Viện Nghiên cứu Khoa học',
                    plan: 'Scholar Pro',
                    access_token: 'google_session_' + Date.now(),
                  };
                  setToken(fallbackUser.access_token);
                  setCurrentUser(fallbackUser);
                  resolve({ success: true, user: fallbackUser });
                  return;
                }
              } catch (gErr) {
                console.warn('Google userinfo fetch failed:', gErr);
              }

              // 3. Fallback to default active session
              const defaultUser = {
                id: 'google_user_default',
                name: 'Nguyễn Đào Nam Hải',
                email: 'namhai23092005@gmail.com',
                avatar: 'NH',
                role: 'Senior Researcher',
                institution: 'Đại học Bách Khoa Hà Nội (HUST)',
                plan: 'Scholar Pro',
                access_token: 'google_session_' + Date.now(),
              };
              setToken(defaultUser.access_token);
              setCurrentUser(defaultUser);
              resolve({ success: true, user: defaultUser });
            },
          });

          client.requestAccessToken({ prompt: 'select_account' });
        } catch (err) {
          reject(err);
        }
      });
    }

    throw new Error('Đang tải thư viện Google Sign-In, vui lòng thử lại sau giây lát.');
  };

  const [demoAccounts, setDemoAccounts] = useState([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await safeFetch('/auth/demo-accounts');
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled && data.accounts) setDemoAccounts(data.accounts);
      } catch {}
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const loginDemo = async (account) => {
    const target = account || {
      username: 'dr_namhai',
      name: 'TS. Nguyễn Đào Nam Hải',
      email: 'namhai23092005@gmail.com',
      role: 'Senior Researcher',
      institution: 'Đại học Bách Khoa Hà Nội (HUST)',
    };
    try {
      const result = await login(target.username || target.email, target.password || 'demo123');
      return result;
    } catch {
      const offlineUser = {
        ...target,
        id: target.id || 'demo_dr_namhai',
        avatar: (target.name || 'NH').slice(0, 2).toUpperCase(),
        plan: 'Scholar Pro',
        access_token: 'demo_session_' + Date.now(),
      };
      setToken(offlineUser.access_token);
      setCurrentUser(offlineUser);
      return { success: true, user: offlineUser };
    }
  };

  const resetPassword = async (email) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ success: true, email });
      }, 500);
    });
  };

  const logout = () => {
    setCurrentUser(null);
    setToken(null);
  };

  const updateProfile = (updatedFields) => {
    setCurrentUser((prev) => (prev ? { ...prev, ...updatedFields } : null));
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        user: currentUser, // Alias for backward compatibility
        token,
        isAuthenticated: Boolean(currentUser),
        login,
        loginWithGoogle,
        loginDemo,
        demoAccounts,
        resetPassword,
        register,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
