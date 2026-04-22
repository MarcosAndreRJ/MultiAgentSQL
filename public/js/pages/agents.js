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
        btn.addEventListener('click', async () => {
          const { agentAction, agentId } = btn.dataset;
          let ag = agents.find(a => a.id === agentId);
          if (!ag) return;

          if (agentAction === 'edit') {
            try {
              const res = await fetch(`/api/agents/${agentId}`);
              const d = await res.json();
              if (d.ok && d.agent) ag = d.agent;
            } catch (e) { console.error("Erro ao carregar detalhes completos:", e); }
            openAgentEditModal(ag, refreshAgents);
          }
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

  const modal = openModal({

    title: `Editar Agente: ${ag.name}`,
    size: 'lg',
    body: `
      <div class="modal-tabs" id="agent-edit-tabs">
        <button class="modal-tab active" data-tab="general">Geral</button>
        <button class="modal-tab" data-tab="security">Segurança</button>
        <button class="modal-tab" data-tab="behavior">Comportamento</button>
      </div>

      <div class="agent-tabs-content">
        <!-- ABA: GERAL -->
        <div class="tab-pane active" id="edit-pane-general">
          <div class="modal-section-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
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
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">MODELO LLM</label>
            <select id="edit-ag-model" class="form-input">${modelOptions}</select>
            <span class="form-hint">O sistema usará o melhor modelo se deixado automático.</span>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">ÍCONE</label>
            <select id="edit-ag-icon" class="form-input" style="font-size:1.2rem;">
              ${iconOptions}
            </select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">CUSTOM PROMPT</label>
            <textarea id="edit-ag-desc" class="form-input" rows="4">${escHtml(ag.description || '')}</textarea>
          </div>
          
          <hr style="border:0; border-top:1px solid var(--border); margin:20px 0;">
          <h5>Conexão de Banco (Target DB)</h5>
          <div class="modal-section-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="form-group">
              <label class="form-label">HOST</label>
              <input id="edit-db-host" class="form-input" value="${escAttr(ag.database?.host || '')}" placeholder="localhost ou IP" />
            </div>
            <div class="form-group">
              <label class="form-label">PORTA</label>
              <input id="edit-db-port" class="form-input" type="number" value="${ag.database?.port || 3306}" />
            </div>
          </div>
          <div class="modal-section-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top:10px;">
            <div class="form-group">
              <label class="form-label">USER</label>
              <input id="edit-db-user" class="form-input" value="${escAttr(ag.database?.user || '')}" />
            </div>
            <div class="form-group">
              <label class="form-label">DATABASE</label>
              <input id="edit-db-name" class="form-input" value="${escAttr(ag.database?.name || '')}" />
            </div>
          </div>
          <div class="form-group" style="margin-top:10px;">
            <label class="form-label">PASSWORD</label>
            <input id="edit-db-pass" type="password" class="form-input" value="${escAttr(ag.database?.password || '')}" placeholder="Mantenha em branco para não alterar" />
          </div>
        </div>

        <!-- ABA: SEGURANÇA -->
        <div class="tab-pane" id="edit-pane-security">
          <div class="permissions-grid">
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Executar SQL</span>
                <span class="switch-desc">Permissão geral para envio de comandos ao banco.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="edit-perm-execute" ${ag.permissions?.can_execute !== false ? 'checked' : ''}><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Gravar no Banco</span>
                <span class="switch-desc">Permite INSERT, UPDATE e DELETE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="edit-perm-write" ${ag.permissions?.can_write_db !== false ? 'checked' : ''}><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Alterar Estrutura (DDL)</span>
                <span class="switch-desc">Permite ALTER, DROP, TRUNCATE e CREATE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="edit-perm-ddl" ${ag.permissions?.can_ddl ? 'checked' : ''}><span class="toggle-track"></span></label>
            </div>
          </div>

          <div class="protected-tables-area">
            <label class="form-label">TABELAS PROTEGIDAS</label>
            <div class="tag-input-container" id="edit-protected-tags">
              ${(ag.permissions?.protected_tables || []).map(t => `<div class="tag-chip"><span>${t}</span><button type="button">\u00D7</button></div>`).join('')}
              <input type="text" id="edit-tag-input" placeholder="Novo nome..." style="background:none; border:none; color:var(--ink); outline:none; font-size:12px; flex:1; min-width:80px;">
            </div>
          </div>
        </div>

        <!-- ABA: COMPORTAMENTO -->
        <div class="tab-pane" id="edit-pane-behavior">
          <div class="form-group">
            <label class="form-label">LIMITE DE REGISTROS</label>
            <input id="edit-beh-rows" type="number" class="form-input" value="${ag.behavior?.max_result_rows || 500}" />
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">ESTILO DE RESPOSTA</label>
            <select id="edit-beh-style" class="form-input">
              <option value="technical" ${ag.behavior?.response_style === 'technical' ? 'selected' : ''}>Técnico / Direto</option>
              <option value="consultative" ${ag.behavior?.response_style === 'consultative' ? 'selected' : ''}>Consultivo / Explicativo</option>
              <option value="minimal" ${ag.behavior?.response_style === 'minimal' ? 'selected' : ''}>Minimalista (Só o Código)</option>
            </select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">IDIOMA (RESPOSTA)</label>
            <input id="edit-beh-lang" class="form-input" value="${escAttr(ag.behavior?.language || 'pt-BR')}" />
          </div>
          
          <div class="switch-field" style="margin-top:20px;">
            <div class="switch-label">
              <span class="switch-title">Auto-refinamento de Schema</span>
              <span class="switch-desc">Sempre revisar DDL (schema) antes de comandos não-descritivos.</span>
            </div>
            <label class="toggle-switch"><input type="checkbox" id="edit-beh-intro" ${ag.behavior?.introspect_before_ddl !== false ? 'checked' : ''}><span class="toggle-track"></span></label>
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

          const pExecute = document.getElementById('edit-perm-execute')?.checked;
          const pWrite = document.getElementById('edit-perm-write')?.checked;
          const pDdl = document.getElementById('edit-perm-ddl')?.checked;
          
          const protectedTables = [];
          document.querySelectorAll('#edit-protected-tags .tag-chip span').forEach(el => {
            protectedTables.push(el.textContent);
          });

          const maxRows = parseInt(document.getElementById('edit-beh-rows')?.value || "500");
          const style = document.getElementById('edit-beh-style')?.value || "technical";
          const lang = document.getElementById('edit-beh-lang')?.value || "pt-BR";
          const introspect = document.getElementById('edit-beh-intro')?.checked;

          if (!name) return;
          
          const payload = { 
            name, 
            description, 
            model: llmModel || null,
            type,
            icon,
            permissions: {
              can_execute: pExecute,
              can_write_db: pWrite,
              can_ddl: pDdl,
              can_read_db: true,
              protected_tables: protectedTables
            },
            behavior: {
              max_result_rows: maxRows,
              response_style: style,
              language: lang,
              introspect_before_ddl: introspect,
              max_loop_steps: 3
            }
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

  if (modal && modal.el) {
    // Eventos das abas
    modal.el.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        modal.el.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
        modal.el.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        
        tab.classList.add('active');
        modal.el.querySelector('#edit-pane-' + tab.dataset.tab).classList.add('active');
      });
    });

    // Eventos de tags (tabelas)
    const tagsContainer = modal.el.querySelector('#edit-protected-tags');
    const tagInput = modal.el.querySelector('#edit-tag-input');
    
    if (tagsContainer && tagInput) {
      tagsContainer.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
          e.target.closest('.tag-chip').remove();
        }
      });
      
      tagInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
          e.preventDefault();
          const val = tagInput.value.trim().replace(/,/g, '');
          if (val) {
            const chip = document.createElement('div');
            chip.className = 'tag-chip';
            chip.innerHTML = `<span>${escHtml(val)}</span><button type="button">×</button>`;
            tagsContainer.insertBefore(chip, tagInput);
            tagInput.value = '';
          }
        }
      });
    }
  }
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

  const modal = openModal({

    title: 'Novo Agente Especialista',
    size: 'lg',
    body: `
      <div class="modal-tabs" id="agent-new-tabs">
        <button class="modal-tab active" data-tab="general">Geral</button>
        <button class="modal-tab" data-tab="security">Segurança</button>
        <button class="modal-tab" data-tab="behavior">Comportamento</button>
      </div>

      <div class="agent-tabs-content">
        <!-- ABA: GERAL -->
        <div class="tab-pane active" id="new-pane-general">
          <div class="modal-section-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
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
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">MODELO LLM</label>
            <select id="new-ag-model" class="form-input">${modelOptions}</select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">ÍCONE</label>
            <select id="new-ag-icon" class="form-input" style="font-size:1.2rem;">
              ${iconOptions}
            </select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">PROMPT DE INSTRUÇÕES</label>
            <textarea id="new-ag-prompt" class="form-input" rows="4" placeholder="Descreva como o agente deve se comportar..."></textarea>
          </div>
          
          <hr style="border:0; border-top:1px solid var(--border); margin:20px 0;">
          <h5>Banco de Dados do Agente (Opcional)</h5>
          <div class="modal-section-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="form-group">
              <label class="form-label">HOST</label>
              <input id="new-db-host" class="form-input" placeholder="127.0.0.1" />
            </div>
            <div class="form-group">
              <label class="form-label">PORTA</label>
              <input id="new-db-port" class="form-input" type="number" value="3306" />
            </div>
          </div>
          <div class="modal-section-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top:10px;">
            <div class="form-group">
              <label class="form-label">USUÁRIO</label>
              <input id="new-db-user" class="form-input" placeholder="root" />
            </div>
            <div class="form-group">
              <label class="form-label">DATABASE</label>
              <input id="new-db-name" class="form-input" placeholder="my_app_db" />
            </div>
          </div>
          <div class="form-group" style="margin-top:10px;">
            <label class="form-label">SENHA</label>
            <input id="new-db-pass" type="password" class="form-input" />
          </div>
        </div>

        <!-- ABA: SEGURANÇA -->
        <div class="tab-pane" id="new-pane-security">
          <div class="permissions-grid">
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Executar SQL</span>
                <span class="switch-desc">Permissão geral para envio de comandos ao banco.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="new-perm-execute" checked><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Gravar no Banco</span>
                <span class="switch-desc">Permite INSERT, UPDATE e DELETE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="new-perm-write" checked><span class="toggle-track"></span></label>
            </div>
            <div class="switch-field">
              <div class="switch-label">
                <span class="switch-title">Pode Alterar Estrutura (DDL)</span>
                <span class="switch-desc">Permite ALTER, DROP, TRUNCATE e CREATE.</span>
              </div>
              <label class="toggle-switch"><input type="checkbox" id="new-perm-ddl"><span class="toggle-track"></span></label>
            </div>
          </div>
        </div>

        <!-- ABA: COMPORTAMENTO -->
        <div class="tab-pane" id="new-pane-behavior">
          <div class="form-group">
            <label class="form-label">LIMITE DE REGISTROS</label>
            <input id="new-beh-rows" type="number" class="form-input" value="500" />
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">ESTILO DE RESPOSTA</label>
            <select id="new-beh-style" class="form-input">
              <option value="technical" selected>Técnico / Direto</option>
              <option value="consultative">Consultivo / Explicativo</option>
              <option value="minimal">Minimalista (Só o Código)</option>
            </select>
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label">IDIOMA (RESPOSTA)</label>
            <input id="new-beh-lang" class="form-input" value="pt-BR" />
          </div>
          
          <div class="switch-field" style="margin-top:20px;">
            <div class="switch-label">
              <span class="switch-title">Auto-refinamento de Schema</span>
              <span class="switch-desc">Sempre revisar DDL (schema) antes de comandos não-descritivos.</span>
            </div>
            <label class="toggle-switch"><input type="checkbox" id="new-beh-intro" checked><span class="toggle-track"></span></label>
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

  if (modal && modal.el) {
    // Eventos das abas
    modal.el.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        modal.el.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
        modal.el.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        
        tab.classList.add('active');
        modal.el.querySelector('#new-pane-' + tab.dataset.tab).classList.add('active');
      });
    });
  }
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
