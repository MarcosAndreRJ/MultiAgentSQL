import { api } from '../api.js?v=1.0.3';

/**
 * sentinel.js — Dashboard de Observabilidade Sentinel
 * UX refatorada com fluxo mais fluido, filtros e drilldown por provider.
 */
export async function renderSentinelPage(container) {
  // Garantir que o container use o layout padrão de scroll do dashboard
  container.classList.add('page-body');
  const safeClient = async (endpoint, options = {}) => {
    const response = await fetch(`/api${endpoint}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const body = await response.json();
        detail = body.detail || body.message || detail;
      } catch (_) {
        // no-op
      }
      throw new Error(detail);
    }

    return response.status === 204 ? null : await response.json();
  };

  const getSummary = () => (api?.getSentinelSummary ? api.getSentinelSummary() : safeClient('/sentinel/summary'));
  const getProviders = () => (api?.getSentinelProviders ? api.getSentinelProviders() : safeClient('/sentinel/providers'));
  const getProviderHistory = (providerId) => (
    api?.getSentinelProviderHistory
      ? api.getSentinelProviderHistory(providerId, 24, 50)
      : safeClient(`/sentinel/providers/${providerId}/history?hours=24&limit=50`)
  );
  const triggerRun = () => (api?.triggerSentinelRun ? api.triggerSentinelRun(true) : safeClient('/sentinel/run?async_mode=true', { method: 'POST' }));

  let countdownInterval = null;
  let autoRefreshInterval = null;
  let currentSummary = null;
  let providersData = [];
  let selectedProviderId = null;
  let statusFilter = 'all';

  container.innerHTML = `
    <div class="page-body sentinel-page-wrapper">
      <div class="sentinel-shell fade-in">
      
      <!-- HEADER APRIMORADO -->
      <div class="sentinel-header">
        <div class="sentinel-header-main">
          <div class="page-title">
            <span class="page-icon">🛡️</span> 
            Sentinel <span class="tag" style="margin-left:8px;vertical-align:middle;font-size:9px">PRO MONITOR</span>
          </div>
          <div class="page-subtitle">Governance & Observability Engine for Multi-Agent Architectures.</div>
        </div>
        <div class="sentinel-header-actions">
          <div class="sentinel-header-meta" style="text-align:right; margin-right:15px;">
            <div id="next-run-badge" class="badge badge-info">Próxima execução: --:--</div>
            <div class="text-muted" style="font-size:10px; margin-top:4px;">Intervalo: <span id="sentinel-period-text">--</span> min</div>
          </div>
          <button class="btn btn-primary btn-sm" id="btn-trigger-sentinel">
            <span class="nav-icon">⚡</span> Executar Agora
          </button>
        </div>
      </div>

      <!-- DASHBOARD MAIN GRID -->
      <div class="sentinel-dashboard-main">
        
        <!-- COLUNA ESQUERDA: OPERAÇÕES -->
        <div class="sentinel-col-left" style="display:flex; flex-direction:column; gap:20px;">
          
          <div class="card sentinel-providers-card">
            <div class="card-header">
              <div>
                <div class="card-title">Monitoramento de Provedores</div>
                <div class="card-subtitle">Saúde em tempo real e detecção de drift de modelos.</div>
              </div>
              <div class="sentinel-table-actions">
                <select id="sentinel-status-filter" class="input input-sm sentinel-filter-select">
                  <option value="all">Todos Status</option>
                  <option value="healthy">Healthy</option>
                  <option value="degraded">Degraded</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <div class="sentinel-table-wrap">
              <table class="table sentinel-table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Status</th>
                    <th>Config</th>
                    <th>Consistência</th>
                    <th style="text-align:right">Tendência (24h)</th>
                  </tr>
                </thead>
                <tbody id="sentinel-providers-table">
                  <tr><td colspan="5" class="sentinel-empty-row"><span class="spinner"></span> Carregando...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- INFO / DOCS RAPIDA -->
          <div class="alert sentinel-info-alert">
            <div class="alert-icon">💡</div>
            <div style="font-size:11px; line-height:1.4">
              <strong>Dica de Governança:</strong> Use o Sentinel para identificar latências anômalas antes que elas afetem a experiência do usuário final nos agentes de produção.
            </div>
          </div>

        </div>

        <!-- COLUNA DIREITA: INSIGHTS & ROADMAP -->
        <div class="sentinel-col-right" style="display:flex; flex-direction:column; gap:20px;">
          
          <!-- SUMMARY MINI CARDS -->
          <div class="sentinel-summary-grid" id="sentinel-summary-cards" style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
             <!-- Injetado por renderSummary -->
          </div>

          <!-- ROADMAP SECTION -->
          <div class="card roadmap-card">
            <div class="card-header">
              <div class="card-title">Sentinel Roadmap</div>
              <span class="tag">Next Steps</span>
            </div>
            <div class="card-body">
              <div class="roadmap-list" id="sentinel-roadmap-list">
                <!-- Injetado por renderRoadmap -->
              </div>
            </div>
          </div>

          <!-- AUTO REFRESH CONTROL -->
          <div class="card" style="padding:12px; background:rgba(255,255,255,0.02)">
             <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="text-muted" style="font-size:11px;">Monitoramento em Tempo Real</span>
                <label class="sentinel-toggle" style="display:flex; align-items:center; gap:8px; cursor:pointer;">
                  <input type="checkbox" id="sentinel-auto-refresh" checked style="width:auto"/>
                  <span style="font-size:11px; font-weight:600">30s Auto-Update</span>
                </label>
             </div>
          </div>

        </div>

      </div>

      <!-- DETAIL DRILLDOWN (ABAIXO OU OVERLAY) -->
      <div class="card sentinel-detail-card" id="sentinel-provider-detail" hidden style="margin-top:20px;">
        <div class="card-header">
          <div class="card-title">Histórico de Verificações</div>
          <button class="btn btn-ghost btn-sm" id="sentinel-close-detail">Fechar Detalhes</button>
        </div>
        <div class="card-body" id="sentinel-provider-detail-body"></div>
      </div>

    </div>
  `;

  const nextRunBadge = container.querySelector('#next-run-badge');
  const summaryCards = container.querySelector('#sentinel-summary-cards');
  const tableBody = container.querySelector('#sentinel-providers-table');
  const periodText = container.querySelector('#sentinel-period-text');
  const statusFilterSelect = container.querySelector('#sentinel-status-filter');
  const detailCard = container.querySelector('#sentinel-provider-detail');
  const detailBody = container.querySelector('#sentinel-provider-detail-body');
  const btnCloseDetail = container.querySelector('#sentinel-close-detail');
  const btnTrigger = container.querySelector('#btn-trigger-sentinel');
  const autoRefreshToggle = container.querySelector('#sentinel-auto-refresh');
  const roadmapList = container.querySelector('#sentinel-roadmap-list');

  const roadmapItems = [
    { title: 'Score de consistência de respostas', status: 'planejado', icon: '📊' },
    { title: 'Detecção de degradação de qualidade', status: 'experimental', icon: '🧬' },
    { title: 'Alertas com threshold customizável', status: 'em-breve', icon: '🔔' },
    { title: 'Fallback automático para provider', status: 'futuro', icon: '🛡️' },
    { title: 'Dashboard de tendências históricas', status: 'planejado', icon: '📈' }
  ];

  const scoreColor = (score) => {
    if (score === null || score === undefined) return 'var(--muted)';
    if (score >= 90) return 'var(--green)';
    if (score >= 70) return 'var(--yellow)';
    return 'var(--red)';
  };

  const statusBadgeClass = (status) => {
    if (status === 'healthy') return 'badge-success';
    if (status === 'degraded') return 'badge-warning';
    if (status === 'critical') return 'badge-danger';
    return 'badge-muted';
  };

  const formatDate = (value) => {
    if (!value) return 'Nunca';
    try {
      return new Date(value).toLocaleString();
    } catch (_) {
      return value;
    }
  };

  const trendDot = (status) => {
    const cls = status === 'healthy' ? 'healthy' : status === 'degraded' ? 'degraded' : status === 'critical' ? 'critical' : 'unknown';
    return `<span class="sentinel-trend-dot ${cls}" title="${status}"></span>`;
  };

  function renderRoadmap() {
    if (!roadmapList) return;
    roadmapList.innerHTML = roadmapItems.map(item => `
      <div class="roadmap-item">
        <div class="roadmap-item-info">
          <span class="roadmap-item-icon">${item.icon}</span>
          <span class="roadmap-item-title">${item.title}</span>
        </div>
        <span class="rm-badge ${item.status}">${item.status.replace('-', ' ')}</span>
      </div>
    `).join('');
  }

  function updateCountdown() {
    if (!currentSummary || !currentSummary.last_run_at || !nextRunBadge) return;

    const intervalMin = currentSummary.sentinel_interval_minutes || 20;
    const last = new Date(currentSummary.last_run_at);
    const next = new Date(last.getTime() + intervalMin * 60000);
    const now = new Date();
    const diff = next - now;

    if (diff <= 0) {
      nextRunBadge.textContent = 'Execução em andamento...';
      nextRunBadge.className = 'badge badge-warning';
      return;
    }

    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    nextRunBadge.textContent = `Próxima: ${mins}m ${secs}s`;
    nextRunBadge.className = 'badge badge-info';
  }

  function renderSummary(summary) {
    currentSummary = summary;
    if (periodText) periodText.textContent = String(summary.sentinel_interval_minutes || 20);

    if (summaryCards) {
      summaryCards.innerHTML = `
        <div class="stat-card">
          <div class="stat-label">Providers</div>
          <div class="stat-value">${summary.providers_total ?? 0}</div>
          <div class="stat-sub">Escopo Total</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Alertas</div>
          <div class="stat-value ${summary.active_alerts > 0 ? 'sentinel-crit' : 'sentinel-ok'}">${summary.active_alerts ?? 0}</div>
          <div class="stat-sub">Incidentes Críticos</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Qualidade</div>
          <div class="stat-value" style="color:${scoreColor(summary.average_quality_score || 0)}">${summary.average_quality_score ?? 0}%</div>
          <div class="stat-sub">Média de Resposta</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Anomalias</div>
          <div class="stat-value ${summary.anomalies_detected > 0 ? 'sentinel-warn' : ''}">${summary.anomalies_detected ?? 0}</div>
          <div class="stat-sub">Últimas 24h</div>
        </div>
      `;
    }

    updateCountdown();
    renderRoadmap();
  }

  function getFilteredProviders() {
    if (statusFilter === 'all') return providersData;
    return providersData.filter((p) => p.status === statusFilter);
  }

  function renderProviders() {
    const providers = getFilteredProviders();

    if (!providers.length) {
      tableBody.innerHTML = '<tr><td colspan="5" class="sentinel-empty-row">Nenhum provider para o filtro selecionado.</td></tr>';
      return;
    }

    tableBody.innerHTML = providers.map((p) => `
      <tr class="sentinel-provider-row ${selectedProviderId === p.provider_id ? 'active' : ''}" data-provider-id="${p.provider_id}">
        <td>
          <div class="sentinel-provider-name">${p.provider_name}</div>
          <div class="sentinel-provider-meta">Última: ${formatDate(p.last_checked_at)}</div>
        </td>
        <td style="vertical-align:middle"><span class="badge ${statusBadgeClass(p.status)}">${(p.status || 'unknown').toUpperCase()}</span></td>
        <td>
          <div style="font-size:11px; font-weight:600">${p.models_checked ?? 0} / ${p.models_registered ?? 0} Models</div>
          <div class="sentinel-provider-meta">Checked / Total</div>
        </td>
        <td>
          <div class="sentinel-score-wrap">
            <div class="sentinel-score-bar">
              <span style="width:${Math.max(0, Math.min(100, p.consistency_score ?? 0))}%; background:${scoreColor(p.consistency_score)}"></span>
            </div>
            <span class="sentinel-score-label" style="color:${scoreColor(p.consistency_score)}">
              ${p.consistency_score !== null ? `${p.consistency_score}%` : '[OFFLINE]'}
            </span>
          </div>
        </td>
        <td style="text-align:right">
          <div class="sentinel-trend" style="justify-content:flex-end">${(p.trend || []).map(trendDot).join('')}</div>
        </td>
      </tr>
    `).join('');

    tableBody.querySelectorAll('.sentinel-provider-row').forEach((row) => {
      row.addEventListener('click', async () => {
        const providerId = Number(row.dataset.providerId);
        selectedProviderId = providerId;
        renderProviders();
        await renderProviderDetail(providerId);
      });
    });
  }

  async function renderProviderDetail(providerId) {
    detailCard.hidden = false;
    detailBody.innerHTML = '<div class="sentinel-detail-loading">Carregando histórico...</div>';

    try {
      const history = await getProviderHistory(providerId);
      const provider = providersData.find((p) => p.provider_id === providerId);

      detailBody.innerHTML = `
        <div class="sentinel-detail-head">
          <div>
            <div class="sentinel-provider-name">${provider?.provider_name || `Provider ${providerId}`}</div>
            <div class="sentinel-provider-meta">Últimos ${history.total} snapshots nas últimas ${history.hours}h</div>
          </div>
        </div>
        <div class="sentinel-timeline">
          ${history.items.map((item) => `
            <div class="sentinel-timeline-item">
              <div class="sentinel-timeline-top">
                <span class="badge ${statusBadgeClass(item.status)}">${(item.status || 'unknown').toUpperCase()}</span>
                <span class="sentinel-provider-meta">${formatDate(item.checked_at)}</span>
              </div>
              <div class="sentinel-timeline-body">
                <span>Modelos: <strong>${item.models_total ?? 0}</strong></span>
                <span>Novos: <strong>${item.models_new ?? 0}</strong></span>
                <span>Atualizados: <strong>${item.models_updated ?? 0}</strong></span>
                <span>Indisponíveis: <strong>${item.models_unavailable ?? 0}</strong></span>
              </div>
              <div class="sentinel-timeline-msg">${item.message || 'Sem mensagem.'}</div>
            </div>
          `).join('')}
        </div>
      `;
    } catch (err) {
      detailBody.innerHTML = `<div class="sentinel-detail-error">Falha ao carregar histórico: ${err.message}</div>`;
    }
  }

  async function loadData() {
    try {
      const [summary, providers] = await Promise.all([getSummary(), getProviders()]);
      providersData = providers || [];
      renderSummary(summary || {});
      renderProviders();
    } catch (err) {
      summaryCards.innerHTML = `<div class="alert alert-danger" style="grid-column: 1 / -1">Falha ao carregar Sentinel: ${err.message}</div>`;
      tableBody.innerHTML = `<tr><td colspan="5" class="sentinel-empty-row">Falha ao carregar dados.</td></tr>`;
    }
  }

  btnTrigger.addEventListener('click', async () => {
    const original = btnTrigger.innerHTML;
    btnTrigger.disabled = true;
    btnTrigger.innerHTML = '<span class="spinner"></span> Disparando ciclo...';

    try {
      const result = await triggerRun();
      nextRunBadge.textContent = result?.message || 'Ciclo enfileirado';
      setTimeout(loadData, 1200);
    } catch (err) {
      nextRunBadge.textContent = `Erro: ${err.message}`;
      nextRunBadge.className = 'badge badge-danger';
    } finally {
      btnTrigger.disabled = false;
      btnTrigger.innerHTML = original;
    }
  });

  statusFilterSelect.addEventListener('change', () => {
    statusFilter = statusFilterSelect.value;
    renderProviders();
  });

  btnCloseDetail.addEventListener('click', () => {
    selectedProviderId = null;
    detailCard.hidden = true;
    renderProviders();
  });

  autoRefreshToggle.addEventListener('change', () => {
    if (autoRefreshToggle.checked) {
      autoRefreshInterval = setInterval(loadData, 30000);
    } else if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = null;
    }
  });

  await loadData();

  countdownInterval = setInterval(updateCountdown, 1000);
  autoRefreshInterval = setInterval(loadData, 30000);

  return () => {
    if (countdownInterval) clearInterval(countdownInterval);
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  };
}
