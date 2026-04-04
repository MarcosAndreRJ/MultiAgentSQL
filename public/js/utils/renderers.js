/**
 * renderers.js — Helpers de Renderização UI (Apresentação)
 * Responsável por transformar DADOS em ELEMENTOS visuais.
 */
import { el, badge } from './dom.js';

/**
 * Renderiza o tipo do provider com cores específicas.
 * @param {string} type 
 */
export function renderProviderType(type) {
  const types = {
    'openai':    'info',
    'anthropic': 'warning',
    'gemini':    'success',
    'ollama':    'muted',
    'custom':    'primary',
  };
  const color = types[type?.toLowerCase()] || 'muted';
  return el('span', { 
    class: `badge badge-${color}`,
    style: 'text-transform:uppercase; font-size:10px;'
  }, type || '—');
}

/**
 * Renderiza um badge de status operacional.
 * @param {string} status 
 * @param {string} [message]
 */
export function renderStatusBadge(status) {
  const cfg = {
    'ok':      { color: 'success', label: 'ONLINE' },
    'online':  { color: 'success', label: 'ONLINE' },
    'error':   { color: 'danger',  label: 'OFFLINE' },
    'offline': { color: 'danger',  label: 'OFFLINE' },
    'unknown': { color: 'muted',   label: 'DESCONHECIDO' },
    'pending': { color: 'warning', label: 'PENDENTE' },
  };
  
  const s = cfg[status?.toLowerCase()] || cfg['unknown'];
  return el('span', { class: `badge badge-${s.color}` }, s.label);
}

/**
 * Renderiza o grupo de botões de ações para as tabelas.
 * @param {object} item Objeto do item (Provider, Agent, etc)
 * @param {object} handlers Mapeamento de action names para callbacks
 */
export function renderActionButtons(item, handlers = {}) {
  const container = el('div', { class: 'col-actions' });

  // Botão Teste (opcional)
  if (handlers.test) {
    container.appendChild(el('button', {
      class: 'btn btn-sm btn-secondary',
      title: 'Testar Conexão',
      onclick: (e) => handlers.test(item, e.currentTarget)
    }, '⚡'));
  }

  // Botão Sincronizar (opcional)
  if (handlers.sync) {
    container.appendChild(el('button', {
      class: 'btn btn-sm btn-secondary',
      title: 'Sincronizar Modelos',
      onclick: (e) => handlers.sync(item, e.currentTarget)
    }, '🔄'));
  }

  // Botão Editar
  if (handlers.edit) {
    container.appendChild(el('button', {
      class: 'btn btn-sm btn-secondary',
      title: 'Editar',
      onclick: () => handlers.edit(item)
    }, '✏️'));
  }

  // Botão Excluir
  if (handlers.delete) {
    container.appendChild(el('button', {
      class: 'btn btn-sm btn-danger',
      title: 'Excluir',
      onclick: () => handlers.delete(item)
    }, '🗑️'));
  }

  return container;
}
