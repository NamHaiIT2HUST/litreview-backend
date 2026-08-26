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

  if (typeof window !== 'undefined' && LOCAL_HOSTNAMES.has(window.location.hostname)) {
    return `http://${window.location.hostname}:8000/api/v1`;
  }

  // Anywhere else, assume the deployment proxies /api/v1 to the backend on the
  // same origin (vercel.json does this). Naming a specific host here is what
  // caused the divergence described above.
  if (import.meta.env.PROD && !import.meta.env.VITE_API_BASE) {
    console.warn(
      '[apiConfig] VITE_API_BASE is not set. Falling back to the same-origin ' +
        '/api/v1 path, which only works if this deployment proxies it to the ' +
        'backend. See frontend/.env.example.'
    );
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

// The API now authenticates every data route, so the stored token has to travel
// with every request. Attaching it here keeps call sites from each having to
// remember, and avoids a second source of truth for where the token lives.
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
    // Local development only: some machines resolve exactly one of these two.
    // This is a genuine retry of the same target, not a different backend.
    if (primaryUrl.includes('localhost:8000')) {
      return fetch(primaryUrl.replace('localhost:8000', '127.0.0.1:8000'), requestOptions);
    }
    if (primaryUrl.includes('127.0.0.1:8000')) {
      return fetch(primaryUrl.replace('127.0.0.1:8000', 'localhost:8000'), requestOptions);
    }

    // A cross-origin fallback to a hardcoded http:// address used to live here.
    // It could never run: the deployed site is HTTPS, and browsers block mixed
    // active content. It read as resilience while doing nothing, and it pointed
    // at a backend the caller had not chosen. Removed rather than repaired.
    throw err;
  }
};
