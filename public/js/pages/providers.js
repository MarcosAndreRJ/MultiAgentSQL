/**
 * providers.js — View de Gestão de Providers de LLM
 * CRUD completo: listar, criar, editar, excluir, testar conexão.
 *
 * @param {HTMLElement} container — #main-content
 * @returns {Function} teardown
 */

import { api }                from '../api.js';
import { createTable, badge, showLoading, showError, toast } from '../utils/dom.js';
import { openModal, confirmModal } from '../components/modal.js';
import { openRightPanel, closeRightPanel } from '../components/panel.js';

export async function renderProvidersPage(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <div class="page-title"><span class="page-icon">🔌</span> Gestão de Providers</div>
        <div class="page-subtitle">Gerencie as conexões com provedores de LLM</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" id="btn-new-provider">+ Novo Provider</button>
      </div>
    </div>
    <div class="page-body">
      <div class="card">
        <div class="card-header">
          <span>Providers Configurados</span>
          <span id="prov-count" class="text-muted"></span>
        </div>
        <div id="providers-table-wrap"></div>
      </div>
    </div>
  `;

  container.querySelector('#btn-new-provider').addEventListener('click', () => openProviderModal(null, refreshTable));

  const wrap = container.querySelector('#providers-table-wrap');
  const countEl = container.querySelector('#prov-count');

  async function refreshTable() {
    showLoading(wrap, 'Carregando providers...');
    try {
      const data = await api.getProviders();
      const providers = data.providers || [];
      countEl.textContent = `${providers.length} provider(s)`;

      if (providers.length === 0) {
        wrap.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">🔌</div>
            <div class="empty-state-title">Nenhum provider configurado</div>
            <div class="empty-state-sub">Clique em "+ Novo Provider" para adicionar.</div>
          </div>
        `;
        return;
      }

      const rows = providers.map(p => [
        p.name,
        `<span class="text-mono" style="font-size:11px;color:var(--ink-2)">${p.baseUrl || '—'}</span>`,
        buildStatusBadge(p.status),
        buildActionsCell(p, refreshTable),
      ]);

      const table = createTable(['Nome', 'Base URL', 'Status', 'Ações'], rows);
      wrap.innerHTML = '';
      wrap.appendChild(table);

      // Bind de botões de ação
      wrap.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
          const { action, id } = btn.dataset;
          const provider = providers.find(p => String(p.id) === id);
          if (!provider) return;
          if (action === 'test') testProvider(provider, btn);
          if (action === 'edit') openProviderModal(provider, refreshTable);
          if (action === 'delete') deleteProvider(provider, refreshTable);
        });
      });

    } catch (err) {
      showError(wrap, `Falha ao carregar providers: ${err.message}`);
    }
  }

  await refreshTable();

  return () => {}; // teardown
}

// ── Helpers ──────────────────────────────────────────────────────
function buildStatusBadge(status) {
  const map = {
    ok:      'success',
    healthy: 'success',
    error:   'danger',
    fail:    'danger',
    unknown: 'muted',
  };
  const type = map[String(status || '').toLowerCase()] || 'muted';
  const label = status ? String(status).toUpperCase() : 'DESCONHECIDO';
  return `<span class="badge badge-${type}">${label}</span>`;
}

function buildActionsCell(p, refresh) {
  return `
    <div class="col-actions">
      <button class="btn btn-sm btn-secondary" data-action="test" data-id="${p.id}">Testar</button>
      <button class="btn btn-sm btn-secondary" data-action="edit" data-id="${p.id}">Editar</button>
      <button class="btn btn-sm btn-danger" data-action="delete" data-id="${p.id}">Excluir</button>
    </div>
  `;
}

async function testProvider(provider, btn) {
  const originalText = btn.textContent;
  btn.textContent = 'Testando...';
  btn.disabled = true;
  try {
    const result = await api.testProvider(provider.id);
    toast(result.message || 'Conexão OK!', result.ok ? 'success' : 'danger');
  } catch (err) {
    toast(`Falha: ${err.message}`, 'danger');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

async function deleteProvider(provider, refresh) {
  confirmModal({
    title: 'Excluir Provider',
    message: `Excluir o provider <strong>${provider.name}</strong>? Esta ação não pode ser desfeita.`,
    confirmLabel: 'Excluir',
    danger: true,
    onConfirm: async () => {
      try {
        await api.deleteProvider(provider.id);
        toast(`Provider "${provider.name}" excluído`, 'info');
        await refresh();
      } catch (err) {
        toast(`Erro: ${err.message}`, 'danger');
      }
    },
  });
}

function openProviderModal(provider, onSave) {
  const isEdit = !!provider;
  openModal({
    title: isEdit ? `Editar Provider: ${provider.name}` : 'Novo Provider',
    body: `
      <div class="form-group">
        <label class="form-label">NOME</label>
        <input id="prov-name" class="form-input" value="${isEdit ? provider.name : ''}" placeholder="Ex: Local Ollama" required />
      </div>
      <div class="form-group">
        <label class="form-label">BASE URL</label>
        <input id="prov-url" class="form-input" value="${isEdit ? (provider.baseUrl || '') : ''}" placeholder="http://host.docker.internal:11434" />
      </div>
      <div class="form-group">
        <label class="form-label">API KEY (OPCIONAL)</label>
        <input id="prov-key" class="form-input" type="password" value="${isEdit ? (provider.apiKey || '') : ''}" placeholder="sk-..." />
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: isEdit ? 'Salvar' : 'Criar',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('prov-name')?.value.trim();
          const baseUrl = document.getElementById('prov-url')?.value.trim();
          const apiKey = document.getElementById('prov-key')?.value.trim();
          if (!name) return;
          try {
            if (isEdit) {
              await api.updateProvider(provider.id, { name, baseUrl, apiKey });
              toast('Provider atualizado!', 'success');
            } else {
              await api.createProvider({ name, baseUrl, apiKey });
              toast('Provider criado!', 'success');
            }
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
