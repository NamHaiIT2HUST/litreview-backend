import React, { useState, useEffect } from 'react';
import {
  Users, Search, BookOpen, FolderGit2, Trash2,
  RefreshCw, Shield, Clock, AlertCircle, CheckCircle2, UserCheck, Zap
} from 'lucide-react';
import { API_BASE, safeFetch } from '../../utils/apiConfig';

export default function AdminDashboard({ darkMode }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const fetchStats = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await safeFetch(`${API_BASE}/auth/admin/stats`);
      if (!res.ok) throw new Error('Không thể tải dữ liệu thống kê');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      setError(err.message || 'Lỗi khi tải dữ liệu');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleDeleteUser = async (userId, username) => {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa người dùng "${username}"?`)) return;
    setDeletingId(userId);
    try {
      const res = await safeFetch(`${API_BASE}/auth/admin/users/${userId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Xóa người dùng thất bại');
      setSuccessMsg(`Đã xóa tài khoản "${username}" thành công.`);
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchStats();
    } catch (err) {
      alert(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const formatTokens = (n) => {
    const num = Number(n) || 0;
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return String(num);
  };

  const formatDate = (isoString) => {
    if (!isoString) return '---';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('vi-VN', {
        hour: '2-digit', minute: '2-digit',
        day: '2-digit', month: '2-digit', year: 'numeric'
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 font-display font-bold text-[11px] uppercase tracking-wider border border-blue-200 dark:border-blue-800">
              HỆ THỐNG QUẢN TRỊ
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-display font-black text-slate-900 dark:text-white tracking-tight">
            Quản Lý Tài Khoản & Hoạt Động Hệ Thống
          </h1>
          <p className="text-xs md:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Dành riêng cho Quản trị viên: Theo dõi số lượng tra cứu, cơ sở dữ liệu và quản lý người dùng.
          </p>
        </div>

        <button
          onClick={fetchStats}
          disabled={loading}
          className="self-start md:self-auto px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-display font-bold flex items-center gap-2 shadow-sm transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Làm mới dữ liệu</span>
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 5 Summary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
        {/* Total Users */}
        <div className={`p-6 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Người Dùng</span>
            <div className="w-10 h-10 rounded-2xl bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-sky-400 flex items-center justify-center font-bold">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-display font-black text-slate-900 dark:text-white">
              {loading ? '...' : (stats?.summary?.total_users ?? 0)}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Tài khoản đã đăng ký</span>
          </div>
        </div>

        {/* Total Queries */}
        <div className={`p-6 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lượt Tra Cứu</span>
            <div className="w-10 h-10 rounded-2xl bg-emerald-50 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
              <Search className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-display font-black text-slate-900 dark:text-white">
              {loading ? '...' : (stats?.summary?.total_queries ?? 0)}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Lệnh tìm kiếm học thuật</span>
          </div>
        </div>

        {/* Total Papers */}
        <div className={`p-6 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Bài Báo Đã Thu Thập</span>
            <div className="w-10 h-10 rounded-2xl bg-purple-50 dark:bg-purple-950/80 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold">
              <BookOpen className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-display font-black text-slate-900 dark:text-white">
              {loading ? '...' : (stats?.summary?.total_papers ?? 0)}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Nguồn tài liệu trong CSDL</span>
          </div>
        </div>

        {/* Total Projects */}
        <div className={`p-6 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đề Tài Nghiên Cứu</span>
            <div className="w-10 h-10 rounded-2xl bg-amber-50 dark:bg-amber-950/80 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold">
              <FolderGit2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-display font-black text-slate-900 dark:text-white">
              {loading ? '...' : (stats?.summary?.total_projects ?? 0)}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Dự án SLR đã tạo</span>
          </div>
        </div>

        {/* Total Tokens */}
        <div className={`p-6 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Token AI Đã Dùng</span>
            <div className="w-10 h-10 rounded-2xl bg-rose-50 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 flex items-center justify-center font-bold">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-display font-black text-slate-900 dark:text-white">
              {loading ? '...' : formatTokens((stats?.summary?.total_input_tokens ?? 0) + (stats?.summary?.total_output_tokens ?? 0))}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">
              {loading ? '...' : `${formatTokens(stats?.summary?.total_input_tokens ?? 0)} vào · ${formatTokens(stats?.summary?.total_output_tokens ?? 0)} ra`}
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: User Management & Recent Search Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* 1. Quản lý tài khoản người dùng */}
        <div className={`p-6 md:p-7 rounded-3xl border space-y-4 ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-blue-600 dark:text-sky-400" />
              <h2 className="text-lg font-display font-black text-slate-900 dark:text-white">
                Danh Sách Tài Khoản
              </h2>
            </div>
            <span className="text-xs font-bold text-slate-500">
              {stats?.users?.length || 0} tài khoản
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-bold uppercase tracking-wider">
                  <th className="py-3 px-2">Tên Đăng Nhập</th>
                  <th className="py-3 px-2">Vai Trò</th>
                  <th className="py-3 px-2 text-right">Tra Cứu</th>
                  <th className="py-3 px-2 text-right">Token</th>
                  <th className="py-3 px-2">Ngày Tạo</th>
                  <th className="py-3 px-2 text-right">Thao Tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {stats?.users?.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-2 font-bold text-slate-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center font-black text-[11px] text-blue-600 dark:text-sky-400">
                          {u.username.slice(0, 2).toUpperCase()}
                        </div>
                        <span>{u.username}</span>
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <span className={`px-2.5 py-1 rounded-full font-bold text-[10px] uppercase tracking-wide inline-flex items-center gap-1 ${
                        u.role === 'admin'
                          ? 'bg-purple-100 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300 border border-purple-200 dark:border-purple-800'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-950/80 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                      }`}>
                        {u.role === 'admin' ? <Shield className="w-2.5 h-2.5" /> : null}
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right font-bold text-slate-700 dark:text-slate-300">
                      {u.query_count ?? 0}
                    </td>
                    <td className="py-3 px-2 text-right font-mono text-slate-700 dark:text-slate-300">
                      {formatTokens((u.input_tokens ?? 0) + (u.output_tokens ?? 0))}
                    </td>
                    <td className="py-3 px-2 text-slate-500 dark:text-slate-400">
                      {formatDate(u.created_at)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {u.role !== 'admin' ? (
                        <button
                          onClick={() => handleDeleteUser(u.id, u.username)}
                          disabled={deletingId === u.id}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors"
                          title="Xóa tài khoản"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-400 italic">Mặc định</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 2. Lịch sử tra cứu gần đây */}
        <div className={`p-6 md:p-7 rounded-3xl border space-y-4 ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h2 className="text-lg font-display font-black text-slate-900 dark:text-white">
                Lịch Sử Tra Cứu Gần Đây
              </h2>
            </div>
            <span className="text-xs font-bold text-slate-500">10 lượt mới nhất</span>
          </div>

          <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
            {stats?.recent_queries?.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">Chưa có lịch sử tra cứu nào</div>
            ) : (
              stats?.recent_queries?.map((q, idx) => (
                <div 
                  key={idx}
                  className="p-3.5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-850/50 space-y-1.5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-bold text-slate-800 dark:text-slate-200 line-clamp-2 leading-relaxed">
                      🔍 {q.query}
                    </p>
                    <span className="px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 font-mono text-[10px] font-bold whitespace-nowrap">
                      {q.results} bài
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {formatDate(q.time)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
