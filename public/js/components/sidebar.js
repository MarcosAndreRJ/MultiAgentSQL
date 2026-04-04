/**
 * sidebar.js - Side navigation controller
 * Renders menu and syncs active item with route.
 */

import { store } from '../store.js';

const NAV_ITEMS = [
  {
    section: 'WORKSPACE',
    items: [
      { route: 'workspace', icon: 'C', label: 'Chat' },
    ],
  },
  {
    section: 'MANAGEMENT',
    items: [
      { route: 'providers', icon: 'P', label: 'Providers' },
      { route: 'models', icon: 'M', label: 'Models' },
      { route: 'agents', icon: 'A', label: 'Agents' },
    ],
  },
  {
    section: 'OBSERVABILITY',
    items: [
      { route: 'health', icon: 'H', label: 'Health' },
      { route: 'sentinel', icon: 'S', label: 'Sentinel' },
    ],
  },
];

export function initSidebar(navEl, onNavigate) {
  renderSidebar(navEl, store.get('route'), onNavigate);

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

    const divider = document.createElement('div');
    divider.className = 'sidebar-divider';
    navEl.appendChild(divider);
  }
}

function updateActiveItem(navEl, activeRoute) {
  navEl.querySelectorAll('.nav-item').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.route === activeRoute);
  });
}
