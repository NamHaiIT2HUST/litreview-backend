import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE } from '../utils/apiConfig';

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

    // The backend is the only authority on identity. The previous version fell
    // back to a demo list, a localStorage user list, and finally to inventing a
    // session for any identifier typed in — signing in anyone without ever
    // checking a password, and storing the literal string
    // 'local_session_token' as the access token.
    let res;
    try {
      res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: cleanIdentifier, password }),
      });
    } catch (err) {
      console.warn('Backend login attempt failed:', err.message);
      throw new Error('Không kết nối được máy chủ. Vui lòng thử lại.');
    }

    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.access_token || !data.user) {
      throw new Error(data.detail || 'Sai tên đăng nhập hoặc mật khẩu.');
    }

    setToken(data.access_token);
    const loggedInUser = {
      ...data.user,
      name: data.user.name || data.user.username,
      email: data.user.email || cleanIdentifier,
      avatar: (data.user.name || data.user.username || 'US').slice(0, 2).toUpperCase(),
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

    const initials = (name || username).split(' ').map(w => w[0]).join('').slice(-2).toUpperCase() || 'US';

    // Registration must succeed on the backend to count. Previously the account
    // was written to localStorage (including the plaintext password) and the
    // user was signed in locally even when the backend call failed.
    let res;
    try {
      res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role }),
      });
    } catch (err) {
      console.warn('Backend register failed:', err.message);
      throw new Error('Không kết nối được máy chủ. Vui lòng thử lại.');
    }

    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.access_token || !data.user) {
      throw new Error(data.detail || 'Không tạo được tài khoản.');
    }

    setToken(data.access_token);
    const newUserObj = {
      ...data.user,
      name: name || data.user.username,
      email: email || data.user.username,
      avatar: initials,
      institution: institution || 'Academic Institution',
      plan: 'Scholar Pro',
      bio: 'Tài khoản nghiên cứu học thuật.',
    };
    setCurrentUser(newUserObj);
    return { success: true, user: newUserObj };
  };

  const loginWithGoogle = async () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      // Graceful fallback to demo researcher account
      const mockUser = {
        id: 'user_researcher_01',
        email: 'researcher.demo@litreview.ai',
        name: 'TS. Nguyễn Hoàng Nam',
        institution: 'Viện Khoa học & Công nghệ',
        role: 'researcher',
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
        bio: 'Nhà nghiên cứu Khoa học Dữ liệu & Y sinh.',
      };
      setCurrentUser(mockUser);
      localStorage.setItem('litreview_user', JSON.stringify(mockUser));
      return { success: true, user: mockUser };
    }

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

              try {
                // The backend re-verifies this token with Google and issues our
                // own access token. Its response is the only accepted identity:
                // deriving a session from the client-side Google profile would
                // produce a "logged in" user the API cannot authorise.
                const beRes = await fetch(`${API_BASE}/auth/google`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ access_token: tokenResponse.access_token }),
                });

                const backendUser = await beRes.json().catch(() => ({}));

                if (!beRes.ok || !backendUser.access_token) {
                  reject(
                    new Error(
                      backendUser.detail || 'Máy chủ không xác thực được tài khoản Google này.'
                    )
                  );
                  return;
                }

                setToken(backendUser.access_token);
                setCurrentUser(backendUser);
                resolve({ success: true, user: backendUser });
              } catch (err) {
                reject(err);
              }
            },
          });

          client.requestAccessToken({ prompt: 'select_account' });
        } catch (err) {
          reject(err);
        }
      });
    }

    throw new Error('Không tải được Google Sign-In. Vui lòng kiểm tra kết nối mạng.');
  };

  // Ready-made researcher profiles for trying the app without registering.
  // The backend serves these only in development and returns an empty list
  // otherwise, so the picker simply does not appear anywhere else.
  const [demoAccounts, setDemoAccounts] = useState([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/demo-accounts`);
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) setDemoAccounts(data.accounts || []);
      } catch {
        // No demo accounts offered. Not an error worth surfacing: the sign-in
        // form works regardless.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const loginDemo = async (account) => {
    // A real login against a real account, not a client-side session. The
    // previous version set React state from a hardcoded profile and stored the
    // string 'local_session_token', which produced a "signed in" user that no
    // authenticated endpoint would accept.
    const result = await login(account.username, account.password);
    return {
      ...result,
      user: { ...result.user, ...account, password: undefined },
    };
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
