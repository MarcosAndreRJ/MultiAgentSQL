/**
 * api.js — Wrapper centralizado para fetch com FastAPI
 * - Trata erros uniformemente
 * - Injeta headers
 * - Prepara integração futura com WebSocket
 */

import { store } from './store.js';

const BASE_URL = '/api';  // FastAPI routers usam prefixo /api

/**
 * Cliente HTTP base
 */
async function client(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || body.message || detail;
    } catch (_) { /* ignore */ }

    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  // 204 No Content
  if (response.status === 204) return null;

  return response.json();
}

/* ── Providers ──────────────────────────────────────────────── */
export const api = {
  // --- Agents ---
  getAgents:   () => client('/agents'),
  updateAgent: (id, data) => client(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // --- Providers ---
  getProviders:    () => client('/providers'),
  createProvider:  (data) => client('/providers', { method: 'POST', body: JSON.stringify(data) }),
  updateProvider:  (id, data) => client(`/providers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProvider:  (id) => client(`/providers/${id}`, { method: 'DELETE' }),
  testProvider:    (id) => client(`/providers/${id}/test`, { method: 'POST' }),

  // --- Models ---
  getModels:           () => client('/models'),
  getModelsByProvider: (provId) => client(`/providers/${provId}/models`),

  // --- Health ---
  getHealthProviders: () => client('/health/providers'),
  getHealthDatabase:  () => client('/health/database'),
  getHealthRuntime:   () => client('/health/runtime'),

  // --- Config ---
  getConfig:    () => client('/config'),
  updateConfig: (data) => client('/config', { method: 'PUT', body: JSON.stringify(data) }),

  // --- Skills ---
  getSkills:    () => client('/skills'),
  createSkill:  (name, content) => client('/skills', { method: 'POST', body: JSON.stringify({ name, content }) }),
  updateSkill:  (name, content) => client(`/skills/${name}`, { method: 'PUT', body: JSON.stringify({ content }) }),
  deleteSkill:  (name) => client(`/skills/${name}`, { method: 'DELETE' }),
  assignSkill:  (agentId, skillName) => client(`/agents/${agentId}/skills/${skillName}`, { method: 'POST' }),
  removeSkill:  (agentId, skillName) => client(`/agents/${agentId}/skills/${skillName}`, { method: 'DELETE' }),
};
