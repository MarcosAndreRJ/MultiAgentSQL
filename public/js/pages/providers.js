/**
 * providers.js — View de Gestão de Providers de LLM
 * CRUD completo: listar, criar, editar, excluir, testar conexão.
 *
 * @param {HTMLElement} container — #main-content
 * @returns {Function} teardown
 */

import { api }                from '../api.js';
import { createTable, badge, showLoading, showError, toast, el } from '../utils/dom.js';
import { openModal, confirmModal } from '../components/modal.js';
import { openRightPanel, closeRightPanel } from '../components/panel.js';
import { renderProviderType, renderStatusBadge, renderActionButtons } from '../utils/renderers.js';

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
      renderProviderType(p.type),
      el('span', { class: 'text-mono', style: 'font-size:11px;color:var(--ink-2)' }, p.base_url || '—'),
      renderStatusBadge(p.last_status || (p.is_active ? 'unknown' : 'offline')),
      renderActionButtons(p, {
        test: (item, btn) => testProvider(item, btn, refreshTable),
      edit: async (item) => {
        try {
          const detail = await api.getProvider(item.id);
          openProviderModal(detail.provider, refreshTable);
        } catch (err) {
          toast(`Erro ao carregar detalhes: ${err.message}`, 'danger');
        }
      },
      delete: (item) => deleteProvider(item, refreshTable)
      })
    ]);

      const table = createTable(['Nome', 'Tipo', 'Base URL', 'Status', 'Ações'], rows);
      wrap.innerHTML = '';
      wrap.appendChild(table);

    } catch (err) {
      showError(wrap, `Falha ao carregar providers: ${err.message}`);
    }
  }

  await refreshTable();

  return () => {}; // teardown
}

// ── Helpers ──────────────────────────────────────────────────────

async function testProvider(provider, btn, onDone) {
  const originalText = btn.textContent;
  btn.textContent = '...';
  btn.disabled = true;
  try {
    const result = await api.testProvider(provider.id);
    toast(result.details || result.message || 'Conexão OK!', result.status === 'ok' ? 'success' : 'danger');
    
    if (onDone) onDone();
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
  const types = ['openai', 'anthropic', 'gemini', 'ollama', 'custom', 'other'];

  openModal({
    title: isEdit ? `Editar Provider: ${provider.name}` : 'Novo Provider',
    body: `
      <div class="form-group">
        <label class="form-label">NOME</label>
        <input id="prov-name" class="form-input" value="${isEdit ? provider.name : ''}" placeholder="Ex: Local Ollama" required />
      </div>
      <div class="form-group">
        <label class="form-label">TIPO DE PROVIDER</label>
        <select id="prov-type" class="form-input">
          ${types.map(t => `<option value="${t}" ${isEdit && provider.type === t ? 'selected' : ''}>${t.toUpperCase()}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">BASE URL (OPCIONAL)</label>
        <input id="prov-url" class="form-input" value="${isEdit ? (provider.base_url || '') : ''}" placeholder="http://host.docker.internal:11434" />
      </div>
      <div class="form-group">
        <label class="form-label">API KEY (OPCIONAL)</label>
        <div class="input-group">
          <input id="prov-key" class="form-input" type="password" 
                 value="${isEdit ? (provider.api_key || '') : ''}" 
                 placeholder="${isEdit && !provider.api_key ? '•••••••• (Inalterada se vazio)' : 'sk-...'}" />
          <button type="button" class="btn-toggle-password" id="btn-toggle-prov-key" title="Mostrar/Ocultar Chave">
            <span class="icon-eye">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </span>
          </button>
        </div>
        <small class="text-muted" style="font-size:10px">A chave é armazenada de forma segura e nunca exposta na UI.</small>
      </div>
    `,
    actions: [
      { label: 'Cancelar', type: 'ghost', onClick: (close) => close() },
      {
        label: isEdit ? 'Salvar' : 'Criar',
        type: 'primary',
        onClick: async (close) => {
          const name = document.getElementById('prov-name')?.value.trim();
          const type = document.getElementById('prov-type')?.value;
          const base_url = document.getElementById('prov-url')?.value.trim();
          const api_key = document.getElementById('prov-key')?.value.trim();
          
          if (!name) return;

          // Validação client-side para custom
          if (type === 'custom' && !base_url) {
            toast('Erro: Base URL é obrigatória para o tipo CUSTOM', 'danger');
            return;
          }

          const payload = { 
            name, 
            type: type, 
            base_url: base_url || null, 
            api_key: api_key || null 
          };

          try {
            if (isEdit) {
              await api.updateProvider(provider.id, payload);
              toast('Provider atualizado!', 'success');
            } else {
              await api.createProvider(payload);
              toast('Provider criado!', 'success');
            }
            close();
            if (onSave) onSave();
          } catch (err) {
            // Se o backend retornou 422, a mensagem amigável estará em err.message (via api.js)
            const detail = err.message || 'Erro desconhecido';
            toast(`Falha na validação: ${detail}`, 'danger');
            console.error('[Providers] Erro no salvamento:', err);
          }
        },
      },
    ],
  });

  // Lógica de toggle da senha (Eye Button)
  const toggleBtn = document.getElementById('btn-toggle-prov-key');
  const keyInput = document.getElementById('prov-key');
  const iconSpan = toggleBtn?.querySelector('.icon-eye');

  const ICON_EYE = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
  const ICON_EYE_SLASH = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

  if (toggleBtn && keyInput) {
    toggleBtn.addEventListener('click', (e) => {
      e.preventDefault(); // Garante que não submeta (embora type="button" já faça isso)
      const isPassword = keyInput.type === 'password';
      keyInput.type = isPassword ? 'text' : 'password';
      iconSpan.innerHTML = isPassword ? ICON_EYE_SLASH : ICON_EYE;
    });
  }
}
