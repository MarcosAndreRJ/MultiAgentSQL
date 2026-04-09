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
        ag.icon || '🤖',
        `<span class="text-mono" style="font-size:11px;">${ag.id}</span>`,
        ag.name,
        `<span style="font-size:11px;color:var(--ink-2);">${ag.model || '<span class="text-muted">padrão</span>'}</span>`,
        buildAgentActions(ag),
      ]);

      const table = createTable(['Ícone', 'ID', 'Nome', 'Modelo LLM', 'Ações'], rows);
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

async function openAgentEditModal(ag, onSave) {
  // Busca modelos para o select
  let modelOptions = '<option value="">(Automático - Melhor disponível)</option>';
  try {
    const models = await api.getModels();
    models.forEach(m => {
      const selected = m.model_id === ag.llmModel ? 'selected' : '';
      modelOptions += `<option value="${escAttr(m.model_id)}" ${selected}>${escHtml(m.display_name)} (${m.provider_name})</option>`;
    });
  } catch (e) {
    console.error("Erro ao buscar modelos:", e);
  }

  const icons = ['🤖', '👨‍💻', '📊', '🛠️', '🛡️', '🔍', '⚡'];
  let iconOptions = '';
  icons.forEach(ic => {
    const selected = (ag.icon || '🤖') === ic ? 'selected' : '';
    iconOptions += `<option value="${ic}" ${selected}>${ic}</option>`;
  });

  openModal({

    title: `Editar Agente: ${ag.name}`,
    size: 'lg',
    body: `
      <div class="modal-sections">
        <div class="modal-section">
          <h5>Configuração Básica</h5>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">NOME</label>
              <input id="edit-ag-name" class="form-input" value="${escAttr(ag.name)}" ${ag.id === 'main' ? 'disabled' : ''} required />
            </div>
            <div class="form-group">
              <label class="form-label">TIPO</label>
              <select id="edit-ag-type" class="form-input">
                <option value="mysql-specialist" ${ag.type === 'mysql-specialist' ? 'selected' : ''}>DBA (Oracle/MySQL Specialist)</option>
                <option value="mockdata" ${ag.type === 'mockdata' ? 'selected' : ''}>MockData Generator</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">ÍCONE</label>
              <select id="edit-ag-icon" class="form-input" style="font-size:1.2rem;">
                ${iconOptions}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">CUSTOM PROMPT</label>
            <textarea id="edit-ag-desc" class="form-input" rows="4" placeholder="Defina o comportamento do agente...">${escHtml(ag.description || '')}</textarea>
          </div>
          <div class="form-group">
            <label class="form-label">MODELO LLM</label>
            <select id="edit-ag-model" class="form-input">
              ${modelOptions}
            </select>
            <span class="form-hint">O sistema usará o melhor modelo do ranking se deixado em automático.</span>
          </div>
        </div>

        <div class="modal-section">
          <h5>Conexão de Banco (Target DB)</h5>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">HOST</label>
              <input id="edit-db-host" class="form-input" value="${escAttr(ag.database?.host || '')}" placeholder="localhost ou IP" />
            </div>
            <div class="form-group">
              <label class="form-label">PORTA</label>
              <input id="edit-db-port" class="form-input" type="number" value="${ag.database?.port || 3306}" />
            </div>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">USER</label>
              <input id="edit-db-user" class="form-input" value="${escAttr(ag.database?.user || '')}" />
            </div>
            <div class="form-group">
              <label class="form-label">DATABASE</label>
              <input id="edit-db-name" class="form-input" value="${escAttr(ag.database?.name || '')}" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">PASSWORD</label>
            <input id="edit-db-pass" type="password" class="form-input" value="${escAttr(ag.database?.password || '')}" placeholder="Deixe em branco para não alterar" />
          </div>
        </div>
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: 'Salvar Alterações',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('edit-ag-name')?.value.trim();
          const type = document.getElementById('edit-ag-type')?.value;
          const icon = document.getElementById('edit-ag-icon')?.value;
          const description = document.getElementById('edit-ag-desc')?.value.trim();
          const llmModel = document.getElementById('edit-ag-model')?.value.trim();
          
          const dbHost = document.getElementById('edit-db-host')?.value.trim();
          const dbPort = parseInt(document.getElementById('edit-db-port')?.value);
          const dbUser = document.getElementById('edit-db-user')?.value.trim();
          const dbName = document.getElementById('edit-db-name')?.value.trim();
          const dbPass = document.getElementById('edit-db-pass')?.value;

          if (!name) return;
          
          const payload = { 
            name, 
            description, 
            model: llmModel || null,
            type,
            icon
          };

          if (dbHost && dbUser && dbName) {
            payload.database = {
              host: dbHost,
              port: dbPort,
              user: dbUser,
              name: dbName,
              password: dbPass
            };
          }

          try {
            await api.updateAgent(ag.id, payload);
            toast(`Agente "${name}" atualizado!`, 'success');
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

async function openNewAgentModal(onSave) {
  // Busca modelos para o select
  let modelOptions = '<option value="">(Automático - Melhor disponível)</option>';
  try {
    const models = await api.getModels();
    models.forEach(m => {
      modelOptions += `<option value="${escAttr(m.model_id)}">${escHtml(m.display_name)} (${m.provider_name})</option>`;
    });
  } catch (e) {
    console.error("Erro ao buscar modelos:", e);
  }

  const icons = ['🤖', '👨‍💻', '📊', '🛠️', '🛡️', '🔍', '⚡'];
  let iconOptions = '';
  icons.forEach(ic => {
    iconOptions += `<option value="${ic}">${ic}</option>`;
  });

  openModal({

    title: 'Novo Agente Especialista',
    size: 'lg',
    body: `
      <div class="modal-sections">
        <div class="modal-section">
          <h5>Configuração de Identidade</h5>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">NOME DO AGENTE</label>
              <input id="new-ag-name" class="form-input" placeholder="Ex: MySQL Sentinel" required />
            </div>
            <div class="form-group">
              <label class="form-label">TIPO</label>
              <select id="new-ag-type" class="form-input">
                <option value="mysql-specialist">DBA (MySQL Expert)</option>
                <option value="mockdata">MockData Service</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">ÍCONE</label>
              <select id="new-ag-icon" class="form-input" style="font-size:1.2rem;">
                ${iconOptions}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">PROMPT DE INSTRUÇÕES</label>
            <textarea id="new-ag-prompt" class="form-input" rows="4" placeholder="Descreva como o agente deve se comportar..."></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">MODELO LLM</label>
            <select id="new-ag-model" class="form-input">
              ${modelOptions}
            </select>
          </div>
        </div>

        <div class="modal-section">
          <h5>Banco de Dados do Agente (Opcional)</h5>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">HOST</label>
              <input id="new-db-host" class="form-input" placeholder="127.0.0.1" />
            </div>
            <div class="form-group">
              <label class="form-label">PORTA</label>
              <input id="new-db-port" class="form-input" type="number" value="3306" />
            </div>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">USUÁRIO</label>
              <input id="new-db-user" class="form-input" placeholder="root" />
            </div>
            <div class="form-group">
              <label class="form-label">DATABASE</label>
              <input id="new-db-name" class="form-input" placeholder="my_app_db" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">SENHA</label>
            <input id="new-db-pass" type="password" class="form-input" />
          </div>
        </div>
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: 'Criar Agente',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('new-ag-name')?.value.trim();
          const type = document.getElementById('new-ag-type')?.value;
          const icon = document.getElementById('new-ag-icon')?.value;
          const description = document.getElementById('new-ag-prompt')?.value.trim();
          const model = document.getElementById('new-ag-model')?.value;
          
          const dbHost = document.getElementById('new-db-host')?.value.trim();
          const dbPort = document.getElementById('new-db-port')?.value;
          const dbUser = document.getElementById('new-db-user')?.value.trim();
          const dbName = document.getElementById('new-db-name')?.value.trim();
          const dbPass = document.getElementById('new-db-pass')?.value;

          if (!name) return;

          const payload = {
            name,
            description,
            model: model || null,
            type,
            icon
          };

          if (dbHost && dbUser && dbName) {
            payload.database = {
              host: dbHost,
              port: parseInt(dbPort),
              user: dbUser,
              name: dbName,
              password: dbPass
            };
          }

          try {
            // Agora enviamos JSON puro para o backend (ajustado no schema)
            await fetch('/api/agents', { 
              method: 'POST', 
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload) 
            }).then(r => r.json());

            toast(`Agente "${name}" criado com sucesso!`, 'success');
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
