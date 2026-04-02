/**
 * sentinel.js — Placeholder para futura detecção de anomalias
 * Preparado para receber dados via EventBus quando implementado.
 *
 * @param {HTMLElement} container
 * @returns {Function} teardown
 */

export async function renderSentinelPage(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <div class="page-title"><span class="page-icon">🛡️</span> Sentinel</div>
        <div class="page-subtitle">Detecção de anomalias e monitoramento de qualidade dos providers de LLM</div>
      </div>
      <div class="page-actions">
        <span class="badge badge-warning">EM BREVE</span>
      </div>
    </div>
    <div class="page-body">

      <!-- Hero da feature futura -->
      <div class="card" style="padding:48px 24px;text-align:center;">
        <div style="font-size:64px;margin-bottom:16px;opacity:.7;filter:drop-shadow(0 0 20px rgba(245,158,11,.3));">🛡️</div>
        <div style="font-size:20px;font-weight:700;margin-bottom:8px;color:var(--ink);">Sentinel — Inteligência de Anomalias</div>
        <div style="font-size:13px;color:var(--ink-2);max-width:480px;margin:0 auto 24px;line-height:1.7;">
          O Sentinel será responsável por monitorar a <strong>qualidade e consistência</strong> dos providers de LLM em tempo real,
          detectando degradação de performance, alucinações persistentes e desvios comportamentais.
        </div>
        <div class="stats-grid" style="max-width:600px;margin:0 auto 32px;grid-template-columns:repeat(3,1fr);">
          <div class="stat-card" style="opacity:.6;">
            <div class="stat-label">Anomalias Detectadas</div>
            <div class="stat-value">—</div>
            <div class="stat-sub">Aguardando dados</div>
          </div>
          <div class="stat-card" style="opacity:.6;">
            <div class="stat-label">Score de Qualidade</div>
            <div class="stat-value">—</div>
            <div class="stat-sub">Por provider</div>
          </div>
          <div class="stat-card" style="opacity:.6;">
            <div class="stat-label">Alertas Ativos</div>
            <div class="stat-value">—</div>
            <div class="stat-sub">Threshold configurável</div>
          </div>
        </div>

        <!-- Roadmap visual -->
        <div style="border-top:1px solid var(--border);padding-top:24px;max-width:560px;margin:0 auto;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-2);margin-bottom:16px;">Roadmap de Funcionalidades</div>
          <div style="display:flex;flex-direction:column;gap:10px;text-align:left;">
            ${[
              ['🔍', 'Detecção de degradação de qualidade por provider', 'PLANEJADO'],
              ['📊', 'Score de consistência de respostas ao longo do tempo', 'PLANEJADO'],
              ['⚠️', 'Alertas configuráveis com threshold customizável', 'PLANEJADO'],
              ['🔄', 'Fallback automático para provider alternativo', 'FUTURO'],
              ['📈', 'Dashboard de tendências e análise histórica', 'FUTURO'],
            ].map(([icon, desc, status]) => `
              <div style="display:flex;align-items:center;gap:12px;padding:8px 12px;background:var(--surface-2);border-radius:8px;border:1px solid var(--border);">
                <span style="font-size:16px;">${icon}</span>
                <span style="flex:1;font-size:12px;color:var(--ink)">${desc}</span>
                <span class="tag">${status}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- Preparado para EventBus -->
      <div class="alert alert-info" style="font-size:12px;">
        <div class="alert-icon">ℹ️</div>
        <div>
          <strong>Nota arquitetural:</strong> Esta view já está conectada ao EventBus central.
          Quando o backend emitir eventos <code>sentinel:anomaly</code> via WebSocket ou polling,
          este painel será atualizado automaticamente sem necessidade de refatoração.
        </div>
      </div>

    </div>
  `;

  return () => {};
}
