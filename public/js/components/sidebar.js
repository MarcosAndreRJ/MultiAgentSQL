/**
 * sidebar.js — Controle da navegação lateral (Hash Router aware)
 * Renderiza o menu e sincroniza o item ativo com a rota atual.
 */

import { store } from '../store.js';

const NAV_ITEMS = [
  // Workspace operacional
  {
    section: 'WORKSPACE',
    items: [
      { route: 'workspace', icon: '💬', label: 'Chat' },
    ],
  },
  // Gestão
  {
    section: 'MANAGEMENT',
    items: [
      { route: 'providers', icon: '🔌', label: 'Providers' },
      { route: 'models',    icon: '🧩', label: 'Models' },
      { route: 'agents',    icon: '🤖', label: 'Agents' },
    ],
  },
  // Observabilidade
  {
    section: 'OBSERVABILITY',
    items: [
      { route: 'health',   icon: '❤️', label: 'Health' },
      { route: 'sentinel', icon: '🛡️', label: 'Sentinel', badge: 'SOON' },
    ],
  },
];

/**
 * Monta o HTML do sidebar nav e ativa listeners de clique.
 * @param {HTMLElement} navEl — o elemento #sidebar-nav
 * @param {Function} onNavigate — callback(route)
 */
export function initSidebar(navEl, onNavigate) {
  renderSidebar(navEl, store.get('route'), onNavigate);

  // Sincroniza quando a rota muda
  store.on('route', (route) => {
    updateActiveItem(navEl, route);
  });
}

function renderSidebar(navEl, currentRoute, onNavigate) {
  navEl.innerHTML = '';

  for (const group of NAV_ITEMS) {
    const section = document.createElement('div');
    section.className = 'sidebar-section';

    const label = document.createElement('div');
    label.className = 'sidebar-section-label';
    label.textContent = group.section;
    section.appendChild(label);

    for (const item of group.items) {
      const btn = document.createElement('button');
      btn.className = `nav-item${currentRoute === item.route ? ' active' : ''}`;
      btn.dataset.route = item.route;

      btn.innerHTML = `
        <span class="nav-icon">${item.icon}</span>
        <span>${item.label}</span>
        ${item.badge ? `<span class="nav-badge">${item.badge}</span>` : ''}
      `;

      btn.addEventListener('click', () => {
        window.location.hash = item.route;
        onNavigate(item.route);
      });

      section.appendChild(btn);
    }

    navEl.appendChild(section);

    // Divider entre grupos
    const divider = document.createElement('div');
    divider.className = 'sidebar-divider';
    navEl.appendChild(divider);
  }
}

function updateActiveItem(navEl, activeRoute) {
  navEl.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.route === activeRoute);
  });
}
