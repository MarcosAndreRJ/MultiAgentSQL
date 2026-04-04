/**
 * models.js — Catálogo de modelos em cards agrupados por provider.
 * Consome /api/models/catalog para uma visualização estruturada.
 */

import { api } from '../api.js';
import { el, badge, showLoading, showError, toast } from '../utils/dom.js';

function placeholderText(value) {
  return value || '—';
}

function formatContextWindow(cw) {
  if (!cw) return '—';
  if (cw >= 1000) return `${(cw / 1000).toFixed(0)}k tokens`;
  return `${cw} tokens`;
}

function renderCapabilities(model) {
  const wrap = el('div', { class: 'cap-list' });
  const caps = [];

  if (model.supports_tools) caps.push({ label: 'Tools', class: 'cap-tools' });
  if (model.supports_json) caps.push({ label: 'JSON', class: 'cap-json' });
  if (model.supports_streaming) caps.push({ label: 'Stream', class: 'cap-stream' });

  if (caps.length === 0) {
    wrap.appendChild(el('span', { class: 'text-muted', style: 'font-size:10px;' }, 'Básico'));
  } else {
    caps.forEach(cap => {
      const badgeElem = el('span', { class: `cap-badge ${cap.class}` }, cap.label);
      wrap.appendChild(badgeElem);
    });
  }
  
  return wrap;
}

function renderStatusBadge(model) {
  if (!model.is_available) {
    return badge('muted', 'Indisponível');
  }
  if (!model.is_active) {
    return badge('danger', 'Inativo');
  }
  return badge('success', 'Ativo');
}

function createModelCard(model) {
  const card = el('div', { class: 'model-catalog-card h-fade-in' });

  const header = el('div', { class: 'model-card-header' });
  const info = el('div', { class: 'model-card-info' });
  info.appendChild(el('div', { class: 'model-card-display' }, placeholderText(model.display_name)));
  info.appendChild(el('div', { class: 'model-card-id' }, model.model_id));
  header.appendChild(info);
  header.appendChild(renderStatusBadge(model));

  const stats = el('div', { class: 'model-card-stats' });
  stats.appendChild(el('div', { class: 'stat-box' }, 
    el('span', { class: 'stat-label' }, 'Contexto'),
    el('span', { class: 'stat-value' }, formatContextWindow(model.context_window))
  ));
  stats.appendChild(el('div', { class: 'stat-box' }, 
    el('span', { class: 'stat-label' }, 'Fonte'),
    el('span', { class: 'stat-value' }, model.source === 'sync' ? 'Auto·Sync' : model.source)
  ));

  const footer = el('div', { class: 'model-card-footer' });
  footer.appendChild(renderCapabilities(model));

  card.appendChild(header);
  card.appendChild(stats);
  card.appendChild(footer);
  
  return card;
}

function createProviderSection(provider, models, onSync) {
  const section = el('div', { class: 'provider-section fade-in' });
  
  const sHeader = el('div', { class: 'provider-section-header', style: 'cursor:pointer;' });
  
  // Expand/collapse icon
  const expandIcon = el('span', { class: 'expand-icon expanded' }, '▼');
  const providerIcon = el('span', { class: 'provider-icon' }, '🏢');
  const providerName = el('span', { class: 'provider-name' }, provider.name);
  const modelCount = el('span', { class: 'model-tag' }, `${models.length} modelos`);
  
  const syncBtn = el('button', { 
    class: 'btn btn-secondary btn-sm btn-icon-text',
    style: 'margin-left:auto;',
    onClick: (e) => {
      e.stopPropagation();
      onSync(provider.id, e.currentTarget);
    }
  }, '⟳', ' Sincronizar');

  sHeader.appendChild(expandIcon);
  sHeader.appendChild(providerIcon);
  sHeader.appendChild(providerName);
  sHeader.appendChild(modelCount);
  sHeader.appendChild(syncBtn);

  const grid = el('div', { class: 'models-grid' });
  
  if (models.length === 0) {
    grid.appendChild(el('div', { class: 'no-models-message' }, 'Nenhum modelo sincronizado para este provedor. Clique em sincronizar.'));
  } else {
    models.forEach(m => grid.appendChild(createModelCard(m)));
  }

  // Collapse logic
  let isExpanded = true;
  const toggle = () => {
    isExpanded = !isExpanded;
    expandIcon.textContent = isExpanded ? '▼' : '▶';
    expandIcon.classList.toggle('expanded', isExpanded);
    grid.style.display = isExpanded ? '' : 'none';
  };
  
  sHeader.addEventListener('click', toggle);

  section.appendChild(sHeader);
  section.appendChild(grid);
  
  return section;
}

function renderCatalog(wrap, catalog, onSync) {
  wrap.innerHTML = '';

  if (catalog.length === 0) {
    wrap.appendChild(el('div', { class: 'empty-state' },
      el('div', { class: 'empty-state-icon' }, '🧩'),
      el('div', { class: 'empty-state-title' }, 'Nenhum provider ativo'),
      el('div', { class: 'empty-state-sub' }, 'Adicione e ative pelo menos um provider para ver os modelos.')
    ));
    return;
  }

  catalog.forEach(item => {
    const { provider, models } = item;
    const section = createProviderSection(provider, models, onSync);
    wrap.appendChild(section);
  });
}

function createScrollToTopButton() {
  const btn = el('button', {
    id: 'scroll-to-top',
    class: 'scroll-to-top-btn',
    style: 'display:none;'
  }, '↑');
  
  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  
  document.body.appendChild(btn);
  
  let scrollTimeout;
  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      if (window.scrollY > 300) {
        btn.style.display = 'flex';
      } else {
        btn.style.display = 'none';
      }
    }, 50);
  });
}

async function handleSync(providerId, btn) {
  const original = btn.innerHTML;
  btn.classList.add('loading-btn');
  btn.disabled = true;
  btn.innerHTML = '⟳ Sincronizando...';

  try {
    const res = await api.syncProviderModels(providerId);
    toast(res.message, 'success');
    window.dispatchEvent(new CustomEvent('models-updated'));
  } catch (err) {
    toast(`Falha ao sincronizar: ${err.message}`, 'danger');
  } finally {
    btn.innerHTML = original;
    btn.classList.remove('loading-btn');
    btn.disabled = false;
  }
}

export async function renderModelsPage(container) {
  // Add scroll-to-top button once
  if (!document.getElementById('scroll-to-top')) {
    createScrollToTopButton();
  }

  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <div class="page-title"><span class="page-icon">🧩</span> Catálogo de Models</div>
        <div class="page-subtitle">Modelos técnicos detectados nos provedores ativos via sincronização automática.</div>
      </div>
      <div class="page-actions">
        <div class="filter-bar no-margin">
          <div class="filter-search">
            <span class="filter-search-icon">🔍</span>
            <input type="text" id="model-search" placeholder="Filtrar modelos ou providers..." />
          </div>
        </div>
      </div>
    </div>
    <div class="page-body">
      <div id="models-catalog-container"></div>
    </div>
  `;

  const wrap = container.querySelector('#models-catalog-container');
  const searchInput = container.querySelector('#model-search');
  let currentCatalog = [];

  async function loadData() {
    showLoading(wrap, 'Obtendo catálogo de modelos...');
    try {
      currentCatalog = await api.getModelsCatalog();
      renderCatalog(wrap, currentCatalog, handleSync);
    } catch (err) {
      showError(wrap, `Erro ao carregar catálogo: ${err.message}`);
    }
  }

  window.addEventListener('models-updated', loadData);

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.toLowerCase();
    const filtered = currentCatalog.map(item => ({
      ...item,
      models: item.models.filter(m => 
        m.model_id.toLowerCase().includes(q) || 
        (m.display_name || '').toLowerCase().includes(q) ||
        item.provider.name.toLowerCase().includes(q)
      )
    })).filter(item => item.models.length > 0 || item.provider.name.toLowerCase().includes(q));
    
    renderCatalog(wrap, filtered, handleSync);
  });

  await loadData();

  return () => {
    window.removeEventListener('models-updated', loadData);
  };
}