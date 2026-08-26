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

  // Unified login: authenticates against the backend only. A backend that is
  // unreachable or that rejects the credentials must fail the login, not hand
  // out a fabricated local session — a fake session cannot call a single
  // authenticated API now that the backend actually verifies tokens.
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
      throw new Error('Không thể kết nối tới máy chủ. Vui lòng thử lại sau.');
    }

    if (!res.ok || !data.access_token) {
      throw new Error(data?.detail || 'Sai tên đăng nhập hoặc mật khẩu.');
    }

    const tokenVal = data.access_token;
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
      throw new Error('Không thể kết nối tới máy chủ. Vui lòng thử lại sau.');
    }

    if (!res.ok || !data.access_token) {
      throw new Error(data?.detail || 'Không thể tạo tài khoản. Vui lòng thử lại.');
    }

    const tokenVal = data.access_token;
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

              // The backend is the only party that verifies this token against
              // Google and issues a real session. A frontend-only fallback
              // (calling Google directly, or worse, a hardcoded default user)
              // would let sign-in "succeed" without a token any authenticated
              // API route accepts, and previously did so as a fixed identity
              // regardless of who was actually signing in.
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

                reject(new Error(backendUser?.detail || 'Không thể xác thực đăng nhập Google. Vui lòng thử lại.'));
              } catch (fetchErr) {
                reject(new Error('Không thể kết nối tới máy chủ để xác thực Google. Vui lòng thử lại sau.'));
              }
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
    if (!account) {
      throw new Error('Không có tài khoản demo khả dụng lúc này.');
    }
    // Demo accounts are ordinary user rows (see GET /auth/demo-accounts): this
    // performs a real login and receives a real access token, so it is
    // authorised exactly like any other account rather than only looking so.
    return login(account.username || account.email, account.password || 'demo123');
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
