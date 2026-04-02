/**
 * models.js — View de Lista de Modelos por Provider
 * Consulta o registry do backend de modelos suportados.
 *
 * @param {HTMLElement} container
 * @returns {Function} teardown
 */

import { api }           from '../api.js';
import { createTable, badge, showLoading, showError } from '../utils/dom.js';

export async function renderModelsPage(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <div class="page-title"><span class="page-icon">🧩</span> Modelos Disponíveis</div>
        <div class="page-subtitle">Registry de modelos suportados por cada Provider</div>
      </div>
      <div class="page-actions">
        <div class="filter-bar" style="padding:0;margin:0;">
          <div class="filter-search">
            <span class="filter-search-icon">🔍</span>
            <input type="text" id="model-search" placeholder="Filtrar modelos..." />
          </div>
        </div>
      </div>
    </div>
    <div class="page-body">
      <div class="card">
        <div class="card-header">
          <span>Modelos</span>
          <span id="model-count" class="text-muted"></span>
        </div>
        <div id="models-table-wrap"></div>
      </div>
    </div>
  `;

  let allModels = [];
  const wrap = container.querySelector('#models-table-wrap');
  const countEl = container.querySelector('#model-count');
  const searchInput = container.querySelector('#model-search');

  function renderTable(models) {
    countEl.textContent = `${models.length} modelo(s)`;
    if (models.length === 0) {
      wrap.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🧩</div>
          <div class="empty-state-title">Nenhum modelo encontrado</div>
          <div class="empty-state-sub">Verifique se os providers estão configurados e online.</div>
        </div>
      `;
      return;
    }

    const rows = models.map(m => [
      `<span class="text-mono">${m.name || m.id || '—'}</span>`,
      m.provider || '—',
      m.contextWindow ? `${(m.contextWindow / 1000).toFixed(0)}K tokens` : '—',
      m.toolCalling
        ? `<span class="badge badge-success">✓ Tool Calling</span>`
        : `<span class="badge badge-muted">—</span>`,
    ]);

    const table = createTable(['Modelo', 'Provider', 'Context Window', 'Capabilities'], rows);
    wrap.innerHTML = '';
    wrap.appendChild(table);
  }

  showLoading(wrap, 'Carregando modelos...');
  try {
    const data = await api.getModels();
    allModels = data.models || [];
    renderTable(allModels);
  } catch (err) {
    showError(wrap, `Falha ao carregar modelos: ${err.message}`);
  }

  // Filtro em tempo real
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.toLowerCase();
    const filtered = allModels.filter(m =>
      (m.name || m.id || '').toLowerCase().includes(q) ||
      (m.provider || '').toLowerCase().includes(q)
    );
    renderTable(filtered);
  });

  return () => {}; // teardown
}
