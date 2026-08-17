export const getApiBase = () => {
  const envBase = import.meta.env.VITE_API_BASE;
  if (envBase && typeof envBase === 'string' && envBase.trim() !== '' && !envBase.includes('localhost')) {
    return envBase.trim();
  }
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return 'http://localhost:8000/api/v1';
  }
  return 'https://litreview-backend-5u4q.onrender.com/api/v1';
};

export const API_BASE = getApiBase();

export const safeFetch = async (urlOrEndpoint, options = {}) => {
  let primaryUrl = urlOrEndpoint;
  if (!primaryUrl.startsWith('http://') && !primaryUrl.startsWith('https://')) {
    primaryUrl = `${API_BASE}${urlOrEndpoint.startsWith('/') ? '' : '/'}${urlOrEndpoint}`;
  }
  try {
    const res = await fetch(primaryUrl, options);
    return res;
  } catch (err) {
    if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      const path = primaryUrl.includes('/api/v1') ? primaryUrl.split('/api/v1')[1] : '';
      if (path) {
        const fallbackUrl = `https://litreview-backend-5u4q.onrender.com/api/v1${path}`;
        try {
          return await fetch(fallbackUrl, options);
        } catch (fallbackErr) {
          throw fallbackErr;
        }
      }
    }
    throw err;
  }
};
