/**
 * workspace.js — View operacional do chat (Etapa 2)
 * Porta fiel da lógica do chat.js/Alpine para Vanilla ESM puro.
 * Gerencia: agentes, chat, steps, skills, config.
 *
 * @param {HTMLElement} container — #main-content
 * @returns {Function} teardown — limpa listeners e timers
 */

import { api }           from '../api.js';
import { store }         from '../store.js';
import { openModal, confirmModal } from '../components/modal.js';
import { openRightPanel, closeRightPanel } from '../components/panel.js';
import { toast }         from '../utils/dom.js';

// ── Estado local desta view ──────────────────────────────────────
const state = {
  sessionId: '',
  agents: [],
  activeAgent: 'main',
  currentAgentName: 'Principal',
  messagesByAgent: {},
  loadedHistoryByAgent: {},
  thinkingAgents: {},
  thinking: false,
  connected: true,
  copiedId: null,
  skills: [],
  assignedSkillsCurrentAgent: [],
  selectedSkillName: '',
  chatFiles: [],
  cfg: {
    ollamaProvider: 'ollama',
    ollamaBaseUrl: '',
    ollamaModel: '',
    telegramBotToken: '',
    telegramAllowedUser: '',
    enableTelegram: true,
    enableWebChat: true,
    showThoughtFlow: true,
    typewriterEffect: true,
  },
  allModels: [], // Armazena cache global de modelos para o picker
};

// ── Refs para elementos DOM ──────────────────────────────────────
let els = {};

// ── Utils temporais ──────────────────────────────────────────────
function nowTime() {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function uid() {
  return Math.random().toString(36).slice(2);
}

// ── Renderização do markdown ────────────────────────────────────
function renderMd(text) {
  if (!text) return '';
  try { return window.marked.parse(text); } catch (_) { return text; }
}

// ═══════════════════════════════════════════════════════════════
//  RENDER PRINCIPAL
// ═══════════════════════════════════════════════════════════════
export async function renderWorkspacePage(container) {
  container.innerHTML = buildWorkspaceHTML();
  cacheEls(container);
  bindEvents();

  // Bootstrap
  await loadConfig();
  await loadAgents();
  await loadSkills();

  // Abrir config via evento do botão Settings da sidebar
  document.addEventListener('ws:open-settings', openConfigPanel);

  // Retorna teardown
  return teardown;
}

function teardown() {
  document.removeEventListener('ws:open-settings', openConfigPanel);
  state.connected = false;
}

// ═══════════════════════════════════════════════════════════════
//  HTML DA VIEW
// ═══════════════════════════════════════════════════════════════
function buildWorkspaceHTML() {
  return `
    <div id="workspace-view">

      <!-- Sub-sidebar: lista de agentes -->
      <div class="ws-agents-list">
        <div class="ws-agents-header">Agentes</div>
        <div class="ws-agents-scroll" id="ws-agent-list"></div>
        <div class="ws-agents-footer">
          <button class="btn-new-agent" id="btn-new-agent">+ Novo agente</button>
        </div>
      </div>

      <!-- Coluna central: chat -->
      <div class="col-chat">
        <header class="chat-header">
          <div class="chat-header-info">
            <div class="agent-avatar-lg" id="ws-agent-avatar">🧠</div>
            <div style="position:relative;">
              <div class="agent-name" id="ws-agent-name" style="cursor:pointer;" onclick="toggleModelPicker()">Principal</div>
              <div class="agent-status">
                <span class="status-dot active" id="ws-status-dot"></span>
                <span id="ws-status-txt">Online</span>
              </div>
              
              <!-- MODEL PICKER POPOVER -->
              <div id="model-picker-popover" class="model-picker-popover" style="display:none;">
                <div class="popover-header">Selecionar Modelo</div>
                <div class="popover-scroll" id="model-picker-list">
                  <div style="padding:10px;color:var(--muted);font-size:11px;">Carregando modelos...</div>
                </div>
              </div>
            </div>
          </div>
          <div class="header-commands">
            <button class="cmd-btn" id="btn-reset">↺ Reset</button>
            <button class="cmd-btn danger" id="btn-stop">⏹ Stop</button>
            <button class="cmd-btn" id="btn-skills">🧠 Skills</button>
            <button class="cmd-btn" id="btn-agent-details" title="Detalhes do Agente" style="width:34px;padding:0;display:inline-flex;align-items:center;justify-content:center;">
              <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="15" width="15">
                <line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line>
                <line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line>
                <line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line>
                <line x1="17" y1="16" x2="23" y2="16"></line>
              </svg>
            </button>
            <button class="cmd-btn" id="btn-config" style="font-size:16px;width:34px;padding:0;" title="Configurações">⚙</button>
          </div>
        </header>

        <section class="messages" id="ws-messages">
          <div class="chat-empty-state" id="ws-empty-state">
            <div class="chat-empty-icon">💬</div>
            <div>Inicie uma conversa com <strong id="ws-empty-agent-name">Principal</strong></div>
            <div class="chat-empty-hint">Comandos: <code>/reset</code> · <code>/stop</code></div>
          </div>
        </section>

        <form class="composer" id="ws-composer">
          <input type="file" multiple id="ws-file-input" style="display:none;" accept=".md,.txt,.json,.csv" />
          <div style="display:flex;flex-direction:column;flex:1;gap:4px;">
            <div id="ws-file-chips" style="display:flex;gap:6px;flex-wrap:wrap;padding:0 4px 4px;"></div>
            <textarea id="ws-input" placeholder="Digite sua mensagem... (Enter envia | /reset /stop)" rows="1"></textarea>
          </div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
            <button type="button" id="btn-attach" style="background:none;border:none;cursor:pointer;padding:4px;border-radius:8px;font-size:20px;color:var(--muted);" title="Anexar">📎</button>
            <button type="submit" class="btn-send" id="btn-send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </form>
      </div>

    </div>
  `;
}

// ═══════════════════════════════════════════════════════════════
//  CACHE DE ELEMENTOS
// ═══════════════════════════════════════════════════════════════
function cacheEls(container) {
  els = {
    agentList:     container.querySelector('#ws-agent-list'),
    agentAvatar:   container.querySelector('#ws-agent-avatar'),
    agentName:     container.querySelector('#ws-agent-name'),
    statusDot:     container.querySelector('#ws-status-dot'),
    messages:      container.querySelector('#ws-messages'),
    emptyState:    container.querySelector('#ws-empty-state'),
    emptyAgentName:container.querySelector('#ws-empty-agent-name'),
    composer:      container.querySelector('#ws-composer'),
    input:         container.querySelector('#ws-input'),
    fileInput:     container.querySelector('#ws-file-input'),
    fileChips:     container.querySelector('#ws-file-chips'),
    sendBtn:       container.querySelector('#btn-send'),
    btnNewAgent:   container.querySelector('#btn-new-agent'),
    btnReset:      container.querySelector('#btn-reset'),
    btnStop:       container.querySelector('#btn-stop'),
    btnSkills:     container.querySelector('#btn-skills'),
    btnDetails:    container.querySelector('#btn-agent-details'),
    btnConfig:     container.querySelector('#btn-config'),
    btnAttach:     container.querySelector('#btn-attach'),
  };
}

// ═══════════════════════════════════════════════════════════════
//  BIND DE EVENTOS
// ═══════════════════════════════════════════════════════════════
function bindEvents() {
  // Composer
  els.composer.addEventListener('submit', onSend);
  els.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
      e.preventDefault();
      onSend(e);
    }
  });
  els.input.addEventListener('input', autoResize);

  // Anexo
  els.btnAttach.addEventListener('click', () => els.fileInput.click());
  els.fileInput.addEventListener('change', (e) => {
    state.chatFiles.push(...Array.from(e.target.files));
    renderFileChips();
  });

  // Comandos do header
  els.btnReset.addEventListener('click', () => sendCommand('/reset'));
  els.btnStop.addEventListener('click', () => sendCommand('/stop'));
  els.btnSkills.addEventListener('click', openSkillsModal);
  els.btnConfig.addEventListener('click', openConfigPanel);
  els.btnNewAgent.addEventListener('click', openNewAgentModal);
  
  // Detalhes do Agente via Botão de Configuração específico no cabeçalho
  if (els.btnDetails) {
    els.btnDetails.onclick = openCurrentAgentDetailsPanel;
  }
}

// ═══════════════════════════════════════════════════════════════
//  AGENTES
// ═══════════════════════════════════════════════════════════════
async function loadAgents() {
  try {
    const d = await api.getAgents();
    state.agents = d.agents || [{ id: 'main', name: 'Principal', description: '' }];
  } catch (_) {
    state.agents = [{ id: 'main', name: 'Principal', description: '' }];
  }
  state.agents.forEach(ag => {
    if (!state.messagesByAgent[ag.id]) state.messagesByAgent[ag.id] = [];
  });
  renderAgentList();
  updateCurrentAgent();
  await loadChatHistory(state.activeAgent);
}

function renderAgentList() {
  if (!els.agentList) return;
  els.agentList.innerHTML = '';
  for (const ag of state.agents) {
    const item = document.createElement('button');
    item.className = `agent-item${state.activeAgent === ag.id ? ' active' : ''}`;
    item.dataset.agentId = ag.id;
    item.innerHTML = `
      <div class="agent-item-avatar">${ag.id === 'main' ? '🧠' : '🤖'}</div>
      <div class="agent-item-info">
        <div class="agent-item-name">${ag.name}</div>
        <div class="agent-item-sub">${ag.id === 'main' ? 'Principal' : 'Especialista'}</div>
      </div>
      ${ag.id !== 'main' ? `<button class="agent-delete-btn" data-delete="${ag.id}" title="Excluir">✕</button>` : ''}
    `;

    item.addEventListener('click', () => switchAgent(ag.id));

    const delBtn = item.querySelector('.agent-delete-btn');
    if (delBtn) {
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteAgent(ag.id);
      });
    }

    els.agentList.appendChild(item);
  }
}

function switchAgent(id) {
  state.activeAgent = id;
  state.thinking = !!state.thinkingAgents[id];
  updateCurrentAgent();
  renderAgentList();
  loadChatHistory(id);
}

function updateCurrentAgent() {
  const ag = state.agents.find(a => a.id === state.activeAgent);
  state.currentAgentName = ag ? ag.name : 'Agent';

  if (els.agentName) els.agentName.textContent = state.currentAgentName;
  if (els.agentAvatar) els.agentAvatar.textContent = state.activeAgent === 'main' ? '🧠' : '🤖';
  if (els.emptyAgentName) els.emptyAgentName.textContent = state.currentAgentName;

  renderMessages();
}

async function deleteAgent(agentId) {
  if (agentId === 'main') return;
  confirmModal({
    title: 'Excluir Agente',
    message: `Excluir o agente <strong>${agentId}</strong>? Esta ação não pode ser desfeita.`,
    confirmLabel: 'Excluir',
    danger: true,
    onConfirm: async () => {
      try {
        await fetch(`/api/agents/${agentId}`, { method: 'DELETE' });
      } catch (_) {}
      state.agents = state.agents.filter(a => a.id !== agentId);
      delete state.messagesByAgent[agentId];
      if (state.activeAgent === agentId) switchAgent('main');
      else renderAgentList();
    },
  });
}

// ═══════════════════════════════════════════════════════════════
//  HISTÓRICO + MENSAGENS
// ═══════════════════════════════════════════════════════════════
async function loadChatHistory(agentId) {
  if (state.loadedHistoryByAgent[agentId]) {
    renderMessages();
    return;
  }
  try {
    const sessionId = getSessionId();
    const d = await fetch(`/api/chat/history/${sessionId}/${agentId}`).then(r => r.json());
    if (d.ok && d.messages) {
      const serverMsgs = d.messages.map(m => ({
        id: uid(), role: m.role, text: m.content,
        time: new Date(m.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        isDone: true, agentName: m.agentName, modelUsed: m.modelUsed || null,
      }));
      const local = state.messagesByAgent[agentId] || [];
      const merged = [...serverMsgs];
      for (const msg of local) {
        const exists = merged.some(s => s.role === msg.role && s.text === msg.text);
        if (!exists) merged.push(msg);
      }
      state.messagesByAgent[agentId] = merged;
      state.loadedHistoryByAgent[agentId] = true;
    }
  } catch (_) {}
  if (agentId === state.activeAgent) renderMessages();
}

function pushMessage(agentId, role, text, agentName, modelUsed) {
  if (!state.messagesByAgent[agentId]) state.messagesByAgent[agentId] = [];
  state.messagesByAgent[agentId].push({
    id: uid(), role, text, time: nowTime(), isDone: true,
    agentName: agentName || state.currentAgentName, modelUsed: modelUsed || null,
  });
  if (agentId === state.activeAgent) {
    renderMessages();
  }
}

function pushStep(agentId, stepId, title, status = 'loading', text = '') {
  if (!state.messagesByAgent[agentId]) state.messagesByAgent[agentId] = [];
  const msg = {
    id: stepId, role: 'step', text, time: nowTime(), isDone: false,
    open: false, stepInfo: { status, title },
  };
  state.messagesByAgent[agentId].push(msg);
  if (agentId === state.activeAgent) renderMessages();
  return msg;
}

function updateStep(agentId, stepId, title, status, text) {
  const msgs = state.messagesByAgent[agentId] || [];
  const msg = msgs.find(m => m.id === stepId);
  if (msg) {
    msg.stepInfo = { status, title };
    msg.text = text;
    msg.isDone = true;
  }
  if (agentId === state.activeAgent) renderMessages();
}

// ── Render das mensagens no DOM ──────────────────────────────────
function renderMessages() {
  if (!els.messages) return;
  const msgs = state.messagesByAgent[state.activeAgent] || [];

  if (msgs.length === 0) {
    if (els.emptyState && !els.messages.contains(els.emptyState)) {
      // Limpa e mostra empty state
      els.messages.innerHTML = '';
      els.messages.appendChild(els.emptyState);
    }
    return;
  }

  // Remove empty state se existir
  if (els.emptyState && els.messages.contains(els.emptyState)) {
    els.emptyState.remove();
  }

  // Re-renderiza tudo (simples mas funcional para MVP)
  els.messages.innerHTML = msgs.map(msg => buildMessageHTML(msg)).join('');

  // Typing indicator
  if (state.thinkingAgents[state.activeAgent]) {
    els.messages.insertAdjacentHTML('beforeend', `
      <div class="msg-row assistant">
        <div class="avatar-sm">${state.activeAgent === 'main' ? '🧠' : '🤖'}</div>
        <div class="bubble assistant typing">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
      </div>
    `);
  }

  // Bind de cliques nos steps
  els.messages.querySelectorAll('.step-title').forEach(btn => {
    btn.addEventListener('click', () => {
      const content = btn.nextElementSibling?.nextElementSibling;
      if (content) content.style.display = content.style.display === 'none' ? 'block' : 'none';
    });
  });

  // Bind de cópia
  els.messages.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.dataset.text;
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = '⎘'; }, 2000);
      });
    });
  });

  scrollToBottom();
}

function buildMessageHTML(msg) {
  if (msg.role === 'step') return buildStepHTML(msg);

  const isUser = msg.role === 'user';
  const isSystem = msg.role === 'system';
  const avatar = isUser
    ? `<div class="avatar-sm user">V</div>`
    : isSystem
      ? `<div class="avatar-sm sys">⚙</div>`
      : `<div class="avatar-sm">${msg.agentName === 'Principal' ? '🧠' : '🤖'}</div>`;

  const content = isUser || isSystem
    ? `<div class="bubble-content">${escapeHtml(msg.text)}</div>`
    : `<div class="assistant-final markdown">${renderMd(msg.text)}</div>`;

  const meta = !isSystem ? `
    <div class="bubble-footer">
      <div class="bubble-meta">
        ${msg.modelUsed ? `<span>[${msg.modelUsed}]</span>` : ''}
        <span>${msg.time}</span>
      </div>
      <button class="copy-btn" data-text="${escapeAttr(msg.text)}" title="Copiar">⎘</button>
    </div>
  ` : '';

  const bubbleClass = isUser ? 'user' : isSystem ? 'system' : 'assistant';

  return `
    <div class="msg-row ${msg.role}">
      ${!isUser ? avatar : ''}
      <div class="bubble ${bubbleClass}">
        ${content}
        ${meta}
      </div>
      ${isUser ? avatar : ''}
    </div>
  `;
}

function buildStepHTML(msg) {
  const isLoading = msg.stepInfo.status === 'loading';
  return `
    <div class="msg-row system" style="max-width:90%;">
      <div class="avatar-sm sys">⚙</div>
      <div class="bubble step-bubble">
        <div class="assistant-step">
          <div class="step-title" style="cursor:pointer;">
            <span>${msg.stepInfo.title}</span>
            ${!isLoading ? `<span style="margin-left:auto;font-size:10px;color:var(--muted)">▶</span>` : ''}
          </div>
          ${isLoading ? `<div class="step-loading"><span class="spinner"></span> Carregando...</div>` : ''}
          <div class="step-content markdown" style="display:none">${renderMd(msg.text)}</div>
        </div>
      </div>
    </div>
  `;
}

function scrollToBottom() {
  if (els.messages) {
    requestAnimationFrame(() => { els.messages.scrollTop = els.messages.scrollHeight; });
  }
}

// ═══════════════════════════════════════════════════════════════
//  ENVIO DE MENSAGEM
// ═══════════════════════════════════════════════════════════════
async function onSend(e) {
  e?.preventDefault();
  const text = els.input.value.trim();
  if (!text && state.chatFiles.length === 0) return;
  if (state.thinking) return;

  els.input.value = '';
  els.input.style.height = 'auto';

  if (text.startsWith('/')) {
    sendCommand(text);
    state.chatFiles = [];
    renderFileChips();
    return;
  }

  state.thinking = true;
  setInputEnabled(false);

  const agentId = state.activeAgent;
  pushMessage(agentId, 'user', text, 'Você', null);
  state.thinkingAgents[agentId] = true;

  const sessionId = getSessionId();
  const payload = { message: text, conversation_id: sessionId, agent_id: agentId };

  // Step 1: Planner
  let plannerStepId = null;
  if (state.cfg.showThoughtFlow) {
    plannerStepId = uid();
    pushStep(agentId, plannerStepId, '🧠 PlannerAgent analisando o contexto...');
  }

  try {
    const data = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(async r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      return r.json();
    });

    if (!state.cfg.showThoughtFlow) {
      pushMessage(agentId, 'assistant', data.response || 'Sem resposta.', state.currentAgentName, data.model_used);
      finishThinking(agentId);
      return;
    }

    // Preenche Planner
    if (plannerStepId) {
      updateStep(agentId, plannerStepId, '🧠 Planejamento concluído', 'done', data.planner || 'Sem plano gerado.');
    }

    // Step 2: Specialist
    const specId = uid();
    pushStep(agentId, specId, `⚙️ ${data.selected_specialist || 'SpecialistAgent'} elaborando resposta...`);

    await delay(600);
    updateStep(agentId, specId, `⚙️ ${data.selected_specialist || 'SpecialistAgent'} finalizou a análise`, 'done', data.specialist || '');

    // Step 3: Reviewer
    const revId = uid();
    pushStep(agentId, revId, '🔍 ReviewerAgent processando revisão...');

    await delay(600);
    updateStep(agentId, revId, '🔍 Revisão concluída', 'done', data.reviewer || '');

    // Resposta final
    await delay(400);
    pushMessage(agentId, 'assistant', data.response || 'Sem resposta.', state.currentAgentName, data.model_used);
    finishThinking(agentId);

  } catch (err) {
    console.error('[Workspace] Erro no chat:', err);
    if (plannerStepId) {
      updateStep(agentId, plannerStepId, '🧠 Erro no Planner', 'error', `Erro: ${err.message}`);
    }
    pushMessage(agentId, 'assistant', 'Erro ao processar a resposta do servidor.', state.currentAgentName);
    finishThinking(agentId);
  }
}

function finishThinking(agentId) {
  state.thinkingAgents[agentId] = false;
  state.thinking = false;
  setInputEnabled(true);
  renderMessages();
}

function setInputEnabled(enabled) {
  if (els.input) els.input.disabled = !enabled;
  if (els.sendBtn) els.sendBtn.disabled = !enabled;
}

async function sendCommand(cmd) {
  if (cmd === '/stop' || cmd === '/reset') {
    state.thinking = false;
    state.thinkingAgents[state.activeAgent] = false;
  }
  const agentId = state.activeAgent;
  try {
    const data = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: cmd, conversation_id: getSessionId(), agent_id: agentId }),
    }).then(r => r.json());

    const text = data.response || 'Erro ao executar comando.';
    pushMessage(agentId, 'system', text, 'Sistema');

    if (cmd === '/reset') {
      state.messagesByAgent[agentId] = [];
      state.loadedHistoryByAgent[agentId] = false;
      state.thinking = false;
      state.thinkingAgents[agentId] = false;
      setInputEnabled(true);
      renderMessages();
    }
  } catch (_) {
    pushMessage(agentId, 'system', 'Erro ao executar comando.', 'Sistema');
  }
}

// ═══════════════════════════════════════════════════════════════
//  CONFIG
// ═══════════════════════════════════════════════════════════════
async function loadConfig() {
  try {
    const d = await api.getConfig();
    if (d.ok) {
      Object.assign(state.cfg, d.config);
    }
  } catch (_) {}
}

function openConfigPanel() {
  const content = buildConfigPanelHTML();
  const container = document.createElement('div');
  container.className = 'ws-right-panel';
  container.innerHTML = `
    <div class="ws-panel-header">
      <span>⚙ Configurações</span>
      <button id="ws-cfg-close" style="background:none;border:none;cursor:pointer;color:var(--muted);">✕</button>
    </div>
    <div class="ws-panel-body" id="ws-cfg-body">
      ${content}
    </div>
  `;

  openRightPanel(container);

  container.querySelector('#ws-cfg-close').addEventListener('click', closeRightPanel);
  container.querySelector('#ws-cfg-save').addEventListener('click', saveConfig);

  // Toggle listeners
  container.querySelectorAll('input[type="checkbox"][data-cfg]').forEach(cb => {
    cb.addEventListener('change', () => { state.cfg[cb.dataset.cfg] = cb.checked; });
  });
  container.querySelectorAll('input[data-cfg], select[data-cfg]').forEach(inp => {
    inp.addEventListener('input', () => { state.cfg[inp.dataset.cfg] = inp.value; });
  });
}

function buildConfigPanelHTML() {
  const c = state.cfg;
  return `
    <form class="config-form" id="ws-cfg-form">
      <div class="config-section-title">AI Engine</div>
      <div class="config-field">
        <label>Provedor LLM</label>
        <select class="input-cfg" data-cfg="ollamaProvider">
          <option value="ollama" ${c.ollamaProvider === 'ollama' ? 'selected' : ''}>Ollama (Local)</option>
        </select>
      </div>
      <div class="config-field">
        <label>Ollama Base URL</label>
        <input class="input-cfg" data-cfg="ollamaBaseUrl" value="${c.ollamaBaseUrl || ''}" placeholder="http://host.docker.internal:11434" />
      </div>
      <div class="config-field">
        <label>Modelo</label>
        <input class="input-cfg" data-cfg="ollamaModel" value="${c.ollamaModel || ''}" placeholder="llama3.1:8b" />
      </div>
      <div class="config-section-title" style="margin-top:18px">Telegram</div>
      <div class="config-field">
        <label>Bot Token</label>
        <input class="input-cfg" type="password" data-cfg="telegramBotToken" value="${c.telegramBotToken || ''}" placeholder="Bot Token" />
      </div>
      <div class="config-field">
        <label>User ID Permitido</label>
        <input class="input-cfg" data-cfg="telegramAllowedUser" value="${c.telegramAllowedUser || ''}" placeholder="123456789" />
      </div>
      <div class="config-section-title" style="margin-top:18px">Interface</div>
      <div class="config-toggle">
        <span>Telegram ativo</span>
        <label class="toggle-switch"><input type="checkbox" data-cfg="enableTelegram" ${c.enableTelegram ? 'checked' : ''}><span class="toggle-track"></span></label>
      </div>
      <div class="config-toggle">
        <span>Fluxo de Pensamento</span>
        <label class="toggle-switch"><input type="checkbox" data-cfg="showThoughtFlow" ${c.showThoughtFlow ? 'checked' : ''}><span class="toggle-track"></span></label>
      </div>
      <button type="button" class="btn-save" id="ws-cfg-save" style="margin-top:12px;">Salvar Configurações</button>
      <div class="config-note">Alterações de token Telegram requerem reinicio do container.</div>
    </form>
  `;
}

async function saveConfig() {
  const btn = document.getElementById('ws-cfg-save');
  if (btn) btn.textContent = 'Salvando...';
  try {
    await api.updateConfig(state.cfg);
    toast('Configurações salvas!', 'success');
  } catch (_) {
    toast('Erro ao salvar configurações', 'danger');
  } finally {
    if (btn) btn.textContent = 'Salvar Configurações';
  }
}

// ═══════════════════════════════════════════════════════════════
//  SKILLS
// ═══════════════════════════════════════════════════════════════
async function loadSkills() {
  try {
    const d = await api.getSkills();
    state.skills = d.skills || [];
  } catch (_) { state.skills = []; }
}

async function loadAssignedSkills() {
  try {
    const d = await fetch(`/api/agents/${state.activeAgent}/skills`).then(r => r.json());
    state.assignedSkillsCurrentAgent = d.skills || [];
  } catch (_) { state.assignedSkillsCurrentAgent = []; }
}

function openSkillsModal() {
  loadSkills().then(() => {
    loadAssignedSkills().then(() => {
      const { el: box } = openModal({
        title: '🧠 Skills',
        size: 'lg',
        body: buildSkillsModalHTML(),
      });
      bindSkillsModalEvents(box);
    });
  });
}

function buildSkillsModalHTML() {
  const skillsHTML = state.skills.length
    ? state.skills.map(s => `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:6px 4px;border-bottom:1px dashed var(--border);">
        <div>
          <div style="font-weight:600;">${escapeHtml(s.name)}</div>
          <div style="font-size:11px;color:var(--muted);">${s.updatedAt || ''}</div>
        </div>
        <div style="display:flex;gap:6px;">
          <button class="cmd-btn skill-select" data-name="${escapeAttr(s.name)}">Selecionar</button>
          <button class="cmd-btn skill-edit" data-name="${escapeAttr(s.name)}">Editar</button>
          <button class="cmd-btn danger skill-delete" data-name="${escapeAttr(s.name)}">Excluir</button>
        </div>
      </div>
    `).join('')
    : `<div style="color:var(--muted);font-size:12px;">Sem skills cadastradas.</div>`;

  const assignedHTML = state.assignedSkillsCurrentAgent.length
    ? state.assignedSkillsCurrentAgent.map(s => `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:6px 4px;border-bottom:1px dashed var(--border);">
        <div style="font-weight:600;">${escapeHtml(s.name)}</div>
        <button class="cmd-btn danger skill-unassign" data-name="${escapeAttr(s.name)}">Remover</button>
      </div>
    `).join('')
    : `<div style="color:var(--muted);font-size:12px;">Nenhuma skill atribuída.</div>`;

  return `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div>
        <label>SKILLS CADASTRADAS</label>
        <div id="skills-list" style="max-height:280px;overflow:auto;border:1px solid var(--border);border-radius:10px;padding:8px;margin-top:6px;">
          ${skillsHTML}
        </div>
        <div style="margin-top:8px;font-size:12px;">Selecionada: <strong id="skill-selected-name">${state.selectedSkillName || 'nenhuma'}</strong></div>
        <button class="cmd-btn" style="margin-top:8px;" id="btn-assign-skill" ${!state.selectedSkillName ? 'disabled' : ''}>Atribuir ao agente atual</button>

        <label style="margin-top:12px;display:block;">SKILLS DO AGENTE ATUAL</label>
        <div id="assigned-skills-list" style="max-height:170px;overflow:auto;border:1px solid var(--border);border-radius:10px;padding:8px;margin-top:6px;">
          ${assignedHTML}
        </div>
      </div>

      <form id="skill-form">
        <label>NOME DA SKILL</label>
        <input id="skill-name-input" class="input-cfg" placeholder="ex: dba-mysql-playbook" required style="margin-top:6px;" />
        <label style="margin-top:10px;display:block;">CONTEUDO (SKILL.md)</label>
        <textarea id="skill-content-input" class="input-cfg" rows="11" placeholder="Descreva instruções da skill..." required style="margin-top:6px;"></textarea>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <button type="submit" class="btn-save-modal">Criar/Atualizar</button>
          <button type="button" class="btn-cancel" id="btn-clear-skill-form">Limpar</button>
        </div>
      </form>
    </div>
  `;
}

function bindSkillsModalEvents(box) {
  box.addEventListener('click', async (e) => {
    const name = e.target.dataset.name;
    if (e.target.classList.contains('skill-select') && name) {
      state.selectedSkillName = name;
      const lbl = box.querySelector('#skill-selected-name');
      if (lbl) lbl.textContent = name;
      const assignBtn = box.querySelector('#btn-assign-skill');
      if (assignBtn) assignBtn.disabled = false;
    }
    if (e.target.classList.contains('skill-edit') && name) {
      try {
        const d = await fetch(`/api/skills/${encodeURIComponent(name)}`).then(r => r.json());
        if (d.ok && d.skill) {
          box.querySelector('#skill-name-input').value = d.skill.name;
          box.querySelector('#skill-content-input').value = d.skill.content || '';
        }
      } catch (_) {}
    }
    if (e.target.classList.contains('skill-delete') && name) {
      if (!confirm(`Excluir skill '${name}'?`)) return;
      await api.deleteSkill(name);
      if (state.selectedSkillName === name) state.selectedSkillName = '';
      await loadSkills();
      box.querySelector('#skills-list').innerHTML = buildSkillsModalHTML().split('id="skills-list"')[1]?.split('</div>')[0] || '';
      toast(`Skill "${name}" excluída`, 'info');
    }
    if (e.target.id === 'btn-assign-skill') {
      if (!state.selectedSkillName || !state.activeAgent) return;
      await api.assignSkill(state.activeAgent, state.selectedSkillName);
      await loadAssignedSkills();
      toast(`Skill "${state.selectedSkillName}" atribuída!`, 'success');
    }
    if (e.target.classList.contains('skill-unassign') && name) {
      await api.removeSkill(state.activeAgent, name);
      await loadAssignedSkills();
      toast(`Skill "${name}" removida do agente`, 'info');
    }
  });

  const form = box.querySelector('#skill-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = box.querySelector('#skill-name-input').value.trim();
    const content = box.querySelector('#skill-content-input').value.trim();
    if (!name || !content) return;
    await api.createSkill(name, content);
    box.querySelector('#skill-name-input').value = '';
    box.querySelector('#skill-content-input').value = '';
    state.selectedSkillName = name;
    await loadSkills();
    toast(`Skill "${name}" salva!`, 'success');
  });

  box.querySelector('#btn-clear-skill-form')?.addEventListener('click', () => {
    box.querySelector('#skill-name-input').value = '';
    box.querySelector('#skill-content-input').value = '';
  });
}

// ═══════════════════════════════════════════════════════════════
//  DETALHES DO AGENTE
// ═══════════════════════════════════════════════════════════════
async function openCurrentAgentDetailsPanel() {
  const agentId = state.activeAgent;
  if (!agentId) return;

  let ag = state.agents.find(a => a.id === agentId);
  try {
    const res = await api.getAgent(agentId);
    if (res.ok && res.agent) ag = res.agent;
  } catch (e) { console.error("Erro ao carregar detalhes:", e); }

  let modelOptions = '<option value="">(Autom\u00E1tico - Melhor dispon\u00EDvel)</option>';
  try {
    const models = state.allModels.length ? state.allModels : await api.getModels();
    state.allModels = models;
    models.forEach(m => {
      const selected = m.model_id === (ag.model || ag.llm_model) ? 'selected' : '';
      modelOptions += `<option value="${escapeAttr(m.model_id)}" ${selected}>${escapeHtml(m.display_name)} (${m.provider_name})</option>`;
    });
  } catch (e) { console.error("Erro ao carregar modelos:", e); }

  const container = document.createElement('div');
  container.className = 'ws-right-panel';
  container.innerHTML = `
    <div class="ws-panel-header">
      <button id="ws-det-back" style="background:none;border:none;cursor:pointer;color:var(--muted);font-size:16px;">\u2190</button>
      <span style="flex:1;">Configurar: ${ag.name}</span>
      <button id="ws-det-close" style="background:none;border:none;cursor:pointer;color:var(--muted);">\u2715</button>
    </div>
    
    <div class="ws-panel-body">
      <div class="modal-tabs" id="agent-edit-tabs">
        <button class="modal-tab active" data-tab="general">Geral</button>
        <button class="modal-tab" data-tab="security">Seguran\u00A7a</button>
        <button class="modal-tab" data-tab="behavior">Comportamento</button>
      </div>

      <form id="ws-det-form" class="agent-tabs-content">
        <!-- ABA: GERAL -->
        <div class="tab-pane active" id="edit-pane-general">
          <div class="modal-section-grid">
            <div class="form-group">
              <label class="form-label">NOME</label>
              <input id="det-name" class="form-input" value="${escapeAttr(ag.name)}" ${ag.id === 'main' ? 'disabled' : ''} />
            </div>
            <div class="form-group">
              <label class="form-label">TIPO</label>
              <select id="det-type" class="form-input">
                <option value="mysql-specialist" ${ag.type === 'mysql-specialist' ? 'selected' : ''}>DBA (MySQL Expert)</option>
                <option value="mockdata" ${ag.type === 'mockdata' ? 'selected' : ''}>MockData Service</option>
              </select>
            </div>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">MODELO LLM</label>
            <select id="det-model" class="form-input">${modelOptions}</select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">\u00CDCONE</label>
            <select id="det-icon" class="form-input">
              <option value="\uD83E\uDDBE" ${ag.icon === '\uD83E\uDDBE' ? 'selected' : ''}>\uD83E\uDDBE Rob\u00F4</option>
              <option value="\uD83D\uDEE1\ufe0f" ${ag.icon === '\uD83D\uDEE1\ufe0f' ? 'selected' : ''}>\uD83D\uDEE1\ufe0f Escudo</option>
              <option value="\uD83E\uDDD9\u200D\u2642\ufe0f" ${ag.icon === '\uD83E\uDDD9\u200D\u2642\ufe0f' ? 'selected' : ''}>\uD83E\uDDD9\u200D\u2642\ufe0f Mago</option>
              <option value="\uD83D\uDCCA" ${ag.icon === '\uD83D\uDCCA' ? 'selected' : ''}>\uD83D\uDCCA Gr\u00E1fico</option>
              <option value="\u26A1" ${ag.icon === '\u26A1' ? 'selected' : ''}>\u26A1 Raio</option>
            </select>
          </div>

          <hr style="border:0; border-top:1px solid var(--border); margin:20px 0;">
          <h5>Conex\u00E3o de Banco (Target)</h5>
          <div class="modal-section-grid">
            <div class="form-group"><label class="form-label">HOST</label><input id="det-db-host" class="form-input" value="${escapeAttr(ag.database?.host || '')}" /></div>
            <div class="form-group"><label class="form-label">PORTA</label><input id="det-db-port" class="form-input" type="number" value="${ag.database?.port || 3306}" /></div>
          </div>
          <div class="modal-section-grid" style="margin-top:10px;">
            <div class="form-group"><label class="form-label">USU\u00C1RIO</label><input id="det-db-user" class="form-input" value="${escapeAttr(ag.database?.user || '')}" /></div>
            <div class="form-group"><label class="form-label">DATABASE</label><input id="det-db-name" class="form-input" value="${escapeAttr(ag.database?.name || '')}" /></div>
          </div>
          <div class="form-group" style="margin-top:10px;">
            <label class="form-label">SENHA</label>
            <input id="det-db-pass" type="password" class="form-input" placeholder="****" />
          </div>
        </div>

        <!-- ABA: SEGURAN\u00C7A -->
        <div class="tab-pane" id="edit-pane-security" style="display:none">
          <div class="permissions-grid">
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Executar SQL</span>
                <span class="switch-desc">Permiss\u00E3o geral para envio de comandos ao banco.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="det-perm-execute" ${ag.permissions?.can_execute ? 'checked' : ''}><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Gravar no Banco</span>
                <span class="switch-desc">Permite INSERT, UPDATE e DELETE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="det-perm-write" ${ag.permissions?.can_write_db ? 'checked' : ''}><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Alterar Estrutura (DDL)</span>
                <span class="switch-desc">Permite ALTER, DROP, TRUNCATE e CREATE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="det-perm-ddl" ${ag.permissions?.can_ddl ? 'checked' : ''}><span class="toggle-track"></span></label>
            </div>
          </div>

          <div class="protected-tables-area" style="margin-top:20px;">
            <label class="form-label">TABELAS PROTEGIDAS</label>
            <div class="tag-input-container" id="det-protected-tags">
              ${(ag.permissions?.protected_tables || []).map(t => `<div class="tag-chip"><span>${t}</span><button type="button">\u00D7</button></div>`).join('')}
              <input type="text" id="det-tag-input" placeholder="Novo nome..." style="background:none; border:none; color:var(--ink); outline:none; font-size:12px; flex:1; min-width:80px;">
            </div>
          </div>
        </div>

        <!-- ABA: COMPORTAMENTO -->
        <div class="tab-pane" id="edit-pane-behavior" style="display:none">
          <div class="form-group">
            <label class="form-label">LIMITE DE REGISTROS</label>
            <input id="det-beh-rows" type="number" class="form-input" value="${ag.behavior?.max_result_rows || 500}" />
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">ESTILO DE RESPOSTA</label>
            <select id="det-beh-style" class="form-input">
              <option value="technical" ${ag.behavior?.response_style === 'technical' ? 'selected' : ''}>T\u00E9cnico</option>
              <option value="concise" ${ag.behavior?.response_style === 'concise' ? 'selected' : ''}>Conciso</option>
              <option value="business" ${ag.behavior?.response_style === 'business' ? 'selected' : ''}>Neg\u00F3cio</option>
            </select>
          </div>
          <div class="switch-field" style="margin-top:12px;">
             <div class="switch-label">
                <span class="switch-title">Introspec\u00E7\u00E3o antes de DDL</span>
                <span class="switch-desc">Agente confirma schema antes de tentar alterar tabelas.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="det-beh-introspect" ${ag.behavior?.introspect_before_ddl ? 'checked' : ''}><span class="toggle-track"></span></label>
          </div>
        </div>

        <button type="submit" class="btn-save" style="margin-top:25px;">Salvar Altera\u00E7\u00F5es</button>
      </form>
    </div>
  `;

  openRightPanel(container);

  // Tabs logic
  const tabs = container.querySelectorAll('.modal-tab');
  const panes = container.querySelectorAll('.tab-pane');
  tabs.forEach(tab => {
    tab.onclick = () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.style.display = 'none');
      tab.classList.add('active');
      container.querySelector(`#edit-pane-${tab.dataset.tab}`).style.display = 'block';
    };
  });

  // Tag Input logic
  const tagInput = container.querySelector('#det-tag-input');
  const tagContainer = container.querySelector('#det-protected-tags');
  tagInput.onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const val = tagInput.value.trim();
      if (val) {
        const chip = document.createElement('div');
        chip.className = 'tag-chip';
        chip.innerHTML = `<span>${val}</span><button type="button">\u00D7</button>`;
        chip.querySelector('button').onclick = () => chip.remove();
        tagContainer.insertBefore(chip, tagInput);
        tagInput.value = '';
      }
    }
  };
  tagContainer.querySelectorAll('.tag-chip button').forEach(b => b.onclick = () => b.parentElement.remove());

  container.querySelector('#ws-det-close').onclick = closeRightPanel;
  container.querySelector('#ws-det-back').onclick = closeRightPanel;

  container.querySelector('#ws-det-form').onsubmit = async (e) => {
    e.preventDefault();
    const payload = {
      name: container.querySelector('#det-name').value.trim(),
      type: container.querySelector('#det-type').value,
      model: container.querySelector('#det-model').value || null,
      icon: container.querySelector('#det-icon').value,
      database: {
        host: container.querySelector('#det-db-host').value.trim(),
        port: parseInt(container.querySelector('#det-db-port').value),
        user: container.querySelector('#det-db-user').value.trim(),
        name: container.querySelector('#det-db-name').value.trim(),
        password: container.querySelector('#det-db-pass').value
      },
      permissions: {
        can_execute: container.querySelector('#det-perm-execute').checked,
        can_read_db: true,
        can_write_db: container.querySelector('#det-perm-write').checked,
        can_ddl: container.querySelector('#det-perm-ddl').checked,
        protected_tables: Array.from(tagContainer.querySelectorAll('.tag-chip span')).map(s => s.textContent)
      },
      behavior: {
        max_result_rows: parseInt(container.querySelector('#det-beh-rows').value),
        response_style: container.querySelector('#det-beh-style').value,
        introspect_before_ddl: container.querySelector('#det-beh-introspect').checked
      }
    };

    try {
      await api.updateAgent(ag.id, payload);
      toast('Agente atualizado com sucesso!', 'success');
      loadAgents(); // Refresh list
      closeRightPanel();
    } catch (err) { toast(`Erro: ${err.message}`, 'danger'); }
  };
}

// ═══════════════════════════════════════════════════════════════
//  CRIAR NOVO AGENTE
// ═══════════════════════════════════════════════════════════════
async function openNewAgentModal() {
  let modelOptions = '<option value="">(Autom\u00E1tico - Melhor dispon\u00EDvel)</option>';
  try {
    const models = state.allModels.length ? state.allModels : await api.getModels();
    state.allModels = models;
    models.forEach(m => {
      modelOptions += `<option value="${escapeAttr(m.model_id)}">${escapeHtml(m.display_name)} (${m.provider_name})</option>`;
    });
  } catch (e) { console.error("Erro ao carregar modelos:", e); }

  const { el: box, close: closeModalFn } = openModal({
    title: 'Configurar Agente Especialista',
    size: 'lg',
    body: `
      <div class="modal-tabs" id="agent-modal-tabs">
        <button class="modal-tab active" data-tab="general">Geral</button>
        <button class="modal-tab" data-tab="security">Seguran\u00E7a</button>
        <button class="modal-tab" data-tab="behavior">Comportamento</button>
      </div>

      <div class="agent-tabs-content">
        <!-- ABA: GERAL -->
        <div class="tab-pane active" id="pane-general">
          <div class="modal-section-grid">
            <div class="form-group">
              <label class="form-label">NOME DO AGENTE</label>
              <input id="ag-name" class="form-input" placeholder="Ex: DBA MasterKey" required />
            </div>
            <div class="form-group">
              <label class="form-label">TIPO</label>
              <select id="ag-type" class="form-input">
                <option value="mysql-specialist">DBA (MySQL Specialist)</option>
                <option value="mockdata">MockData Service</option>
              </select>
            </div>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">MODELO LLM</label>
            <select id="ag-model" class="form-input">${modelOptions}</select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">\u00CDCONE</label>
            <select id="ag-icon" class="form-input">
              <option value="\uD83E\uDDBE">\uD83E\uDDBE Rob\u00F4</option>
              <option value="\uD83D\uDEE1\ufe0f">\uD83D\uDEE1\ufe0f Escudo</option>
              <option value="\uD83E\uDDD9\u200D\u2642\ufe0f">\uD83E\uDDD9\u200D\u2642\ufe0f Mago</option>
              <option value="\uD83D\uDCCA">\uD83D\uDCCA Gr\u00E1fico</option>
              <option value="\u26A1">\u26A1 Raio</option>
            </select>
          </div>

          <hr style="border:0; border-top:1px solid var(--border); margin:20px 0;">
          <h5>Banco de Dados ALVO (Target)</h5>
          <div class="modal-section-grid">
            <div class="form-group"><label class="form-label">HOST</label><input id="db-host" class="form-input" placeholder="192.168.0.5" /></div>
            <div class="form-group"><label class="form-label">PORTA</label><input id="db-port" class="form-input" type="number" value="3306" /></div>
          </div>
          <div class="modal-section-grid" style="margin-top:10px;">
            <div class="form-group"><label class="form-label">USU\u00C1RIO</label><input id="db-user" class="form-input" placeholder="root" /></div>
            <div class="form-group"><label class="form-label">DATABASE</label><input id="db-name" class="form-input" placeholder="devhacks_site" /></div>
          </div>
          <div class="form-group" style="margin-top:10px;">
            <label class="form-label">SENHA</label>
            <input id="db-pass" type="password" class="form-input" placeholder="****" />
          </div>
        </div>

        <!-- ABA: SEGURAN\u00C7A -->
        <div class="tab-pane" id="pane-security" style="display:none">
          <div class="permissions-grid">
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Executar SQL</span>
                <span class="switch-desc">Permiss\u00E3o geral para envio de comandos ao banco.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="perm-execute" checked><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Gravar no Banco</span>
                <span class="switch-desc">Permite INSERT, UPDATE e DELETE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="perm-write" checked><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Alterar Estrutura (DDL)</span>
                <span class="switch-desc">Permite ALTER, DROP, TRUNCATE e CREATE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="perm-ddl"><span class="toggle-track"></span></label>
            </div>
          </div>

          <div class="protected-tables-area" style="margin-top:20px;">
            <label class="form-label">TABELAS PROTEGIDAS (O Agente n\u00E3o poder\u00E1 acessar)</label>
            <div class="tag-input-container" id="protected-tags">
              <input type="text" id="tag-input" placeholder="Digite o nome e pressione Enter..." style="background:none; border:none; color:var(--ink); outline:none; font-size:12px; flex:1; min-width:120px;">
            </div>
          </div>
        </div>

        <!-- ABA: COMPORTAMENTO -->
        <div class="tab-pane" id="pane-behavior" style="display:none">
          <div class="form-group">
            <label class="form-label">LIMITE DE REGISTROS POR RESPOSTA</label>
            <input id="beh-rows" type="number" class="form-input" value="500" />
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">ESTILO DE RESPOSTA</label>
            <select id="beh-style" class="form-input">
              <option value="technical">T\u00E9cnico e Detalhado</option>
              <option value="concise">Conciso e Direto</option>
              <option value="business">Focado em Neg\u00F3cio</option>
            </select>
          </div>
          <div class="switch-field" style="margin-top:12px;">
             <div class="switch-label">
                <span class="switch-title">Introspec\u00E7\u00E3o antes de DDL</span>
                <span class="switch-desc">Agente confirma schema antes de tentar alterar tabelas.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="beh-introspect" checked><span class="toggle-track"></span></label>
          </div>
        </div>
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: 'Salvar Agente',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('ag-name')?.value.trim();
          if (!name) { toast("Nome \u00E9 obrigat\u00F3rio", "danger"); return; }

          const payload = {
            name,
            type: document.getElementById('ag-type').value,
            model: document.getElementById('ag-model').value || null,
            icon: document.getElementById('ag-icon').value,
            database: {
              host: document.getElementById('db-host').value.trim(),
              port: parseInt(document.getElementById('db-port').value),
              user: document.getElementById('db-user').value.trim(),
              name: document.getElementById('db-name').value.trim(),
              password: document.getElementById('db-pass').value
            },
            permissions: {
                can_execute: document.getElementById('perm-execute').checked,
                can_read_db: true,
                can_write_db: document.getElementById('perm-write').checked,
                can_ddl: document.getElementById('perm-ddl').checked,
                protected_tables: Array.from(document.querySelectorAll('.tag-chip span')).map(s => s.textContent)
            },
            behavior: {
                max_result_rows: parseInt(document.getElementById('beh-rows').value),
                response_style: document.getElementById('beh-style').value,
                introspect_before_ddl: document.getElementById('beh-introspect').checked
            }
          };

          try {
            const data = await fetch('/api/agents', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            }).then(r => r.json());

            if (data.ok) {
              state.agents.push(data.agent);
              state.messagesByAgent[data.agent.id] = [];
              switchAgent(data.agent.id);
              toast(`Agente "${name}" configurado com sucesso!`, 'success');
              close();
            } else {
              toast(`Erro: ${data.message}`, 'danger');
            }
          } catch (err) { toast(`Erro: ${err.message}`, 'danger'); }
        }
      }
    ]
  });

  // LÃ³gica de Abas
  const tabs = box.querySelectorAll('.modal-tab');
  const panes = box.querySelectorAll('.tab-pane');
  tabs.forEach(tab => {
    tab.onclick = () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.style.display = 'none');
      tab.classList.add('active');
      box.querySelector(`#pane-${tab.dataset.tab}`).style.display = 'block';
    };
  });

  // LÃ³gica de Protected Tables (Tag Input)
  const tagInput = box.querySelector('#tag-input');
  const tagContainer = box.querySelector('#protected-tags');
  tagInput.onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const val = tagInput.value.trim();
      if (val) {
        const chip = document.createElement('div');
        chip.className = 'tag-chip';
        chip.innerHTML = `<span>${val}</span><button type="button">\u00D7</button>`;
        chip.querySelector('button').onclick = () => chip.remove();
        tagContainer.insertBefore(chip, tagInput);
        tagInput.value = '';
      }
    }
  };
}

// ═══════════════════════════════════════════════════════════════
//  FILE CHIPS
// ═══════════════════════════════════════════════════════════════
function renderFileChips() {
  if (!els.fileChips) return;
  els.fileChips.innerHTML = state.chatFiles.map((f, i) => `
    <div style="background:rgba(99,91,255,.08);border:1px solid rgba(99,91,255,.2);border-radius:20px;padding:2px 10px;font-size:11px;display:flex;align-items:center;gap:6px;color:var(--accent);">
      <span>📎</span>
      <span>${escapeHtml(f.name)}</span>
      <button type="button" data-idx="${i}" style="background:transparent;border:none;cursor:pointer;font-size:13px;color:var(--muted);">×</button>
    </div>
  `).join('');

  els.fileChips.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      state.chatFiles.splice(idx, 1);
      renderFileChips();
    });
  });
}

// ═══════════════════════════════════════════════════════════════
//  UTILS
// ═══════════════════════════════════════════════════════════════
function getSessionId() {
  if (!state.sessionId) {
    state.sessionId = localStorage.getItem('aa-session');
    if (!state.sessionId) {
      state.sessionId = crypto.randomUUID?.() || `sess-${Math.random().toString(36).slice(2)}`;
      localStorage.setItem('aa-session', state.sessionId);
    }
  }
  return state.sessionId;
}

function autoResize(e) {
  const el = e.target;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  if (!str) return '';
  return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ═══════════════════════════════════════════════════════════════
//  MODEL PICKER POPOVER (Restauração)
// ═══════════════════════════════════════════════════════════════
window.toggleModelPicker = async function() {
  const popover = document.getElementById('model-picker-popover');
  if (!popover) return;
  
  if (popover.style.display === 'block') {
    popover.style.display = 'none';
    return;
  }
  
  popover.style.display = 'block';
  const list = document.getElementById('model-picker-list');
  list.innerHTML = '<div style="padding:10px;color:var(--muted);font-size:11px;">Carregando modelos...</div>';

  try {
    const models = state.allModels && state.allModels.length ? state.allModels : await api.getModels();
    state.allModels = models;
    
    // Filtro rápido: apenas modelos ativos e disponíveis
    const filtered = models.filter(m => m.is_available && m.is_active);

    list.innerHTML = filtered.map(m => `
      <div class="popover-item" onclick="selectModelFromPicker('${escapeAttr(m.model_id)}')">
        <div style="font-weight:600;">${escapeHtml(m.display_name)}</div>
        <div style="font-size:10px;color:var(--muted);">${m.provider_name}</div>
      </div>
    `).join('');
    
    if (!filtered.length) {
      list.innerHTML = '<div style="padding:10px;color:var(--muted);font-size:11px;">Nenhum modelo disponível.</div>';
    }
  } catch (e) {
    list.innerHTML = '<div style="padding:10px;color:var(--danger);font-size:11px;">Erro ao carregar modelos.</div>';
  }
};

window.selectModelFromPicker = async function(modelId) {
  const agentId = state.activeAgent;
  if (!agentId) return;
  
  try {
    const ag = state.agents.find(a => a.id === agentId);
    if (!ag) return;
    
    const payload = { model: modelId };
    await api.updateAgent(agentId, payload);
    ag.model = modelId;
    
    toast(`Modelo alterado para ${modelId}`, 'success');
    document.getElementById('model-picker-popover').style.display = 'none';
    updateCurrentAgent();
  } catch (err) {
    toast('Erro ao trocar modelo', 'danger');
  }
};

// Fechar popover ao clicar fora
document.addEventListener('mousedown', (e) => {
  const popover = document.getElementById('model-picker-popover');
  const nameLabel = document.getElementById('ws-agent-name');
  if (popover && !popover.contains(e.target) && e.target !== nameLabel) {
    popover.style.display = 'none';
  }
});
