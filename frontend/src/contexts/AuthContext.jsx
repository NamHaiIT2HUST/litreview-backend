import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE } from '../utils/apiConfig';

const AuthContext = createContext(null);

export const DEMO_USERS = [
  {
    id: 'user_researcher_01',
    username: 'hai.nguyen',
    name: 'TS. Nguyễn Hải',
    email: 'hai.nguyen@vinuni.edu.vn',
    avatar: 'NH',
    role: 'Senior AI Researcher',
    institution: 'VinUniversity & VinAI Research',
    plan: 'Academic Enterprise',
    bio: 'Nghiên cứu thị giác máy tính & mô hình chẩn đoán y sinh học.',
  },
  {
    id: 'user_student_02',
    username: 'minh.pham',
    name: 'Minh Phạm',
    email: 'minh.pham@hust.edu.vn',
    avatar: 'MP',
    role: 'Graduate Researcher',
    institution: 'HUST - Đại học Bách Khoa Hà Nội',
    plan: 'Scholar Pro',
    bio: 'Học viên cao học chuyên ngành Khoa học Dữ liệu & Xử lý Ngôn ngữ Tự nhiên.',
  },
];

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
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: usernameOrEmail, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.user) {
        setToken(data.access_token);
        const loggedInUser = {
          ...data.user,
          name: data.user.name || data.user.username,
          avatar: (data.user.username || 'US').slice(0, 2).toUpperCase(),
        };
        setCurrentUser(loggedInUser);
        return { success: true, user: loggedInUser };
      }
      if (!res.ok) {
        throw new Error(data.detail || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.');
      }
    } catch (err) {
      if (err.message && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
        throw err;
      }
      // Fallback demo/local match if backend offline
      const foundDemo = DEMO_USERS.find(
        (u) =>
          u.email.toLowerCase() === usernameOrEmail.toLowerCase() ||
          u.username.toLowerCase() === usernameOrEmail.toLowerCase()
      );
      if (foundDemo) {
        setCurrentUser(foundDemo);
        return { success: true, user: foundDemo };
      }
      throw err;
    }
  };

  // Unified register: tries backend API first
  const register = async (userDataOrUsername, maybePassword, maybeRole = 'user') => {
    let username, password, role, name, institution;
    if (typeof userDataOrUsername === 'object') {
      name = userDataOrUsername.name;
      username = userDataOrUsername.username || userDataOrUsername.email?.split('@')[0] || name;
      password = userDataOrUsername.password;
      role = userDataOrUsername.role || 'user';
      institution = userDataOrUsername.institution || 'Academic Institution';
    } else {
      username = userDataOrUsername;
      password = maybePassword;
      role = maybeRole;
      name = username;
      institution = 'Academic Institution';
    }

    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.user) {
        setToken(data.access_token);
        const registeredUser = {
          ...data.user,
          name: name || data.user.username,
          institution,
          avatar: (username || 'US').slice(0, 2).toUpperCase(),
        };
        setCurrentUser(registeredUser);
        return { success: true, user: registeredUser };
      }
      if (!res.ok) {
        throw new Error(data.detail || 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.');
      }
    } catch (err) {
      if (err.message && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError')) {
        throw err;
      }
      // Offline fallback
      const initials = (name || username).slice(0, 2).toUpperCase();
      const fallbackUser = {
        id: `user_${Date.now()}`,
        username,
        name,
        avatar: initials || 'US',
        role: role || 'user',
        institution: institution || 'Academic Institution',
        plan: 'Scholar Standard',
      };
      setCurrentUser(fallbackUser);
      return { success: true, user: fallbackUser };
    }
  };

  const loginWithGoogle = async (customGoogleUser = null) => {
    if (customGoogleUser) {
      setCurrentUser(customGoogleUser);
      return { success: true, user: customGoogleUser };
    }

    const clientId =
      import.meta.env.VITE_GOOGLE_CLIENT_ID ||
      '447985190531-p2gko4a06q485g1mku819bno42qsifen.apps.googleusercontent.com';

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
                const userinfoRes = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                  headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
                });
                const googleProfile = await userinfoRes.json();

                let backendUser = null;
                try {
                  const beRes = await fetch(`${API_BASE}/auth/google`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      access_token: tokenResponse.access_token,
                      email: googleProfile.email,
                      name: googleProfile.name,
                      picture: googleProfile.picture,
                      sub: googleProfile.sub,
                    }),
                  });
                  if (beRes.ok) {
                    backendUser = await beRes.json();
                  }
                } catch (e) {
                  console.warn('Backend auth sync warning:', e);
                }

                const finalUser = backendUser || {
                  id: googleProfile.sub || `google_${Date.now()}`,
                  username: googleProfile.email?.split('@')[0],
                  name: googleProfile.name || googleProfile.email.split('@')[0],
                  email: googleProfile.email,
                  avatar: googleProfile.name
                    ? googleProfile.name
                        .split(' ')
                        .map((w) => w[0])
                        .join('')
                        .slice(0, 2)
                        .toUpperCase()
                    : 'G',
                  picture: googleProfile.picture,
                  role: 'Senior Researcher',
                  institution: googleProfile.email.includes('@')
                    ? googleProfile.email.split('@')[1].toUpperCase()
                    : 'Academic Institution',
                  plan: 'Scholar Pro',
                  bio: 'Tài khoản học thuật xác thực qua Google OAuth 2.0.',
                  provider: 'google',
                };

                setCurrentUser(finalUser);
                resolve({ success: true, user: finalUser });
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

    const fallbackUser = {
      id: `google_${Date.now()}`,
      username: 'scholar.researcher',
      name: 'Google Scholar Researcher',
      email: 'scholar.researcher@gmail.com',
      avatar: 'G',
      picture: 'https://lh3.googleusercontent.com/a/default-user=s96-c',
      role: 'Senior Researcher',
      institution: 'Academic Google Workspace',
      plan: 'Scholar Pro',
      bio: 'Tài khoản học thuật xác thực qua Google Workspace.',
      provider: 'google',
    };
    setCurrentUser(fallbackUser);
    return { success: true, user: fallbackUser };
  };

  const loginDemo = (profileId) => {
    const u = DEMO_USERS.find((item) => item.id === profileId) || DEMO_USERS[0];
    setCurrentUser(u);
    return { success: true, user: u };
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
        resetPassword,
        register,
        logout,
        updateProfile,
        demoUsers: DEMO_USERS,
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
