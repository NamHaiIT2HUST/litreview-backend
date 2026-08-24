import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const DEMO_USERS = [
  {
    id: 'user_researcher_01',
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

  useEffect(() => {
    if (currentUser) {
      localStorage.setItem('litreview_auth_user', JSON.stringify(currentUser));
    } else {
      localStorage.removeItem('litreview_auth_user');
    }
  }, [currentUser]);

  const login = (email, password) => {
    // Check if matches demo users or create session
    const foundDemo = DEMO_USERS.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (foundDemo) {
      setCurrentUser(foundDemo);
      return { success: true, user: foundDemo };
    }

    const nameFromEmail = email.split('@')[0].replace(/[._]/g, ' ');
    const initials = nameFromEmail.slice(0, 2).toUpperCase();
    const newUser = {
      id: `user_${Date.now()}`,
      name: nameFromEmail.charAt(0).toUpperCase() + nameFromEmail.slice(1),
      email,
      avatar: initials || 'US',
      role: 'Academic Researcher',
      institution: 'Independent Research',
      plan: 'Scholar Standard',
      bio: 'Nhà nghiên cứu khoa học độc lập.',
    };
    setCurrentUser(newUser);
    return { success: true, user: newUser };
  };

  const loginWithGoogle = async (customGoogleUser = null) => {
    if (customGoogleUser) {
      setCurrentUser(customGoogleUser);
      return { success: true, user: customGoogleUser };
    }

    const clientId =
      import.meta.env.VITE_GOOGLE_CLIENT_ID ||
      '447985190531-p2gko4a06q485g1mku819bno42qsifen.apps.googleusercontent.com';

    // 1. If Google Identity Services (GIS) SDK is loaded on window
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
                // Fetch verified profile directly from Google
                const userinfoRes = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                  headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
                });
                const googleProfile = await userinfoRes.json();

                // Send to backend API for verification and database registration
                let backendUser = null;
                try {
                  const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';
                  const beRes = await fetch(`${apiBase}/auth/google`, {
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
                  console.warn('Backend auth sync warning (using client profile):', e);
                }

                const finalUser = backendUser || {
                  id: googleProfile.sub || `google_${Date.now()}`,
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

    // 2. Fallback if GIS SDK not yet available: prompt direct account
    const fallbackUser = {
      id: `google_${Date.now()}`,
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

  const resetPassword = async (email) => {
    // Simulate recovery link dispatch
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ success: true, email });
      }, 500);
    });
  };

  const loginDemo = (profileId) => {
    const user = DEMO_USERS.find(u => u.id === profileId) || DEMO_USERS[0];
    setCurrentUser(user);
    return { success: true, user };
  };

  const register = ({ name, email, password, institution, role }) => {
    const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
    const newUser = {
      id: `user_${Date.now()}`,
      name,
      email,
      avatar: initials || 'US',
      role: role || 'Researcher',
      institution: institution || 'Academic Institution',
      plan: 'Scholar Pro',
      bio: 'Nhà nghiên cứu khoa học.',
    };
    setCurrentUser(newUser);
    return { success: true, user: newUser };
  };

  const logout = () => {
    setCurrentUser(null);
  };

  const updateProfile = (updatedFields) => {
    setCurrentUser(prev => prev ? { ...prev, ...updatedFields } : null);
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
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
