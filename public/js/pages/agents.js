/**
 * agents.js — View de Gestão de Agentes (Dashboard mode)
 * Lista e edita agentes com metadados expandidos.
 *
 * @param {HTMLElement} container
 * @returns {Function} teardown
 */

import { api }                from '../api.js';
import { createTable, showLoading, showError, toast } from '../utils/dom.js';
import { openModal, confirmModal } from '../components/modal.js';

export async function renderAgentsPage(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <div class="page-title"><span class="page-icon">🤖</span> Configuração de Agentes</div>
        <div class="page-subtitle">Gerencie metadados, prompts e skills de cada agente</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" id="btn-new-agent-dash">+ Novo Agente</button>
      </div>
    </div>
    <div class="page-body">
      <div class="card">
        <div class="card-header">
          <span>Agentes Registrados</span>
          <span id="agents-count" class="text-muted"></span>
        </div>
        <div id="agents-table-wrap"></div>
      </div>
    </div>
  `;

  const wrap = container.querySelector('#agents-table-wrap');
  const countEl = container.querySelector('#agents-count');

  async function refreshAgents() {
    showLoading(wrap, 'Carregando agentes...');
    try {
      const data = await api.getAgents();
      const agents = data.agents || [];
      countEl.textContent = `${agents.length} agente(s)`;

      if (agents.length === 0) {
        wrap.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">🤖</div>
            <div class="empty-state-title">Nenhum agente registrado</div>
          </div>
        `;
        return;
      }

      const rows = agents.map(ag => [
        `<span class="text-mono" style="font-size:11px;">${ag.id}</span>`,
        ag.name,
        `<span style="font-size:11px;color:var(--ink-2);">${ag.llmModel || '<span class="text-muted">padrão</span>'}</span>`,
        buildAgentActions(ag),
      ]);

      const table = createTable(['ID', 'Nome', 'Modelo LLM', 'Ações'], rows);
      wrap.innerHTML = '';
      wrap.appendChild(table);

      wrap.querySelectorAll('[data-agent-action]').forEach(btn => {
        btn.addEventListener('click', () => {
          const { agentAction, agentId } = btn.dataset;
          const ag = agents.find(a => a.id === agentId);
          if (!ag) return;
          if (agentAction === 'edit') openAgentEditModal(ag, refreshAgents);
          if (agentAction === 'delete') deleteAgent(ag, refreshAgents);
        });
      });

    } catch (err) {
      showError(wrap, `Falha ao carregar agentes: ${err.message}`);
    }
  }

  container.querySelector('#btn-new-agent-dash').addEventListener('click', () =>
    openNewAgentModal(refreshAgents)
  );

  await refreshAgents();
  return () => {};
}

function buildAgentActions(ag) {
  const canDelete = ag.id !== 'main';
  return `
    <div class="col-actions">
      <button class="btn btn-sm btn-secondary" data-agent-action="edit" data-agent-id="${ag.id}">Editar</button>
      ${canDelete ? `<button class="btn btn-sm btn-danger" data-agent-action="delete" data-agent-id="${ag.id}">Excluir</button>` : ''}
    </div>
  `;
}

function openAgentEditModal(ag, onSave) {
  openModal({
    title: `Editar Agente: ${ag.name}`,
    size: 'lg',
    body: `
      <div class="form-group">
        <label class="form-label">NOME</label>
        <input id="edit-ag-name" class="form-input" value="${escAttr(ag.name)}" ${ag.id === 'main' ? 'disabled' : ''} required />
      </div>
      <div class="form-group">
        <label class="form-label">CUSTOM PROMPT</label>
        <textarea id="edit-ag-desc" class="form-input" rows="8" placeholder="Defina o comportamento do agente...">${escHtml(ag.description || '')}</textarea>
      </div>
      <div class="form-group">
        <label class="form-label">MODELO LLM</label>
        <input id="edit-ag-model" class="form-input" value="${escAttr(ag.llmModel || '')}" placeholder="Deixe em branco para usar o padrão" />
        <span class="form-hint">Sobrescreve o modelo padrão configurado nas Settings.</span>
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: 'Salvar',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('edit-ag-name')?.value.trim();
          const description = document.getElementById('edit-ag-desc')?.value.trim();
          const llmModel = document.getElementById('edit-ag-model')?.value.trim();
          if (!name) return;
          try {
            await api.updateAgent(ag.id, { name, description, llmModel });
            toast(`Agente "${name}" salvo!`, 'success');
            close();
            if (onSave) onSave();
          } catch (err) {
            toast(`Erro: ${err.message}`, 'danger');
          }
        },
      },
    ],
  });
}

function openNewAgentModal(onSave) {
  openModal({
    title: 'Novo Agente',
    body: `
      <div class="form-group">
        <label class="form-label">NOME DO AGENTE</label>
        <input id="new-ag-name" class="form-input" placeholder="Ex: Canvas AI" required />
      </div>
      <div class="form-group">
        <label class="form-label">PROMPT DE INSTRUÇÕES</label>
        <textarea id="new-ag-prompt" class="form-input" rows="5" placeholder="Descreva como o agente deve se comportar..."></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">MODELO LLM (OPCIONAL)</label>
        <input id="new-ag-model" class="form-input" placeholder="Deixe em branco para usar o padrão" />
      </div>
      <div class="form-group">
        <label class="form-label">ARQUIVOS DE ESPECIALIDADE (OPCIONAL)</label>
        <input type="file" id="new-ag-files" multiple accept=".md,.txt,.json,.csv" class="form-input" />
        <span class="form-hint">Bases de conhecimento para especialização do agente.</span>
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: 'Criar Agente',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('new-ag-name')?.value.trim();
          const description = document.getElementById('new-ag-prompt')?.value.trim();
          const llmModel = document.getElementById('new-ag-model')?.value.trim();
          const filesEl = document.getElementById('new-ag-files');
          if (!name) return;
          const formData = new FormData();
          formData.append('name', name);
          formData.append('description', description);
          formData.append('llmModel', llmModel);
          if (filesEl) for (const f of filesEl.files) formData.append('files', f);
          try {
            await fetch('/api/agents', { method: 'POST', body: formData }).then(r => r.json());
            toast(`Agente "${name}" criado!`, 'success');
            close();
            if (onSave) onSave();
          } catch (err) {
            toast(`Erro: ${err.message}`, 'danger');
          }
        },
      },
    ],
  });
}

async function deleteAgent(ag, onDelete) {
  confirmModal({
    title: 'Excluir Agente',
    message: `Excluir o agente <strong>${ag.name}</strong>? Esta ação não pode ser desfeita.`,
    confirmLabel: 'Excluir',
    danger: true,
    onConfirm: async () => {
      try {
        await fetch(`/api/agents/${ag.id}`, { method: 'DELETE' });
        toast(`Agente "${ag.name}" excluído`, 'info');
        if (onDelete) onDelete();
      } catch (err) {
        toast(`Erro: ${err.message}`, 'danger');
      }
    },
  });
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escAttr(str) {
  return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
