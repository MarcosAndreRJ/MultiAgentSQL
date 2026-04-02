/**
 * MultiAgent SQL - Frontend Application Logic
 * Interface de chat multi-agente com suporte a pending actions.
 * v3: Tabelas para listas, som de resposta, botão copiar.
 */

const API_BASE = '';
const STORAGE_PREFIX = 'multiagentsql_';

// ─── Estado Global ─────────────────────────────────────────────
const state = {
  selectedAgent: null,
  sessionId: null,
  isLoading: false,
  pendingActions: [],
  attachedFiles: [],
  lastUserMessage: '',
  historyIndex: -1,
  currentInputTemp: ''
};

// ─── Bootstrap ────────────────────────────────────────────────â”€
document.addEventListener('DOMContentLoaded', () => {
  loadAgents();
  checkOllama();
  setupInput();
  setupAutocomplete();
  setupUpload();
  setupRefresh();
  setupEventsToggle();
  setInterval(refreshPending, 10000);
});

function setupEventsToggle() {
  const toggle = document.getElementById('showEventsToggle');
  const body = document.body;
  
  // Carregar preferência
  const hideEvents = localStorage.getItem('hide_events') === 'true';
  if (toggle) {
    toggle.checked = !hideEvents;
    if (hideEvents) body.classList.add('hide-events');
    
    toggle.addEventListener('change', () => {
      const isVisible = toggle.checked;
      if (isVisible) {
        body.classList.remove('hide-events');
        localStorage.setItem('hide_events', 'false');
      } else {
        body.classList.add('hide-events');
        localStorage.setItem('hide_events', 'true');
      }
    });
  }
}

// ─── localStorage Helpers ────────────────────────────────────â”€â”€
function storageKey(type, agentId) {
  return `${STORAGE_PREFIX}${type}_${agentId}`;
}

function saveChat(agentId, messages) {
  try {
    localStorage.setItem(storageKey('chat', agentId), JSON.stringify(messages));
  } catch (e) { /* quota exceeded */ }
}

function loadChat(agentId) {
  try {
    const raw = localStorage.getItem(storageKey('chat', agentId));
    return raw ? JSON.parse(raw) : [];
  } catch (e) { return []; }
}

function saveSessionId(agentId, sessionId) {
  localStorage.setItem(storageKey('session', agentId), sessionId);
}

function loadSessionId(agentId) {
  return localStorage.getItem(storageKey('session', agentId)) || null;
}

function clearChatStorage(agentId) {
  localStorage.removeItem(storageKey('chat', agentId));
  localStorage.removeItem(storageKey('session', agentId));
}

// Chat message store in memory (mirrors localStorage)
let _chatMessages = []; // [{role, html, time}]

function recordMessage(role, html, time, model, executionSource, latencyMs, usedLlm, type = 'message', runId = null, id = null, executionResult = null, contentRaw = null) {
  _chatMessages.push({ role, html, time, model, executionSource, latencyMs, usedLlm, type, runId, id, executionResult, content_raw: contentRaw });
  if (state.selectedAgent) {
    saveChat(state.selectedAgent, _chatMessages);
  }
}

// ─── Refresh Button ──────────────────────────────────────────â”€â”€
function setupRefresh() {
  const btn = document.getElementById('refreshAgentsBtn');
  if (btn) {
    btn.addEventListener('click', refreshAgents);
  }
}

async function refreshAgents() {
  const btn = document.getElementById('refreshAgentsBtn');
  if (!btn || btn.classList.contains('loading')) return;

  btn.classList.add('loading');
  try {
    const res = await fetch(`${API_BASE}/api/agents/reload`, { method: 'POST' });
    if (res.ok) {
      await loadAgents();
      if (state.selectedAgent) {
        await loadAgentDetail(state.selectedAgent);
        updateChatHeader(state.selectedAgent);
      }
      const originalText = btn.innerHTML;
      btn.innerHTML = '<span class="icon">\u{2705}</span> Atualizado';
      setTimeout(() => { btn.innerHTML = originalText; }, 2000);
    }
  } catch (e) {
    console.error('Erro ao recarregar agentes:', e);
  } finally {
    btn.classList.remove('loading');
  }
}

// ─── Agentes ───────────────────────────────────────────────────
async function loadAgents() {
  try {
    const res = await fetch(`${API_BASE}/api/agents/`);
    const agents = await res.json();
    renderAgentList(agents);
  } catch (e) {
    document.getElementById('agentList').innerHTML =
      '<div class="empty-state">Erro ao carregar agentes</div>';
  }
}

function renderAgentList(agents) {
  const list = document.getElementById('agentList');
  if (!agents.length) {
    list.innerHTML = '<div class="empty-state">Nenhum agente configurado</div>';
    return;
  }

  list.innerHTML = agents.map(agent => `
    <div class="agent-item" id="agent-item-${agent.id}" onclick="selectAgent('${agent.id}')">
      <div class="agent-avatar ${agent.type === 'principal' ? 'principal' : 'specialist'}">
        ${agent.type === "principal" ? "\u{1F9E0}" : "\u{1F6E2}\u{FE0F}"}
      </div>
      <div class="agent-info">
        <div class="agent-name">${agent.name}</div>
        <div class="agent-type">${agent.type}</div>
      </div>
      ${agent.database_name
        ? `<div class="agent-badge db">${agent.database_name}</div>`
        : '<div class="agent-badge">geral</div>'
      }
    </div>
  `).join('');
}

async function selectAgent(agentId) {
  document.querySelectorAll('.agent-item').forEach(el => el.classList.remove('active'));
  document.getElementById(`agent-item-${agentId}`)?.classList.add('active');

  state.selectedAgent = agentId;

  // Restore or create session
  const savedSession = loadSessionId(agentId);
  if (savedSession) {
    state.sessionId = savedSession;
  } else {
    state.sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    saveSessionId(agentId, state.sessionId);
  }

  // Carregar detalhes do agente
  await loadAgentDetail(agentId);

  // Restaurar ou limpar chat
  restoreChat(agentId);
  enableInput();

  // Atualizar cabeçalho
  updateChatHeader(agentId);
}

// ─── Chat Persistence ──────────────────────────────────────────
function restoreChat(agentId) {
  const msgs = document.getElementById('messages');
  const saved = loadChat(agentId);
  _chatMessages = saved;

  if (!saved.length) {
    msgs.innerHTML = `
      <div class="welcome-message">
        <div class="welcome-icon">\u{1F4AC}</div>
        <h2>Nova conversa</h2>
        <p>Agente selecionado. Digite sua mensagem abaixo.</p>
      </div>
    `;
    return;
  }

  for (const msg of saved) {
    if (msg.type === 'event') {
      renderEventMessage(msg);
    } else {
      renderStandardMessage(msg);
    }
  }
  msgs.scrollTop = msgs.scrollHeight;
}

function renderEventMessage(msg) {
  const msgs = document.getElementById('messages');
  const el = document.createElement('div');
  const status = msg.status || (msg.metadata?.status) || 'active';
  el.className = `message event run-${msg.runId}`;
  el.id = msg.id;
  
  el.innerHTML = `
    <div class="message-bubble">
      <div class="event-status ${status}"></div>
      <div class="message-content">${msg.html || msg.content}</div>
    </div>
  `;
  msgs.appendChild(el);
}

function renderStandardMessage(msg) {
  const msgs = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = `message ${msg.role}`;
  el.id = msg.id; // Garantir ID no elemento para mensagens restauradas

  const avatarClass = msg.role === 'user' ? 'user-av' : 'agent-av';
  const avatarIcon = msg.role === 'user' ? '\u{1F464}' : '\u{1F916}';
  const modelBadge = msg.model ? `<span class="model-badge">${escHtmlBare(msg.model)}</span>` : '';
  const sourceLabel = msg.executionSource ? msg.executionSource.replace(/_/g, ' ').toUpperCase() : '';
  const sourceBadge = msg.executionSource ? `<span class="execution-badge source-${msg.executionSource}">${sourceLabel}</span>` : '';
  const latencyBadge = msg.latencyMs ? `<span class="execution-badge latency-badge">${Math.round(msg.latencyMs)}ms</span>` : '';
  
  const copyBtn = `<button class="copy-btn" title="Copiar" onclick="copyBubble(this)">\u{1F4CB}</button>`;
  
  // Re-formatar se tiver content_raw para garantir interatividade (listeners)
  let contentHtml = msg.html;
  if (msg.role === 'assistant' && msg.content_raw) {
      contentHtml = formatResponse(msg.content_raw, {
          executionResult: msg.executionResult,
          id: msg.id,
          pendingId: msg.pendingId // Caso queiramos restaurar badges de ação (opcional)
      });
  }

  el.innerHTML = `
    <div class="message-avatar ${avatarClass}">${avatarIcon}</div>
    <div class="message-bubble">
      ${copyBtn}
      <div class="execution-badges">${sourceBadge}${latencyBadge}${modelBadge}</div>
      <div class="message-content" data-message-id="${msg.id || ''}">${contentHtml}</div>
      <div class="message-time">${msg.time}</div>
    </div>
  `;
  msgs.appendChild(el);
}

// ─── Agent Detail ─────────────────────────────────────────────â”€â”€
async function loadAgentDetail(agentId) {
  try {
    const res = await fetch(`${API_BASE}/api/agents/${agentId}`);
    const agent = await res.json();
    renderAgentDetail(agent);
  } catch (e) {
    document.getElementById('agentDetail').innerHTML =
      '<div class="empty-state">Erro ao carregar detalhes</div>';
  }
}

function renderAgentDetail(agent) {
  const div = document.getElementById('agentDetail');

  const skills = agent.skills?.map(s => `
    <span class="skill-tag">
      ${s}
      <span class="remove-skill" onclick="removeSkill('${agent.id}', '${s}')" title="Remover">x</span>
    </span>
  `).join('') || '<span class="empty-state">Nenhuma skill</span>';

  const guards = agent.guards?.require_confirmation_for?.map(g =>
    `<div class="guard-item">${g}</div>`
  ).join('') || '';

  const digestSection = agent.database_name ? `
    <div class="detail-section" id="digest-section-${agent.id}">
      <div class="detail-label">DB Digest</div>
      <div id="digest-status-${agent.id}" class="digest-status-bar">
        <span class="digest-status-text" id="digest-status-text-${agent.id}">Carregando...</span>
      </div>
      <div class="digest-actions" style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">
        <button
          id="btn-generate-digest-${agent.id}"
          onclick="generateDigest('${agent.id}')"
          class="digest-btn digest-btn-primary"
          title="Gera ou atualiza o digest do banco">
          Gerar Digest
        </button>
        <button
          onclick="viewDigest('${agent.id}')"
          class="digest-btn"
          title="Visualiza o digest atual em nova aba">
          Ver Digest
        </button>
        <button
          id="btn-view-diagram-${agent.id}"
          onclick="openDiagram('${agent.id}')"
          class="digest-btn digest-btn-diagram"
          title="Visualiza estrutura relacional baseada no digest"
          disabled>
          Visualizar Estrutura
        </button>
      </div>
      <div id="diagram-hint-${agent.id}" class="digest-diagram-hint">Gere o digest antes de visualizar a estrutura</div>
      <div id="digest-aliases-${agent.id}" style="margin-top:6px;font-size:11px;color:var(--text-muted);"></div>
    </div>
  ` : '';

  div.innerHTML = `
    <div class="detail-section">
      <div class="detail-label">Modelo</div>
      <div class="detail-value mono">${agent.model}</div>
    </div>
    ${agent.database_name ? `
    <div class="detail-section">
      <div class="detail-label">Banco de Dados</div>
      <div class="detail-value mono">${agent.database_name}</div>
      <div style="margin-top:6px">
        <button onclick="testConnection('${agent.id}')" style="background:var(--bg-hover);border:1px solid var(--border);color:var(--text-secondary);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;">
          Testar Conexao
        </button>
        <span id="conn-status-${agent.id}" style="font-size:11px;margin-left:6px;"></span>
      </div>
    </div>
    ` : ''}
    ${digestSection}
    <div class="detail-section">
      <div class="detail-label">Skills</div>
      <div>${skills}</div>
      <div class="add-skill-form">
        <input type="text" id="newSkillInput-${agent.id}" placeholder="nome-da-skill" />
        <button onclick="addSkill('${agent.id}')">+</button>
      </div>
    </div>
    ${guards ? `
    <div class="detail-section">
      <div class="detail-label">Guard - Exige Confirmacao</div>
      <div class="guard-list">${guards}</div>
    </div>
    ` : ''}
    ${agent.prompt_preview ? `
    <div class="detail-section">
      <div class="detail-label">Prompt Base (preview)</div>
      <div class="prompt-preview">${escHtml(agent.prompt_preview)}</div>
    </div>
    ` : ''}
    <div class="detail-section">
      <button onclick="clearHistory()" style="background:var(--bg-hover);border:1px solid var(--border);color:var(--danger);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;width:100%;">
        Limpar historico local
      </button>
    </div>
  `;

  if (agent.database_name) {
    loadDigestStatus(agent.id);
  }
}

function updateChatHeader(agentId) {
  fetch(`${API_BASE}/api/agents/${agentId}`)
    .then(r => r.json())
    .then(agent => {
      document.getElementById('chatHeader').innerHTML = `
        <div class="agent-avatar ${agent.type === 'principal' ? 'principal' : 'specialist'}" style="width:36px;height:36px;font-size:16px">
          ${agent.type === "principal" ? "\u{1F9E0}" : "\u{1F6E2}\u{FE0F}"}
        </div>
        <div>
          <div class="chat-agent-name">${agent.name}</div>
          ${agent.database_name
            ? `<div class="chat-agent-db">${agent.database_name}</div>`
            : '<div class="chat-agent-db">agente generalista</div>'
          }
        </div>
      `;
    });
}

function clearHistory() {
  if (!state.selectedAgent) return;
  clearChatStorage(state.selectedAgent);
  // Also reset session so a fresh one is created
  state.sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  saveSessionId(state.selectedAgent, state.sessionId);
  _chatMessages = [];
  document.getElementById('messages').innerHTML = `
    <div class="welcome-message">
      <div class="welcome-icon">\u{1F4AC}</div>
      <h2>Histórico limpo</h2>
      <p>Uma nova sessão foi iniciada.</p>
    </div>
  `;
}

async function testConnection(agentId) {
  const span = document.getElementById(`conn-status-${agentId}`);
  span.textContent = 'Testando...';
  span.style.color = 'var(--text-muted)';
  try {
    const res = await fetch(`${API_BASE}/api/agents/${agentId}/test-connection`);
    const data = await res.json();
    if (data.success) {
      span.textContent = '✓ OK';
      span.style.color = 'var(--success)';
    } else {
      span.textContent = '✗ Falha';
      span.style.color = 'var(--danger)';
      span.title = data.message;
    }
  } catch (e) {
    span.textContent = '✗ Erro';
    span.style.color = 'var(--danger)';
  }
}

async function addSkill(agentId) {
  const input = document.getElementById(`newSkillInput-${agentId}`);
  const skillId = input.value.trim();
  if (!skillId) return;

  try {
    const res = await fetch(`${API_BASE}/api/agents/${agentId}/skills?skill_id=${encodeURIComponent(skillId)}`, {
      method: 'POST',
    });
    if (res.ok) {
      input.value = '';
      await loadAgentDetail(agentId);
    }
  } catch (e) {}
}

async function removeSkill(agentId, skillId) {
  try {
    await fetch(`${API_BASE}/api/agents/${agentId}/skills/${encodeURIComponent(skillId)}`, {
      method: 'DELETE',
    });
    await loadAgentDetail(agentId);
  } catch (e) {}
}

// ─── Chat ──────────────────────────────────────────────────────â”€
function setupInput() {
  const input = document.getElementById('messageInput');
  const btn = document.getElementById('sendBtn');

  input.addEventListener('keydown', (e) => {
    // Se o popup do autocomplete estiver visÃ­vel e tratÃ¡vel, deixamos o _acOnKeydown cuidar do Enter
    if (typeof _ac !== 'undefined' && _ac.popup && _ac.popup.classList.contains('visible')) {
      if (e.key === 'Enter' || e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'Tab') {
        return; // não envia mensagem, o AC resolve
      }
    }

    if (e.key === 'ArrowUp') {
      if (input.selectionStart === 0 && input.selectionEnd === 0) {
        const userMsgs = Array.from(document.querySelectorAll('.message.user .message-content')).map(el => el.innerText);
        if (userMsgs.length > 0) {
          if (state.historyIndex === -1) {
            state.currentInputTemp = input.value;
            state.historyIndex = userMsgs.length - 1;
          } else if (state.historyIndex > 0) {
            state.historyIndex--;
          }

          e.preventDefault();
          input.value = userMsgs[state.historyIndex];
          _syncInputHeight(input);
          _setCursorAtEnd(input);
        }
      }
    }

    if (e.key === 'ArrowDown') {
      if (input.selectionStart === input.value.length && input.selectionEnd === input.value.length) {
        const userMsgs = Array.from(document.querySelectorAll('.message.user .message-content')).map(el => el.innerText);
        if (state.historyIndex !== -1) {
          e.preventDefault();
          if (state.historyIndex < userMsgs.length - 1) {
            state.historyIndex++;
            input.value = userMsgs[state.historyIndex];
          } else {
            state.historyIndex = -1;
            input.value = state.currentInputTemp;
          }
          _syncInputHeight(input);
          _setCursorAtEnd(input);
        }
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!state.isLoading && state.selectedAgent) sendMessage();
    }
  });

  input.addEventListener('input', () => {
    _syncInputHeight(input);
  });

  btn.addEventListener('click', () => {
    if (state.isLoading) {
      stopMessage();
    } else if (state.selectedAgent) {
      sendMessage();
    }
  });
}

function _syncInputHeight(input) {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
}

function _setCursorAtEnd(input) {
  setTimeout(() => {
    input.selectionStart = input.value.length;
    input.selectionEnd = input.value.length;
  }, 0);
}

async function stopMessage() {
  if (!state.sessionId) return;
  
  const btn = document.getElementById('sendBtn');
  btn.disabled = true; // desabilita temporariamente enquanto cancela
  
  try {
    const res = await fetch(`${API_BASE}/api/chat/stop?session_id=${encodeURIComponent(state.sessionId)}`, {
      method: 'POST'
    });
    if (res.ok) {
      state.isLoading = false;
      updateSendBtn();
      // O backend jÃ¡ retornarÃ¡ um ChatResponse com status erro/cancelado que o sendMessage tratarÃ¡ se o fetch dele ainda estiver pendente, 
      // mas como queremos feedback imediato na UI:
      const thinking = document.querySelector('.thinking-bubble');
      if (thinking) thinking.parentElement.parentElement.remove(); // remove a bolha de thinking
    }
  } catch (e) {
    console.error('Erro ao parar chat:', e);
  } finally {
    btn.disabled = false;
  }
}

async function sendMessage() {
  const input = document.getElementById('messageInput');
  const text = input.value.trim();
  if (!text || !state.selectedAgent) return;

  input.value = '';
  input.style.height = 'auto';
  state.isLoading = true;
  state.historyIndex = -1;
  state.currentInputTemp = '';
  updateSendBtn();

  state.lastUserMessage = text;

  // Adicionar mensagem do usuário
  addMessage('user', text);

  // Thinking indicator animado
  const thinkingEl = addThinkingIndicator();

  // Iniciar stream de eventos SSE
  const eventSource = startEventStream(state.sessionId);

  try {
    const res = await fetch(`${API_BASE}/api/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: state.selectedAgent,
        session_id: state.sessionId,
        message: text,
        attached_files: state.attachedFiles.map(f => f.id)
      }),
    });

    // Limpar anexos imediatamente após o request start
    state.attachedFiles = [];
    renderAttachments();

    const data = await res.json();
    thinkingEl.remove();

    addMessage('assistant', data.response, {
      pendingId: data.pending_action_id,
      riskLevel: data.risk_level,
      status: data.status,
      model: data.model,
      executionSource: data.execution_source,
      latencyMs: data.latency_ms,
      usedLlm: data.used_llm,
      executionResult: data.execution_result
    });

    if (data.pending_action_id) {
      refreshPending();
    }

  } catch (e) {
    thinkingEl.remove();
    if (eventSource) eventSource.close();
    addMessage('assistant', `[ERRO]\nNão foi possível conectar à API: ${e.message}`);
  } finally {
    state.isLoading = false;
    updateSendBtn();
  }
}

function startEventStream(sessionId) {
  if (!sessionId) return null;
  
  const evs = new EventSource(`${API_BASE}/api/chat/events/${sessionId}`);
  
  evs.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      updateEventInUI(data);
    } catch (err) {
      console.error('Erro ao processar evento SSE:', err);
    }
  };
  
  evs.onerror = (e) => {
    console.warn('SSE Disconnected');
    evs.close();
  };
  
  return evs;
}

function updateEventInUI(data) {
  const existing = document.getElementById(data.id);
  if (existing) {
    const statusEl = existing.querySelector('.event-status');
    if (statusEl) {
      statusEl.className = `event-status ${data.status}`;
    }
    // Atualizar no _chatMessages para persistência correta
    const msgObj = _chatMessages.find(m => m.id === data.id);
    if (msgObj) {
      msgObj.status = data.status;
      saveChat(state.selectedAgent, _chatMessages);
    }
  } else {
    // Novo evento
    addMessage('system', data.content, {
      type: 'event',
      id: data.id,
      runId: data.run_id,
      status: data.status
    });
  }
}

function addMessage(role, text, meta = {}) {
  const msgs = document.getElementById('messages');
  const msgId = meta.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  // Remover welcome message se presente
  const welcome = msgs.querySelector('.welcome-message');
  if (welcome) welcome.remove();

  if (meta.type === 'event') {
    renderEventMessage({
      id: meta.id,
      runId: meta.runId,
      status: meta.status || 'active',
      content: text
    });
    // Persistir como evento
    recordMessage('system', null, new Date().toLocaleTimeString(), null, null, null, false, 'event', meta.runId, meta.id);
    // Nota: content será salvo no recordMessage se adaptarmos
    const last = _chatMessages[_chatMessages.length - 1];
    last.content = text; 
    saveChat(state.selectedAgent, _chatMessages);
    return;
  }

  const el = document.createElement('div');
  el.className = `message ${role}`;

  const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const avatarClass = role === 'user' ? 'user-av' : 'agent-av';
  const avatarIcon = role === 'user' ? '\u{1F464}' : '\u{1F916}';

  let formattedContent;
  if (role === 'assistant') {
    // IMPORTANTE: Sincronizar ID antes de formatar para que componentes (tabelas) usem o ID correto
    meta.id = msgId;
    formattedContent = formatResponse(text, meta);
    // Tocar som ao receber resposta do agente
    playAgentSound();
  } else {
    // Usuário: apenas escapar e preservar quebras de linha
    formattedContent = escHtml(text);
  }

  const modelBadge = meta.model ? `<span class="model-badge">${escHtmlBare(meta.model)}</span>` : '';
  const sourceLabel = meta.executionSource ? meta.executionSource.replace(/_/g, ' ').toUpperCase() : '';
  const sourceBadge = meta.executionSource ? `<span class="execution-badge source-${meta.executionSource}">${sourceLabel}</span>` : '';
  const latencyBadge = meta.latencyMs ? `<span class="execution-badge latency-badge">${Math.round(meta.latencyMs)}ms</span>` : '';

  // Botão de copiar em todos os balÃµes
  const copyBtn = `<button class="copy-btn" title="Copiar" onclick="copyBubble(this)">\u{1F4CB}</button>`;

  el.innerHTML = `
    <div class="message-avatar ${avatarClass}">${avatarIcon}</div>
    <div class="message-bubble">
      ${copyBtn}
      ${role === 'assistant' ? `<div class="execution-badges">${sourceBadge}${latencyBadge}${modelBadge}</div>` : ''}
      <div class="message-content" data-message-id="${msgId}">${formattedContent}</div>
      <div class="message-time">${time}</div>
    </div>
  `;

  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;

  // Persistir (incluindo raw content para re-renderização fiel pós-refresh)
  recordMessage(role, formattedContent, time, meta.model, meta.executionSource, meta.latencyMs, meta.usedLlm, 'message', null, msgId, meta.executionResult, text);
  
  // Garantir ID no elemento para referência imediata
  el.id = msgId;

  return el;
}

// ─── Format Response ──────────────────────────────────────────â”€â”€
const _CODE_TOKEN_PREFIX = '<!--CODEBLOCK';
const _CODE_TOKEN_SUFFIX = '-->';

/**
 * Converte uma lista estilo ASCII-table ou separada por vírgula/newline
 * em uma tabela HTML quando detectada dentro de um bloco [RESULTADO].
 */
function _listToTable(text) {
  const lines = text.trim().split(/\n/);
  // Detectar tabela ASCII (linhas com | ou cabeçalho + separador)
  if (lines.length >= 2 && lines[0].includes('|')) {
    const rows = lines.filter(l => !l.match(/^[-\s|+]+$/)); // remover separadores
    if (rows.length < 1) return text;
    const parseRow = l => l.split('|').map(c => c.trim()).filter(c => c !== '');
    const headers = parseRow(rows[0]);
    const bodyRows = rows.slice(1);
    const thead = `<thead><tr>${headers.map(h => `<th>${escHtmlBare(h)}</th>`).join('')}</tr></thead>`;
    const tbody = bodyRows.map(r => {
      const cells = parseRow(r);
      return `<tr>${cells.map(c => `<td>${escHtmlBare(c)}</td>`).join('')}</tr>`;
    }).join('');
    return `<div class="result-table-wrap"><table class="result-table"><thead>${headers.map(h => `<th>${escHtmlBare(h)}</th>`).join('')}</thead><tbody>${tbody}</tbody></table></div>`;
  }

  // Detectar lista simples (itens separados por vírgula ou newline)
  const items = lines.length > 1
    ? lines.map(l => l.replace(/^[-*•]\s*/, '').trim()).filter(Boolean)
    : text.split(',').map(s => s.trim()).filter(Boolean);

  if (items.length >= 2) {
    const rows = items.map(item => `<tr><td>${escHtmlBare(item)}</td></tr>`).join('');
    return `<div class="result-table-wrap"><table class="result-table"><tbody>${rows}</tbody></table></div>`;
  }

  return escHtml(text);
}

/** Escapa HTML sem converter \n em <br> (para uso interno em tabelas). */
function escHtmlBare(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatResponse(text, meta = {}) {
  // 1. Extrair blocos de código com delimitador seguro
  const codeBlocks = [];
  let processed = text.replace(/```(?:sql)?\n?([\s\S]*?)```/g, (_, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre>${escHtml(code.trim())}</pre>`);
    return `${_CODE_TOKEN_PREFIX}${idx}${_CODE_TOKEN_SUFFIX}`;
  });

  // 2. Escapar o texto restante (os tokens são HTML-comments, seguros)
  processed = escHtml(processed);
  // Os tokens ficam como &lt;!--CODEBLOCKn--&gt; após escaping, recuperar:
  processed = processed.replace(/&lt;!--CODEBLOCK(\d+)--&gt;/g, (_, i) => codeBlocks[+i]);

  // 3. Detectar e converter listas dentro de [RESULTADO ...]
  processed = processed.replace(
    /\[RESULTADO[^\]]*\]<br>([\s\S]*?)(?=<div class="block-label"|<div class="pending-badge"|\[(RESUMO|SQL|STATUS|RISCO|ERRO|DETALHE|ID|INFO|PRÓXIMO\sPASSO|AÇÃO\sNECESSÁRIA|RESULTADO)\]|$)/g,
    (fullMatch, content) => {
      // Se tivermos executionResult em meta, usar renderização superior
      if (meta.executionResult && meta.executionResult.rows) {
          return fullMatch.split(content)[0] + _renderTableFromData(meta.executionResult, meta.id);
      }
      
      const rawContent = content.replace(/<br>/g, '\n').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&quot;/g,'"');
      const converted = _listToTable(rawContent);
      return fullMatch.split(content)[0] + converted;
    }
  );

  // 4. Formatar blocos estruturados
  processed = processed.replace(/\[RESUMO\]/g, '<div class="block-label">\u{1F4DD} RESUMO</div>');
  processed = processed.replace(/\[SQL\]/g, '<div class="block-label">\u{1F4BE} SQL</div>');
  processed = processed.replace(/\[RESULTADO\s*(\([^)]*\))?\]/g, '<div class="block-label status-ok">\u{2705} RESULTADO$1</div>');
  processed = processed.replace(/\[STATUS\]<br>Executado/g, '<div class="block-label status-ok">\u{2705} STATUS</div>Executado');
  processed = processed.replace(/\[STATUS\]<br>Falhou/g, '<div class="block-label status-err">\u{274C} STATUS</div>Falhou');
  processed = processed.replace(/\[STATUS\]/g, '<div class="block-label">\u{2139}\u{FE0F} STATUS</div>');
  processed = processed.replace(/\[RISCO\]/g, '<div class="block-label risk">\u{26A0}\u{FE0F} RISCO</div>');
  processed = processed.replace(/\[ERRO\]/g, '<div class="block-label status-err">\u{274C} ERRO</div>');
  processed = processed.replace(/\[DETALHE\]/g, '<div class="block-label">\u{1F4D6} DETALHE</div>');
  processed = processed.replace(/\[PRÓXIMO PASSO\]/g, '<div class="block-label">\u{2192} PRÓXIMO PASSO</div>');
  processed = processed.replace(/\[AÇÃO NECESSÁRIA\]/g, '<div class="block-label pending">\u{23F3} AÇÃO NECESSÁRIA</div>');
  processed = processed.replace(/\[INFO[^\]]*\]/g, '<div class="block-label">\u{2139}\u{FE0F} INFO</div>');
  processed = processed.replace(/\[ID\]/g, '<div class="block-label">\u{1F511} ID</div>');

  // 5. Pending action badge
  if (meta.pendingId) {
    processed += `
      <div class="pending-badge">
        <span>\u{23F3}</span>
        <span class="pending-badge-id">${meta.pendingId}</span>
        <button class="confirm-btn" onclick="quickConfirm('${meta.pendingId}')">Confirmar</button>
        <button class="cancel-btn" onclick="quickCancel('${meta.pendingId}')">Cancelar</button>
      </div>
    `;
  }

  return processed;
}

/**
 * Renderiza uma tabela premium a partir de dados estruturados.
 */
function _renderTableFromData(data, messageId) {
    if (!data || !data.rows || !data.rows.length) return '';
    
    const columns = data.columns || Object.keys(data.rows[0]);
    
    // Cabeçalho
    const thead = `<thead><tr>${columns.map(c => `<th>${escHtmlBare(c)}</th>`).join('')}</tr></thead>`;
    
    // Corpo
    const tbody = `<tbody>${data.rows.map((row, idx) => {
        const cells = columns.map(col => {
            const val = row[col];
            const displayVal = (val === null) ? '<span class="text-muted">NULL</span>' : escHtmlBare(val);
            return `<td>${displayVal}</td>`;
        }).join('');
        return `<tr onclick="showRecordModal('${messageId}', ${idx})" style="cursor:pointer">${cells}</tr>`;
    }).join('')}</tbody>`;
    
    return `
      <div class="result-table-wrap">
        <table class="result-table">
          ${thead}
          ${tbody}
        </table>
      </div>
    `;
}

function showRecordModal(messageId, rowIndex) {
    try {
        // Fallback: se messageId for string 'undefined', tentar pegar do pai mais próximo
        if (!messageId || messageId === 'undefined') {
            const tr = event.currentTarget.closest('tr');
            const content = tr.closest('.message-content');
            messageId = content?.getAttribute('data-message-id');
        }

        const msg = _chatMessages.find(m => m.id === messageId);
        if (!msg) {
            console.error('Mensagem não encontrada:', messageId);
            return;
        }

        // Tentar ambos os nomes de propriedade por segurança (camelCase vs snake_case)
        const result = msg.executionResult || msg.execution_result;
        if (!result || !result.rows || !result.rows[rowIndex]) {
            console.error('Dados de execução não encontrados no objeto da mensagem');
            return;
        }
        
        const record = result.rows[rowIndex];
        const grid = document.getElementById('recordDetailsGrid');
        if (!grid) return;
        
        grid.innerHTML = Object.entries(record).map(([key, val]) => `
            <div class="detail-item-label">${escHtmlBare(key)}</div>
            <div class="detail-item-value">${val === null ? '<span class="text-muted">NULL</span>' : escHtmlBare(val)}</div>
        `).join('');
        
        const modal = document.getElementById('recordDetailModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    } catch (err) {
        console.error('Erro ao abrir modal:', err);
    }
}

function closeRecordModal() {
    document.getElementById('recordDetailModal').style.display = 'none';
}

// ─── Som de resposta do agente ─────────────────────────────────â”€
let _audioCtx = null;
function playAgentSound() {
  try {
    if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const ctx = _audioCtx;
    // Dois tons curtos — som de "ping" suave
    [[880, 0, 0.06], [1100, 0.08, 0.06]].forEach(([freq, delay, dur]) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0, ctx.currentTime + delay);
      gain.gain.linearRampToValueAtTime(0.12, ctx.currentTime + delay + 0.01);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + delay + dur);
      osc.start(ctx.currentTime + delay);
      osc.stop(ctx.currentTime + delay + dur + 0.01);
    });
  } catch (e) { /* contexto de áudio não disponível */ }
}

// ─── Copiar texto do balão ────────────────────────────────────â”€â”€
function copyBubble(btn) {
  const bubble = btn.closest('.message-bubble');
  const content = bubble.querySelector('.message-content');
  // Extrair texto puro (sem HTML)
  const text = content.innerText || content.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = '\u{2705}';
    btn.classList.add('copied');
    setTimeout(() => { btn.innerHTML = orig; btn.classList.remove('copied'); }, 1500);
  }).catch(() => {
    // Fallback para browsers sem clipboard API
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.innerHTML = '\u{2705}';
    setTimeout(() => { btn.innerHTML = '\u{1F4CB}'; }, 1500);
  });
}

// ─── Thinking Indicator ───────────────────────────────────────â”€â”€
function addThinkingIndicator() {
  const msgs = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.id = 'thinking-indicator';
  el.innerHTML = `
    <div class="message-avatar agent-av">\u{1F916}</div>
    <div class="message-bubble">
      <div class="thinking-bubble">
        <div class="thinking-spinner"></div>
        <div class="thinking-text">
          <span class="thinking-label">Gerando plano</span>
          <span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>
        </div>
      </div>
    </div>
  `;
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
  return el;
}

function addTypingIndicator() {
  const msgs = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.innerHTML = `
    <div class="message-avatar agent-av">\u{1F916}</div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
  return el;
}

// ─── Pending Actions ──────────────────────────────────────────â”€
async function refreshPending() {
  if (!state.selectedAgent) return;
  
  try {
    const res = await fetch(`${API_BASE}/api/pending/?agent_id=${state.selectedAgent}`);
    const data = await res.json();
    const pending = data.actions.filter(a => a.status === 'pending');
    state.pendingActions = pending;
    renderPendingList(pending);
  } catch (e) {}
}

function renderPendingList(actions) {
  const list = document.getElementById('pendingList');
  if (!actions.length) {
    list.innerHTML = '<div class="empty-state">Nenhuma ação pendente</div>';
    return;
  }

  list.innerHTML = actions.map(a => `
    <div class="pending-item">
      <div class="pending-item-id">${a.id}</div>
      <div class="pending-item-summary">${escHtml(a.summary)}</div>
      <div class="pending-actions-btns">
        <button class="btn-confirm-small" onclick="quickConfirm('${a.id}')">Confirmar</button>
        <button class="btn-cancel-small" onclick="quickCancel('${a.id}')">Cancelar</button>
      </div>
    </div>
  `).join('');
}

async function quickConfirm(actionId) {
  if (!state.selectedAgent || !state.sessionId) return;
  
  const input = document.getElementById('messageInput');
  input.value = `confirmar ${actionId}`;
  sendMessage();
}

async function quickCancel(actionId) {
  if (!state.selectedAgent || !state.sessionId) return;
  
  const input = document.getElementById('messageInput');
  input.value = `cancelar ${actionId}`;
  sendMessage();
}

// ─── Status Ollama ─────────────────────────────────────────────
async function checkOllama() {
  const el = document.getElementById('ollamaStatus');
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    el.textContent = `✓ ${data.agents} agente(s)`;
    el.classList.add('ok');
  } catch (e) {
    el.textContent = '✗ Offline';
    el.classList.add('error');
  }
}

// ─── UI Helpers ────────────────────────────────────────────────
function enableInput() {
  const input = document.getElementById('messageInput');
  const btn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  input.disabled = false;
  input.placeholder = 'Digite sua mensagem... (Shift+Enter para nova linha)';
  btn.disabled = false;
  if(attachBtn) attachBtn.disabled = false;
  input.focus();
  
  document.getElementById('inputHints').textContent =
    'Dica: "confirmar <id>" ou "cancelar <id>" para pending actions | "/reset" para limpar sessão';
}

function updateSendBtn() {
  const btn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  
  if (state.isLoading) {
    btn.disabled = false;
    btn.classList.add('stopping');
    btn.title = 'Interromper geração';
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor" style="width:14px;height:14px;stroke:none">
        <rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>
      </svg>
    `;
    if(attachBtn) attachBtn.disabled = true;
  } else {
    btn.disabled = !state.selectedAgent;
    btn.classList.remove('stopping');
    btn.title = 'Enviar mensagem';
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    `;
    if(attachBtn) attachBtn.disabled = !state.selectedAgent;
  }
}

function escHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>');
}

function escHtmlBare(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Upload & Attachments ────────────────────────────────────â”€â”€
function setupUpload() {
  const attachBtn = document.getElementById('attachBtn');
  const fileInput = document.getElementById('fileAttachment');
  const inputArea = document.getElementById('inputArea');

  if (!attachBtn || !fileInput || !inputArea) return;

  attachBtn.addEventListener('click', () => {
    if (!state.selectedAgent) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = ''; // reset
  });

  inputArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (state.selectedAgent) inputArea.classList.add('drag-over');
  });

  inputArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    inputArea.classList.remove('drag-over');
  });

  inputArea.addEventListener('drop', (e) => {
    e.preventDefault();
    inputArea.classList.remove('drag-over');
    if (state.selectedAgent && e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  });
}

function removeAttachment(index) {
  state.attachedFiles.splice(index, 1);
  renderAttachments();
}

function renderAttachments() {
  const viewer = document.getElementById('attachmentsViewer');
  if (!viewer) return;
  
  viewer.innerHTML = state.attachedFiles.map((file, i) => `
    <div class="attachment-item">
      \u{1F4C4} ${escHtmlBare(file.name)}
      <button class="remove-btn" onclick="removeAttachment(${i})" title="Remover">×</button>
    </div>
  `).join('');
}

async function handleFiles(files) {
  if (!files || !files.length || !state.selectedAgent) return;

  const validExts = ['.txt', '.md', '.json', '.csv', '.log'];
  const validFiles = Array.from(files).filter(f => {
    const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase();
    if (!validExts.includes(ext)) {
      alert(`Extensão inválida: ${f.name}. Apenas txt, md, json, csv e log.`);
      return false;
    }
    if (f.size > 2 * 1024 * 1024) {
      alert(`Arquivo ${f.name} excede 2MB.`);
      return false;
    }
    return true;
  });

  if (!validFiles.length) return;

  const attachBtn = document.getElementById('attachBtn');
  if(attachBtn) attachBtn.disabled = true;

  const formData = new FormData();
  formData.append('session_id', state.sessionId);
  validFiles.forEach(f => formData.append('files', f));

  try {
    const res = await fetch(`${API_BASE}/api/chat/upload`, {
      method: 'POST',
      body: formData
    });
    
    if (res.ok) {
      const metadata = await res.json();
      state.attachedFiles.push(...metadata);
      renderAttachments();
    } else {
      const err = await res.json();
      alert(`Erro no upload: ${err.detail}`);
    }
  } catch (e) {
    alert(`Erro ao fazer upload: ${e.message}`);
  } finally {
    if(attachBtn) attachBtn.disabled = false;
  }
}

// ─── DB Digest ────────────────────────────────────────────────â”€

async function loadDigestStatus(agentId) {
  const textEl = document.getElementById(`digest-status-text-${agentId}`);
  const aliasesEl = document.getElementById(`digest-aliases-${agentId}`);
  const diagramBtn = document.getElementById(`btn-view-diagram-${agentId}`);
  const diagramHint = document.getElementById(`diagram-hint-${agentId}`);
  if (!textEl) return;

  try {
    const res = await fetch(`${API_BASE}/api/digest/status?agent_id=${encodeURIComponent(agentId)}`);
    if (!res.ok) {
      textEl.textContent = 'Digest não gerado';
      if (diagramBtn) diagramBtn.disabled = true;
      if (diagramHint) diagramHint.textContent = 'Gere o digest antes de visualizar a estrutura';
      return;
    }
    const status = await res.json();

    if (!status.exists) {
      textEl.innerHTML = '<span style="color:var(--text-muted)">Nenhum digest gerado ainda</span>';
      if (diagramBtn) diagramBtn.disabled = true;
      if (diagramHint) diagramHint.textContent = 'Gere o digest antes de visualizar a estrutura';
      if (aliasesEl) aliasesEl.textContent = '';
      return;
    }

    const dt = new Date(status.generated_at).toLocaleString('pt-BR');
    textEl.innerHTML =
      `<span style="color:var(--success)">✓</span> ` +
      `${status.tables} tabelas · ${status.views} views · ${status.triggers} triggers` +
      `<br><span style="font-size:10px;color:var(--text-muted)">Gerado em ${dt}</span>`;
    if (diagramBtn) diagramBtn.disabled = false;
    if (diagramHint) diagramHint.textContent = 'Abre o diagrama estrutural em nova aba';

    // Mostrar aliases se existirem
    if (aliasesEl) {
      try {
        const aRes = await fetch(`${API_BASE}/api/aliases?agent_id=${encodeURIComponent(agentId)}`);
        if (aRes.ok) {
          const aliasData = await aRes.json();
          const autoCount = Object.keys(aliasData.aliases || {}).length;
          const manualCount = Object.keys(aliasData.manual_aliases || {}).length;
          const sample = Object.entries(aliasData.aliases || {}).slice(0, 4)
            .map(([k]) => `<code style="background:var(--bg-hover);padding:1px 4px;border-radius:3px;">${escHtmlBare(k)}</code>`)
            .join(' ');
          aliasesEl.innerHTML =
            `${autoCount} alias(es) automáticos${manualCount ? ` · ${manualCount} manuais` : ''}: ${sample}` +
            (autoCount > 4 ? ` <span style="color:var(--text-muted)">+${autoCount - 4} mais</span>` : '');
        }
      } catch (_) { /* silencioso */ }
    }
  } catch (e) {
    textEl.textContent = 'Erro ao verificar digest';
    if (diagramBtn) diagramBtn.disabled = true;
    if (diagramHint) diagramHint.textContent = 'Não foi possível validar o digest para o diagrama';
  }
}

async function generateDigest(agentId) {
  const btn = document.getElementById(`btn-generate-digest-${agentId}`);
  const textEl = document.getElementById(`digest-status-text-${agentId}`);
  if (!btn || !textEl) return;

  btn.disabled = true;
  btn.textContent = 'â³ Gerando...';
  textEl.innerHTML = '<span style="color:var(--text-muted)">Conectando ao banco e coletando schema...</span>';

  try {
    const res = await fetch(
      `${API_BASE}/api/digest/generate?agent_id=${encodeURIComponent(agentId)}`,
      { method: 'POST' }
    );
    if (!res.ok) {
      const err = await res.json();
      textEl.innerHTML = `<span style="color:var(--danger)">✗ ${escHtmlBare(err.detail || 'Erro desconhecido')}</span>`;
      return;
    }
    const digest = await res.json();
    const dt = new Date(digest.generated_at).toLocaleString('pt-BR');
    textEl.innerHTML =
      `<span style="color:var(--success)">✓ Atualizado!</span> ` +
      `${digest.summary.tables} tabelas · ${digest.summary.views} views · ${digest.summary.triggers} triggers` +
      `<br><span style="font-size:10px;color:var(--text-muted)">${dt}</span>`;

    // Recarregar aliases no painel
    await loadDigestStatus(agentId);

  } catch (e) {
    textEl.innerHTML = `<span style="color:var(--danger)">✗ Erro de rede</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '\u{1F50D} Gerar Digest';
  }
}

function viewDigest(agentId) {
  window.open(
    `${API_BASE}/api/digest?agent_id=${encodeURIComponent(agentId)}`,
    '_blank'
  );
}

async function openDiagram(agentId) {
  const btn = document.getElementById(`btn-view-diagram-${agentId}`);
  const hint = document.getElementById(`diagram-hint-${agentId}`);

  try {
    if (btn) btn.disabled = true;
    const res = await fetch(`${API_BASE}/api/diagram/${encodeURIComponent(agentId)}/status`);
    if (!res.ok) {
      const errDetail = await res.json().then(j => j.detail).catch(() => null);
      const msg = errDetail || `Erro ${res.status} ao verificar status do diagrama. Tente recarregar a página (Ctrl+Shift+R) e reabrir o diagrama.`;
      if (hint) hint.textContent = 'Não foi possível validar o digest para o diagrama';
      alert(msg);
      return;
    }

    const status = await res.json();
    if (!status.exists) {
      if (hint) hint.textContent = 'Gere o digest antes de visualizar a estrutura';
      alert('Digest não encontrado. Gere o digest antes de visualizar a estrutura.');
      return;
    }
    if (!status.valid) {
      if (hint) hint.textContent = status.message || 'Digest inválido para visualização';
      alert(status.message || 'Digest inválido. Gere o digest novamente antes de visualizar a estrutura.');
      return;
    }

    if (hint) hint.textContent = 'Abrindo diagrama em nova aba...';
    window.open(`${API_BASE}/diagram/${encodeURIComponent(agentId)}`, '_blank', 'noopener');
  } catch (err) {
    if (hint) hint.textContent = 'Erro ao abrir visualização estrutural';
    alert('Erro de rede ao abrir visualização estrutural. Verifique se o servidor está rodando.');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ─── Autocomplete @ Aliases ────────────────────────────────────
/**
 * Detecta tokens @... no textarea e abre um dropdown de sugestões
 * buscando em tempo real no endpoint GET /api/aliases/suggest.
 *
 * Features:
 *  - Detecta `@` seguido de zero ou mais caracteres (palavra)
 *  - Busca sugestões filtradas pelo prefixo atual
 *  - Navegação por teclado (â†‘â†“ Enter Escape)
 *  - Seleção por mouse (click)
 *  - Substitui apenas o token atual no textarea (preserva o restante)
 *  - Depende do agente selecionado (state.selectedAgent)
 *  - NÃ£o faz nada se não houver agente ou token inválido
 */

const _ac = {
  popup: null,        // elemento DOM do dropdown
  items: [],          // lista de sugestões atual
  selected: -1,       // índice de item selecionado (-1 = nenhum)
  tokenStart: -1,     // posição inicial do token @... no textarea
  tokenEnd: -1,       // posição final do token @...
  debounceTimer: null,
};

function setupAutocomplete() {
  const input = document.getElementById('messageInput');
  if (!input) return;

  // Criar popup e ancorar ao DOM
  const popup = document.createElement('div');
  popup.id = 'alias-autocomplete-popup';
  popup.className = 'autocomplete-popup';
  popup.setAttribute('role', 'listbox');
  popup.setAttribute('aria-label', 'Sugestões de aliases');
  // Inserir junto ao formulário de entrada
  input.parentElement.appendChild(popup);
  _ac.popup = popup;

  // Detectar @token enquanto o usuário digita
  input.addEventListener('input', _acOnInput);

  // Navegação por teclado
  input.addEventListener('keydown', _acOnKeydown);

  // Fechar ao clicar fora
  document.addEventListener('mousedown', (e) => {
    if (!popup.contains(e.target) && e.target !== input) {
      _acClose();
    }
  });
}

function _acOnInput() {
  clearTimeout(_ac.debounceTimer);
  _ac.debounceTimer = setTimeout(_acDetectToken, 120);
}

function _acOnKeydown(e) {
  if (!_ac.popup || !_ac.popup.classList.contains('visible')) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    _acMove(1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    _acMove(-1);
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    if (_ac.selected >= 0 && _ac.items[_ac.selected]) {
      e.preventDefault();
      _acSelect(_ac.items[_ac.selected]);
    }
  } else if (e.key === 'Escape') {
    _acClose();
  }
}

async function _acDetectToken() {
  const input = document.getElementById('messageInput');
  if (!input || !state.selectedAgent) { _acClose(); return; }

  const text = input.value;
  const pos = input.selectionStart;

  // Encontrar início do token — percorrer para trás até espaço ou início
  let start = pos;
  while (start > 0 && text[start - 1] !== ' ' && text[start - 1] !== '\n') {
    start--;
  }

  const token = text.slice(start, pos); // ex: "@Di" ou "@Dicas"

  if (!token.startsWith('@')) {
    _acClose();
    return;
  }

  _ac.tokenStart = start;
  _ac.tokenEnd = pos;

  // Não buscar se token for apenas "@" com muitos caracteres sem letras
  const query = token; // ex: "@Di"

  try {
    const url = `${API_BASE}/api/aliases/suggest?agent_id=${encodeURIComponent(state.selectedAgent)}&q=${encodeURIComponent(query)}`;
    const res = await fetch(url);
    if (!res.ok) { _acClose(); return; }
    const suggestions = await res.json();

    if (!suggestions.length) {
      _acClose();
      return;
    }

    _acRender(suggestions, input);
  } catch (e) {
    _acClose();
  }
}

function _acRender(items, input) {
  const popup = _ac.popup;
  if (!popup) return;

  _ac.items = items;
  _ac.selected = -1;

  popup.innerHTML = items.map((item, i) => `
    <div
      class="autocomplete-item"
      role="option"
      data-index="${i}"
      onmousedown="event.preventDefault(); _acSelect(_ac.items[${i}])"
    >
      <span class="autocomplete-alias">${escHtmlBare(item.alias)}</span>
      <span class="autocomplete-table">${escHtmlBare(item.table)}</span>
      <span class="autocomplete-source ${item.source === 'manual' ? 'manual' : ''}">${item.source}</span>
    </div>
  `).join('');

  popup.classList.add('visible');
}

function _acMove(delta) {
  const items = _ac.popup.querySelectorAll('.autocomplete-item');
  if (!items.length) return;

  // Remover seleção atual
  if (_ac.selected >= 0 && items[_ac.selected]) {
    items[_ac.selected].classList.remove('selected');
  }

  _ac.selected = Math.max(0, Math.min(items.length - 1, _ac.selected + delta));
  items[_ac.selected].classList.add('selected');
  items[_ac.selected].scrollIntoView({ block: 'nearest' });
}

function _acSelect(item) {
  const input = document.getElementById('messageInput');
  if (!input || !item) return;

  const text = input.value;
  // Substituir apenas o token @... pelo alias selecionado + espaço
  const before = text.slice(0, _ac.tokenStart);
  const after = text.slice(_ac.tokenEnd);
  const replacement = item.alias + (after.startsWith(' ') ? '' : ' ');
  input.value = before + replacement + after;

  // Reposicionar cursor após o alias inserido
  const newPos = _ac.tokenStart + replacement.length;
  input.setSelectionRange(newPos, newPos);
  input.focus();

  _acClose();
}

function _acClose() {
  if (_ac.popup) {
    _ac.popup.classList.remove('visible');
    _ac.popup.innerHTML = '';
  }
  _ac.items = [];
  _ac.selected = -1;
  _ac.tokenStart = -1;
  _ac.tokenEnd = -1;
}


