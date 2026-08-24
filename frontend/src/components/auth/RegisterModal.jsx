import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { X, Check } from 'lucide-react';

export default function RegisterModal({ isOpen = true, onClose, onSwitchToLogin }) {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const validatePassword = (pass) => {
    return pass.length >= 8 && /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pass);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!validatePassword(password)) {
      setError('Mật khẩu phải có ít nhất 8 ký tự và chứa ít nhất 1 ký tự đặc biệt.');
      return;
    }

    setLoading(true);
    try {
      await register(username, password);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md p-8 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800">
        <button onClick={onClose} className="absolute top-4 right-4 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
          <X className="w-6 h-6" />
        </button>
        <h2 className="text-2xl font-display font-black mb-6 text-slate-900 dark:text-white">Đăng Ký Tài Khoản</h2>
        {error && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-xl text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tên đăng nhập</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Mật khẩu</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
            <ul className="mt-2 text-xs text-slate-500 space-y-1">
              <li className={`flex items-center gap-1 ${password.length >= 8 ? 'text-emerald-500' : ''}`}>
                <Check className="w-3 h-3" /> Ít nhất 8 ký tự
              </li>
              <li className={`flex items-center gap-1 ${/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password) ? 'text-emerald-500' : ''}`}>
                <Check className="w-3 h-3" /> Chứa ký tự đặc biệt
              </li>
            </ul>
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3 mt-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/30 transition-all disabled:opacity-50"
          >
            {loading ? 'Đang xử lý...' : 'ĐĂNG KÝ'}
          </button>
        </form>
        <div className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
          Đã có tài khoản?{' '}
          <button onClick={onSwitchToLogin} className="text-emerald-600 dark:text-emerald-400 font-bold hover:underline">
            Đăng nhập ngay
          </button>
        </div>
      </div>
    </div>
  );
}
