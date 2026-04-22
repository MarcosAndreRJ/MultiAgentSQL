/**
 * api.js - Centralized fetch wrapper for FastAPI
 * - Normalizes errors
 * - Injects headers
 */

import { store } from './store.js';

const BASE_URL = '/api';
window.AGENT_API_VERSION = '1.0.2';

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
    } catch (_) {
      // ignore
    }

    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  get: (endpoint) => client(endpoint),

  // Agents
  getAgents: () => client('/agents'),
  getAgent: (id) => client(`/agents/${id}`),
  updateAgent: (id, data) => client(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Providers
  getProviders: () => client('/providers'),
  getProvider: (id) => client(`/providers/${id}`),
  createProvider: (data) => client('/providers', { method: 'POST', body: JSON.stringify(data) }),
  updateProvider: (id, data) => client(`/providers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProvider: (id) => client(`/providers/${id}`, { method: 'DELETE' }),
  testProvider: (id) => client(`/providers/${id}/test`, { method: 'POST' }),

  // Models
  getModels: () => client('/models'),
  getModelsCatalog: () => client('/models/catalog'),
  syncProviderModels: (id) => client(`/models/sync/${id}`, { method: 'POST' }),

  // Health
  getHealthProviders: () => client('/health/providers'),
  getHealthDatabase: () => client('/health/database'),
  getHealthRuntime: () => client('/health/runtime'),
  getHealthSummary: () => client('/health/summary'),
  getHealthLogs: (limit = 50) => client(`/health/logs?limit=${limit}`),

  // Sentinel
  getSentinelSummary: () => client('/sentinel/summary'),
  getSentinelProviders: () => client('/sentinel/providers'),
  getSentinelProviderHistory: (providerId, hours = 24, limit = 50) =>
    client(`/sentinel/providers/${providerId}/history?hours=${hours}&limit=${limit}`),
  triggerSentinelRun: (asyncMode = true) => client(`/sentinel/run?async_mode=${asyncMode}`, { method: 'POST' }),

  // Config
  getConfig: () => client('/config'),
  updateConfig: (data) => client('/config', { method: 'PUT', body: JSON.stringify(data) }),

  // Skills
  getSkills: () => client('/skills'),
  createSkill: (name, content) => client('/skills', { method: 'POST', body: JSON.stringify({ name, content }) }),
  updateSkill: (name, content) => client(`/skills/${name}`, { method: 'PUT', body: JSON.stringify({ content }) }),
  deleteSkill: (name) => client(`/skills/${name}`, { method: 'DELETE' }),
  assignSkill: (agentId, skillName) => client(`/agents/${agentId}/skills/${skillName}`, { method: 'POST' }),
  removeSkill: (agentId, skillName) => client(`/agents/${agentId}/skills/${skillName}`, { method: 'DELETE' }),

  // Digest & ER
  getDigestStatus: (agentId) => client(`/digest/status?agent_id=${agentId}`),
  generateDigest: (agentId) => client(`/digest/generate?agent_id=${agentId}`, { method: 'POST' }),
  getDigest: (agentId) => client(`/digest/?agent_id=${agentId}`),
  getDiagramStatus: (agentId) => client(`/diagram/${agentId}/status`),
};

export const getSentinelSummary = api.getSentinelSummary;
export const getSentinelProviders = api.getSentinelProviders;
export const triggerSentinelRun = api.triggerSentinelRun;
