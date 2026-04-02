/**
 * health.js — View de Observabilidade do Sistema
 * Monitora: providers, banco de dados e runtime.
 *
 * @param {HTMLElement} container
 * @returns {Function} teardown — cancela polling
 */

import { api }           from '../api.js';
import { badge, showLoading, showError } from '../utils/dom.js';
import { formatRelativeTime } from '../utils/formatters.js';

let _pollingInterval = null;

export async function renderHealthPage(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <div class="page-title"><span class="page-icon">❤️</span> System Health</div>
        <div class="page-subtitle">Monitoramento em tempo real do runtime</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary btn-sm" id="btn-refresh-health">↺ Atualizar</button>
      </div>
    </div>
    <div class="page-body" id="health-body">
      <div class="stats-grid" id="health-stats">
        <!-- Preenchido dinamicamente -->
      </div>
      <div class="card">
        <div class="card-header">Providers</div>
        <div id="health-providers-wrap"></div>
      </div>
      <div class="card">
        <div class="card-header">Banco de Dados</div>
        <div id="health-db-wrap"></div>
      </div>
      <div class="card">
        <div class="card-header">Runtime</div>
        <div id="health-runtime-wrap"></div>
      </div>
    </div>
  `;

  async function refresh() {
    await Promise.allSettled([
      loadProvidersHealth(container),
      loadDatabaseHealth(container),
      loadRuntimeHealth(container),
    ]);
  }

  container.querySelector('#btn-refresh-health').addEventListener('click', refresh);

  await refresh();

  // Polling a cada 30 segundos
  _pollingInterval = setInterval(refresh, 30_000);

  return teardown;
}

function teardown() {
  if (_pollingInterval) {
    clearInterval(_pollingInterval);
    _pollingInterval = null;
  }
}

// ── Providers Health ─────────────────────────────────────────────
async function loadProvidersHealth(container) {
  const wrap = container.querySelector('#health-providers-wrap');
  if (!wrap) return;
  showLoading(wrap, 'Verificando providers...');

  try {
    const data = await api.getHealthProviders();
    const providers = data.providers || [];

    if (providers.length === 0) {
      wrap.innerHTML = `<div class="empty-state"><div class="empty-state-sub">Nenhum provider configurado.</div></div>`;
      return;
    }

    wrap.innerHTML = `
      <table class="data-table">
        <thead><tr>
          <th>Provider</th>
          <th>Base URL</th>
          <th>Status</th>
          <th>Latência</th>
          <th>Última verificação</th>
        </tr></thead>
        <tbody>
          ${providers.map(p => `
            <tr>
              <td><strong>${p.name}</strong></td>
              <td class="text-mono" style="font-size:11px;color:var(--ink-2)">${p.baseUrl || '—'}</td>
              <td>${buildHealthBadge(p.status)}</td>
              <td style="font-size:11px;color:var(--ink-2)">${p.latencyMs ? p.latencyMs + ' ms' : '—'}</td>
              <td style="font-size:11px;color:var(--ink-2)">${p.checkedAt ? formatRelativeTime(p.checkedAt) : '—'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    // Atualiza stat cards
    const healthyCount = providers.filter(p => isHealthy(p.status)).length;
    updateStatCard(container, 'stat-providers', healthyCount, providers.length, 'Providers OK');

  } catch (err) {
    showError(wrap, `Falha ao verificar providers: ${err.message}`);
  }
}

// ── Database Health ─────────────────────────────────────────────
async function loadDatabaseHealth(container) {
  const wrap = container.querySelector('#health-db-wrap');
  if (!wrap) return;
  showLoading(wrap, 'Verificando banco de dados...');

  try {
    const data = await api.getHealthDatabase();

    wrap.innerHTML = `
      <div class="card-body">
        <div class="stats-grid" style="grid-template-columns:repeat(3,1fr);">
          <div class="stat-card">
            <div class="stat-label">Status</div>
            <div style="margin-top:4px;">${buildHealthBadge(data.status)}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Conexões Ativas</div>
            <div class="stat-value">${data.activeConnections ?? '—'}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Latência</div>
            <div class="stat-value" style="font-size:16px;">${data.latencyMs ? data.latencyMs + 'ms' : '—'}</div>
          </div>
        </div>
        ${data.error ? `<div class="alert alert-danger" style="margin-top:12px;"><div class="alert-icon">⚠️</div><div>${data.error}</div></div>` : ''}
      </div>
    `;

    updateStatCard(container, 'stat-database', isHealthy(data.status) ? 1 : 0, 1, 'DB Status');

  } catch (err) {
    showError(wrap, `Falha ao verificar banco: ${err.message}`);
  }
}

// ── Runtime Health ───────────────────────────────────────────────
async function loadRuntimeHealth(container) {
  const wrap = container.querySelector('#health-runtime-wrap');
  if (!wrap) return;
  showLoading(wrap, 'Verificando runtime...');

  try {
    const data = await api.getHealthRuntime();
    const agents = data.agents || [];

    wrap.innerHTML = `
      <div class="card-body">
        <div class="stats-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:12px;">
          <div class="stat-card">
            <div class="stat-label">Agentes Ativos</div>
            <div class="stat-value">${agents.length}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Uptime</div>
            <div class="stat-value" style="font-size:16px;">${data.uptime || '—'}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Versão</div>
            <div class="stat-value" style="font-size:16px;">${data.version || '—'}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Ambiente</div>
            <div class="stat-value" style="font-size:14px;">${data.environment || '—'}</div>
          </div>
        </div>
        ${agents.length > 0 ? `
          <table class="data-table">
            <thead><tr><th>Agente</th><th>ID</th><th>Modelo</th><th>Status</th></tr></thead>
            <tbody>
              ${agents.map(a => `
                <tr>
                  <td>${a.name || '—'}</td>
                  <td class="text-mono" style="font-size:11px;">${a.id}</td>
                  <td style="font-size:11px;color:var(--ink-2);">${a.llmModel || 'padrão'}</td>
                  <td><span class="badge badge-success">Ativo</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        ` : '<div class="empty-state"><div class="empty-state-sub">Nenhum agente no runtime.</div></div>'}
      </div>
    `;

    // Render stat cards se ainda não existem
    const statsEl = container.querySelector('#health-stats');
    if (statsEl && statsEl.children.length === 0) {
      statsEl.innerHTML = `
        <div class="stat-card" id="stat-providers">
          <div class="stat-label">Providers OK</div>
          <div class="stat-value">—</div>
        </div>
        <div class="stat-card" id="stat-database">
          <div class="stat-label">DB Status</div>
          <div class="stat-value">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Agentes Ativos</div>
          <div class="stat-value">${agents.length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Uptime</div>
          <div class="stat-value" style="font-size:16px;">${data.uptime || '—'}</div>
        </div>
      `;
    }

  } catch (err) {
    showError(wrap, `Falha ao verificar runtime: ${err.message}`);
  }
}

// ── Helpers ──────────────────────────────────────────────────────
function buildHealthBadge(status) {
  const s = String(status || '').toLowerCase();
  if (['ok', 'healthy', 'online', 'connected'].includes(s)) return `<span class="badge badge-success">${status}</span>`;
  if (['error', 'fail', 'offline', 'disconnected'].includes(s)) return `<span class="badge badge-danger">${status}</span>`;
  if (['degraded', 'slow', 'warning'].includes(s)) return `<span class="badge badge-warning">${status}</span>`;
  return `<span class="badge badge-muted">${status || 'UNKNOWN'}</span>`;
}

function isHealthy(status) {
  return ['ok', 'healthy', 'online', 'connected'].includes(String(status || '').toLowerCase());
}

function updateStatCard(container, cardId, value, total, label) {
  const card = container.querySelector(`#${cardId}`);
  if (!card) return;
  card.innerHTML = `
    <div class="stat-label">${label}</div>
    <div class="stat-value">${value}/${total}</div>
    <div class="stat-sub">${value === total ? 'Todos OK' : `${total - value} com problema`}</div>
  `;
}
