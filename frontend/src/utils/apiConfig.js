// Single source of truth for where the frontend talks to the backend.
//
// This file used to hardcode a specific backend address as its fallback, and
// the address differed per branch: main carried an EC2 IP, develop and the
// feature branches carried a Railway URL that main had already abandoned.
// Since VITE_API_BASE was documented nowhere, nobody set it, so whichever
// address happened to be in the checked-out branch decided which backend a
// developer was reading and writing. Two people on two branches were using two
// different databases without any indication.
//
// Now: VITE_API_BASE decides, and where it is absent the only assumption made
// is the local development one, which is verifiable on the spot.
// See frontend/.env.example.

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1', '0.0.0.0']);

export const getApiBase = () => {
  const envBase = import.meta.env.VITE_API_BASE;
  if (envBase && typeof envBase === 'string' && envBase.trim() !== '') {
    return envBase.trim();
  }

  if (typeof window !== 'undefined') {
    if (LOCAL_HOSTNAMES.has(window.location.hostname)) {
      return `http://${window.location.hostname}:8000/api/v1`;
    }
    if (window.location.hostname === 'c3-app-165.io.vn') {
      return 'https://www.c3-app-165.io.vn/api/v1';
    }
    return `${window.location.origin}/api/v1`;
  }

  return '/api/v1';
};

export const API_BASE = getApiBase();

export const AUTH_TOKEN_STORAGE_KEY = 'litreview_auth_token';

export const getAuthToken = () => {
  try {
    return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || null;
  } catch {
    return null;
  }
};

const withAuthHeaders = (options = {}) => {
  const token = getAuthToken();
  if (!token) return options;
  return {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  };
};

// FastAPI sends `detail` as a plain string for a hand-raised HTTPException, but
// as an array of {loc, msg, type} objects for its own automatic 422 request
// validation. `new Error(detail)` on that array coerces to the literal string
// "[object Object]" -- three call sites independently hit this. Centralized
// here instead of fixed three times.
export const formatApiErrorDetail = (detail, fallback = 'Đã có lỗi xảy ra.') => {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === 'object' ? item.msg : String(item)))
      .filter(Boolean);
    return messages.length ? messages.join('; ') : fallback;
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.message || fallback;
  }
  return fallback;
};

export const safeFetch = async (urlOrEndpoint, options = {}) => {
  let primaryUrl = urlOrEndpoint;
  if (!primaryUrl.startsWith('http://') && !primaryUrl.startsWith('https://')) {
    const base = getApiBase();
    primaryUrl = `${base}${urlOrEndpoint.startsWith('/') ? '' : '/'}${urlOrEndpoint}`;
  }

  const requestOptions = withAuthHeaders(options);

  try {
    return await fetch(primaryUrl, requestOptions);
  } catch (err) {
    // Local development auto-fallback between 8001 <-> 8000 and localhost <-> 127.0.0.1
    if (primaryUrl.includes(':8001')) {
      try {
        return await fetch(primaryUrl.replace(':8001', ':8000'), requestOptions);
      } catch {}
    }
    if (primaryUrl.includes(':8000')) {
      try {
        return await fetch(primaryUrl.replace(':8000', ':8001'), requestOptions);
      } catch {}
    }
    if (primaryUrl.includes('localhost:')) {
      try {
        return await fetch(primaryUrl.replace('localhost:', '127.0.0.1:'), requestOptions);
      } catch {}
    }
    throw err;
  }
};
