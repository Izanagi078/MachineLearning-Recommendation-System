/**
 * api.js — Central API client for the Movie Recommender frontend.
 *
 * All fetch() calls go through this module. The base URL is read from the
 * VITE_API_BASE environment variable (set in frontend/.env), so you can
 * point the app at any backend without touching component code.
 *
 * Usage:
 *   import api from '../api';
 *   const data = await api.getStats();
 */

const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

/** Build Authorization header from localStorage token if present. */
function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Generic request helper — throws on non-2xx responses. */
async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail || 'API error'), { status: res.status, body: err });
  }
  return res.json();
}

// ── Stats & Feed ──────────────────────────────────────────────────────────────

export const getStats = () => request('/api/stats');

export const getFeed = (limit = 8, page = 1) =>
  request(`/api/feed?limit=${limit}&page=${page}`);

// ── Movies ────────────────────────────────────────────────────────────────────

export const getPopularMovies = (limit = 5, page = 1) =>
  request(`/api/movies/popular?limit=${limit}&page=${page}`);

export const searchMovies = (query, limit = 5) =>
  request(`/api/movies/search?query=${encodeURIComponent(query)}&limit=${limit}`);

export const addMovie = (movie) =>
  request('/api/movies', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(movie),
  });

export const deleteMovie = (movieId) =>
  request(`/api/movies/${movieId}`, { method: 'DELETE' });

// ── Auth ──────────────────────────────────────────────────────────────────────

export const register = (username, password) =>
  request('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

export const login = (username, password) =>
  request('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

export const loginDemo = (username) =>
  request('/api/auth/demo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password: '' }),
  });

// ── Recommendations & Onboarding ─────────────────────────────────────────────

export const getRecommendations = (userId, { weightCol = 0.5, novelty = 0.0, diversity = 0.2, topN = 10 } = {}) =>
  request(
    `/api/recommendations?userId=${encodeURIComponent(userId)}&weight_collaborative=${weightCol}&novelty_weight=${novelty}&diversity_weight=${diversity}&top_n=${topN}`
  );

export const submitOnboarding = (genres, keywords, userId = null) =>
  request('/api/onboarding', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ genres, keywords, userId }),
  });

export const submitRating = (userId, movieId, rating) =>
  request('/api/ratings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId, movieId, rating }),
  });

export const getUserRatings = (userId) =>
  request(`/api/users/${userId}/ratings`);

// ── Default export (namespace object) ────────────────────────────────────────
const api = {
  getStats, getFeed,
  getPopularMovies, searchMovies, addMovie, deleteMovie,
  register, login, loginDemo,
  getRecommendations, submitOnboarding, submitRating, getUserRatings,
};

export default api;
