/**
 * panel.js — Controle do Right Panel (coluna direita)
 * Módulo independente para evitar importações circulares com app.js.
 */

const rightPanel = () => document.getElementById('right-panel');
const rightPanelContent = () => document.getElementById('right-panel-content');

/**
 * Abre o right panel com o conteúdo fornecido.
 * @param {HTMLElement|null} contentEl — elemento a inserir no painel
 */
export function openRightPanel(contentEl) {
  const panel = rightPanel();
  const container = rightPanelContent();
  if (!panel || !container) return;

  container.innerHTML = '';
  if (contentEl) container.appendChild(contentEl);
  panel.classList.remove('collapsed');
}

/**
 * Fecha o right panel.
 */
export function closeRightPanel() {
  const panel = rightPanel();
  if (!panel) return;
  panel.classList.add('collapsed');
}

/**
 * Toggle do right panel.
 */
export function toggleRightPanel(contentEl) {
  const panel = rightPanel();
  if (!panel) return;
  if (panel.classList.contains('collapsed')) {
    openRightPanel(contentEl);
  } else {
    closeRightPanel();
  }
}
