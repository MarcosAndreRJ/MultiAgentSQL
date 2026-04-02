/**
 * modal.js — Factory de modais nativos reutilizável
 * Cria, controla e destrói overlays sem Alpine.
 */

let _activeModal = null;

/**
 * Abre um modal genérico.
 * @param {object} opts
 * @param {string} opts.title
 * @param {string|Node} opts.body  — HTML string ou Node
 * @param {Array<{label,type,onClick}>} opts.actions — botões do footer
 * @param {string} [opts.size]  — 'sm' | '' | 'lg'
 * @param {Function} [opts.onClose]
 * @returns {{ el: HTMLElement, close: Function }}
 */
export function openModal({ title, body, actions = [], size = '', onClose } = {}) {
  closeModal();

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'active-modal-overlay';

  const box = document.createElement('div');
  box.className = `modal-box${size ? ' modal-' + size : ''}`;

  // Header
  const header = document.createElement('div');
  header.className = 'modal-header';
  header.innerHTML = `
    <span class="modal-title">${title}</span>
    <button class="modal-close" id="modal-close-btn">&#x2715;</button>
  `;
  box.appendChild(header);

  // Body
  const bodyEl = document.createElement('div');
  bodyEl.className = 'modal-body';
  if (typeof body === 'string') {
    bodyEl.innerHTML = body;
  } else if (body instanceof Node) {
    bodyEl.appendChild(body);
  }
  box.appendChild(bodyEl);

  // Footer
  if (actions.length > 0) {
    const footer = document.createElement('div');
    footer.className = 'modal-footer';
    for (const action of actions) {
      const btn = document.createElement('button');
      btn.className = `btn btn-${action.type || 'secondary'}`;
      btn.textContent = action.label;
      btn.addEventListener('click', () => {
        if (action.onClick) action.onClick(close);
        else close();
      });
      footer.appendChild(btn);
    }
    box.appendChild(footer);
  }

  overlay.appendChild(box);
  document.body.appendChild(overlay);
  _activeModal = overlay;

  // Fechar pelo X ou click fora
  const close = () => {
    overlay.remove();
    _activeModal = null;
    if (onClose) onClose();
  };

  document.getElementById('modal-close-btn')?.addEventListener('click', close);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

  // ESC
  const escHandler = (e) => { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', escHandler); } };
  document.addEventListener('keydown', escHandler);

  return { el: box, bodyEl, close };
}

/**
 * Modal de confirmação simples.
 */
export function confirmModal({ title = 'Confirmar', message, confirmLabel = 'Confirmar', danger = false, onConfirm }) {
  return openModal({
    title,
    size: 'sm',
    body: `<p style="color:var(--ink);font-size:13px;line-height:1.6;">${message}</p>`,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: confirmLabel,
        type: danger ? 'danger' : 'primary',
        onClick: (close) => {
          if (onConfirm) onConfirm();
          close();
        },
      },
    ],
  });
}

/** Fecha qualquer modal ativo */
export function closeModal() {
  if (_activeModal) {
    _activeModal.remove();
    _activeModal = null;
  }
}
