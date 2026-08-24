export const getApiBase = () => {
  const envBase = import.meta.env.VITE_API_BASE;
  if (envBase && typeof envBase === 'string' && envBase.trim() !== '') {
    return envBase.trim();
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') {
      return `http://${hostname}:8000/api/v1`;
    }
  }
  return 'https://litreview-backend-production-0298.up.railway.app/api/v1';
};

export const API_BASE = getApiBase();

export const safeFetch = async (urlOrEndpoint, options = {}) => {
  let primaryUrl = urlOrEndpoint;
  if (!primaryUrl.startsWith('http://') && !primaryUrl.startsWith('https://')) {
    const base = getApiBase();
    primaryUrl = `${base}${urlOrEndpoint.startsWith('/') ? '' : '/'}${urlOrEndpoint}`;
  }

  try {
    const res = await fetch(primaryUrl, options);
    return res;
  } catch (err) {
    // If localhost failed, try 127.0.0.1
    if (primaryUrl.includes('localhost:8000')) {
      const altUrl = primaryUrl.replace('localhost:8000', '127.0.0.1:8000');
      try {
        return await fetch(altUrl, options);
      } catch {}
    } else if (primaryUrl.includes('127.0.0.1:8000')) {
      const altUrl = primaryUrl.replace('127.0.0.1:8000', 'localhost:8000');
      try {
        return await fetch(altUrl, options);
      } catch {}
    }

    // Remote fallback if not on local dev
    if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      const path = primaryUrl.includes('/api/v1') ? primaryUrl.split('/api/v1')[1] : '';
      if (path) {
        const fallbackUrl = `https://litreview-backend-production-0298.up.railway.app/api/v1${path}`;
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
