/**
 * store.js — Gerenciador de estado global simples (PubSub)
 * Sem dependências externas. Reativo via EventBus.
 */

const _state = {
  route: 'workspace',
  connected: false,
  activeAgent: 'main',
  agents: [],
  providers: [],
  models: [],
  health: null,
};

const _listeners = {};

export const store = {
  /** Lê um valor do estado */
  get(key) {
    return _state[key];
  },

  /** Atualiza e notifica listeners */
  set(key, value) {
    _state[key] = value;
    if (_listeners[key]) {
      _listeners[key].forEach(fn => fn(value));
    }
    if (_listeners['*']) {
      _listeners['*'].forEach(fn => fn({ key, value }));
    }
  },

  /** Observa mudanças em uma chave específica (ou '*' para qualquer) */
  on(key, fn) {
    if (!_listeners[key]) _listeners[key] = [];
    _listeners[key].push(fn);
    return () => {
      _listeners[key] = _listeners[key].filter(f => f !== fn);
    };
  },

  /** Retorna snapshot completo do estado */
  getAll() {
    return { ..._state };
  },
};
