/**
 * dom.js — Helpers para manipulação do DOM
 * Funções puras para criar/atualizar elementos.
 */

/**
 * Cria um elemento com atributos e filhos opcionais.
 * @param {string} tag
 * @param {object} [attrs]
 * @param {...(string|Node|{html:string})} children
 */
export function el(tag, attrs = {}, ...children) {
  const elem = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (key === 'class') {
      elem.className = val;
    } else if (key.startsWith('on') && typeof val === 'function') {
      elem.addEventListener(key.slice(2).toLowerCase(), val);
    } else if (key === 'dataset') {
      Object.assign(elem.dataset, val);
    } else {
      elem.setAttribute(key, val);
    }
  }
  for (const child of children) {
    if (child == null) continue;
    if (typeof child === 'string') {
      // Check if it looks like HTML/SVG markup, then insert properly
      if (child.trim().startsWith('<')) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = child;
        while (wrapper.firstChild) {
          elem.appendChild(wrapper.firstChild);
        }
      } else {
        elem.appendChild(document.createTextNode(child));
      }
    } else if (child.html && typeof child.html === 'string') {
      // Support { html: '<svg>...</svg>' } pattern for raw markup
      const wrapper = document.createElement('div');
      wrapper.innerHTML = child.html;
      while (wrapper.firstChild) {
        elem.appendChild(wrapper.firstChild);
      }
    } else if (child instanceof Node) {
      elem.appendChild(child);
    } else {
      elem.appendChild(document.createTextNode(String(child)));
    }
  }
  return elem;
}

/**
 * Renderiza HTML seguro em um container, limpando primeiro.
 */
export function setHTML(container, html) {
  container.innerHTML = html;
}

/**
 * Cria um badge de status.
 * @param {'success'|'warning'|'danger'|'info'|'muted'} type
 * @param {string} label
 */
export function badge(type, label) {
  const span = document.createElement('span');
  span.className = `badge badge-${type}`;
  span.textContent = label;
  return span;
}

/**
 * Cria uma tabela densa padronizada.
 * @param {string[]} headers
 * @param {Array<Array<string|Node>>} rows
 */
export function createTable(headers, rows) {
  const thead = el('thead', {},
    el('tr', {}, ...headers.map(h => el('th', {}, h)))
  );

  const tbody = el('tbody', {});
  for (const row of rows) {
    const tr = el('tr', {});
    for (const cell of row) {
      const td = el('td', {});
      if (cell == null) {
        td.textContent = '—';
      } else if (cell instanceof Node) {
        td.appendChild(cell);
      } else if (typeof cell === 'string' && cell.trim().startsWith('<')) {
        // Renderiza como HTML se a string começar com '<' (mesmo com espaços)
        td.innerHTML = cell.trim();
      } else {
        td.textContent = String(cell);
      }

      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }

  const table = el('table', { class: 'data-table' }, thead, tbody);
  return table;
}

/**
 * Retorna o container de uma view, criando se não existir.
 */
export function getOrCreate(id, tag = 'div') {
  return document.getElementById(id) || (() => {
    const elem = document.createElement(tag);
    elem.id = id;
    return elem;
  })();
}

/**
 * Mostra loading state em um container.
 */
export function showLoading(container, msg = 'Carregando...') {
  container.innerHTML = `
    <div class="empty-state fade-in">
      <span class="spinner"></span>
      <span class="text-muted">${msg}</span>
    </div>
  `;
}

/**
 * Mostra erro em um container.
 */
export function showError(container, msg = 'Erro ao carregar dados.') {
  container.innerHTML = `
    <div class="empty-state fade-in">
      <div class="empty-state-icon">⚠️</div>
      <div class="empty-state-title text-danger">${msg}</div>
    </div>
  `;
}

/**
 * Clona um <template> por id.
 */
export function cloneTemplate(id) {
  const tpl = document.getElementById(id);
  if (!tpl) throw new Error(`Template #${id} não encontrado`);
  return tpl.content.cloneNode(true);
}

/**
 * Toast notification leve
 */
export function toast(msg, type = 'info', duration = 3000) {
  const existing = document.getElementById('toast-container');
  const container = existing || (() => {
    const c = document.createElement('div');
    c.id = 'toast-container';
    c.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(c);
    return c;
  })();

  const colors = {
    info:    { bg: 'var(--blue-dim)', border: 'rgba(96,165,250,.3)', color: 'var(--blue)' },
    success: { bg: 'var(--green-dim)', border: 'rgba(34,197,94,.3)', color: 'var(--green)' },
    warning: { bg: 'var(--yellow-dim)', border: 'rgba(245,158,11,.3)', color: 'var(--yellow)' },
    danger:  { bg: 'var(--red-dim)', border: 'rgba(239,68,68,.3)', color: 'var(--red)' },
  };

  const c = colors[type] || colors.info;
  const toast = document.createElement('div');
  toast.style.cssText = `
    background:${c.bg};border:1px solid ${c.border};color:${c.color};
    padding:10px 16px;border-radius:8px;font-size:12px;font-weight:500;
    box-shadow:0 4px 12px rgba(0,0,0,.3);animation:fadeIn .2s ease;
    max-width:300px;font-family:inherit;
  `;
  toast.textContent = msg;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity .3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
