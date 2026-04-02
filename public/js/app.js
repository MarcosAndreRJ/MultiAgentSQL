/**
 * app.js — Ponto de entrada do Dashboard MultiAgentSQL
 * Responsabilidades:
 *   - Inicializar o sidebar
 *   - Gerenciar o Hash Router
 *   - Carregar e destruir páginas conforme a rota
 */

import { store }       from './store.js';
import { initSidebar } from './components/sidebar.js';
import { closeRightPanel } from './components/panel.js';

// ── Registro de páginas (lazy import por rota) ──────────────────
const ROUTES = {
  workspace: () => import('./pages/workspace.js').then(m => m.renderWorkspacePage),
  providers: () => import('./pages/providers.js').then(m => m.renderProvidersPage),
  models:    () => import('./pages/models.js').then(m => m.renderModelsPage),
  agents:    () => import('./pages/agents.js').then(m => m.renderAgentsPage),
  health:    () => import('./pages/health.js').then(m => m.renderHealthPage),
  sentinel:  () => import('./pages/sentinel.js').then(m => m.renderSentinelPage),
};

// ── Referências ao DOM ───────────────────────────────────────────
const mainContent  = document.getElementById('main-content');
const sidebarNav   = document.getElementById('sidebar-nav');
const btnSettings  = document.getElementById('btn-settings');


// ── Cleanup de página anterior ───────────────────────────────────
let _pageTeardown = null;

function teardownCurrentPage() {
  if (typeof _pageTeardown === 'function') {
    _pageTeardown();
    _pageTeardown = null;
  }
}

// ── Right panel — centralizado em components/panel.js ────────────

// ── Navegar para uma rota ────────────────────────────────────────
async function navigate(route) {
  const knownRoute = ROUTES[route] ? route : 'workspace';

  if (store.get('route') === knownRoute && _pageTeardown !== null) return;

  store.set('route', knownRoute);
  closeRightPanel();
  teardownCurrentPage();

  // Loading state
  mainContent.innerHTML = `
    <div class="empty-state fade-in" style="margin:auto;">
      <span class="spinner"></span>
      <span class="text-muted">Carregando ${knownRoute}...</span>
    </div>
  `;

  try {
    const renderFn = await ROUTES[knownRoute]();
    const teardown = await renderFn(mainContent);
    _pageTeardown = teardown || null;
  } catch (err) {
    console.error(`[Router] Falha ao renderizar rota "${knownRoute}":`, err);
    mainContent.innerHTML = `
      <div class="empty-state fade-in" style="margin:auto;">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title text-danger">Erro ao carregar a página</div>
        <div class="empty-state-sub">${err.message}</div>
      </div>
    `;
  }
}

// ── Hash Router ──────────────────────────────────────────────────
function getRouteFromHash() {
  return (window.location.hash || '').replace('#', '').trim() || 'workspace';
}

window.addEventListener('hashchange', () => navigate(getRouteFromHash()));

// ── Botão de Settings (atalho para config do workspace) ─────────
btnSettings?.addEventListener('click', () => {
  window.location.hash = 'workspace';
  navigate('workspace');
  // Dispara evento para o workspace abrir o painel de config
  setTimeout(() => document.dispatchEvent(new CustomEvent('ws:open-settings')), 100);
});

// ── Bootstrap ───────────────────────────────────────────────────
function init() {
  // Inicializa sidebar com callback de navegação
  initSidebar(sidebarNav, (route) => navigate(route));

  // Navega para a rota inicial do hash (ou workspace)
  navigate(getRouteFromHash());
}

init();
