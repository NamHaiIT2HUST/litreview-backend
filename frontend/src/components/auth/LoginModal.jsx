import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { X } from 'lucide-react';

export default function LoginModal({ isOpen = true, onClose, onSwitchToRegister }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
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
        <h2 className="text-2xl font-display font-black mb-6 text-slate-900 dark:text-white">Đăng Nhập</h2>
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
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3 mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-500/30 transition-all disabled:opacity-50"
          >
            {loading ? 'Đang xử lý...' : 'ĐĂNG NHẬP'}
          </button>
        </form>
        <div className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
          Chưa có tài khoản?{' '}
          <button onClick={onSwitchToRegister} className="text-blue-600 dark:text-blue-400 font-bold hover:underline">
            Đăng ký ngay
          </button>
        </div>
      </div>
    </div>
  );
}
