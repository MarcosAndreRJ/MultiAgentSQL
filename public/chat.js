function chatApp() {
  return {
    sessionId: '',
    input: '',
    thinking: false,
    connected: false,
    stream: null,
    copiedId: null,
    agents: [],
    activeAgent: 'main',
    currentAgentName: 'Principal',
    currentMessages: [],
    showNewAgent: false,
    showSkillsModal: false,
    newAgentName: '',
    newAgentPrompt: '',
    newAgentLlmModel: '',
    newAgentFiles: [],
    skills: [],
    assignedSkillsCurrentAgent: [],
    selectedSkillName: '',
    newSkillName: '',
    newSkillContent: '',
    chatFiles: [],
    messagesByAgent: {},
    loadedHistoryByAgent: {},
    thinkingAgents: {},
    showRightPanel: false,
    rightPanelMode: 'config',
    editAgentData: null,
    editAgentSaving: false,
    cfg: {
      ollamaProvider: 'ollama',
      ollamaBaseUrl: '',
      ollamaModel: '',
      telegramBotToken: '',
      telegramAllowedUser: '',
      enableTelegram: true,
      enableWebChat: true,
      showThoughtFlow: true,
      typewriterEffect: true
    },
    cfgSaving: false,
    cfgSaved: false,

    init() {
      this.sessionId = localStorage.getItem('aa-session');
      if (!this.sessionId) {
        this.sessionId = (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : 'sess-' + Math.random().toString(36).slice(2);
        localStorage.setItem('aa-session', this.sessionId);
      }
      this.loadAgents().then(() => {
        this.loadConfig();
        this.loadSkills();
        this.connectSSE();
      });
      this.$watch('showNewAgent', (val) => {
        if (val) {
          this.$nextTick(() => {
            const el = document.querySelector('.modal-body input');
            if (el) el.focus();
          });
        }
      });
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = document.getElementById('messages');
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    connectSSE() {
      // Desativado: substituído por lógica REST conforme solicitação.
      this.connected = true;
      console.log("[Client] Conectado temporariamente via REST mode.");
    },

    pushMessage(agentId, role, text, rawAgentName, modelUsed, steps = null) {
      if (!this.messagesByAgent[agentId]) this.messagesByAgent[agentId] = [];
      const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      this.messagesByAgent[agentId].push({ 
        id: Math.random().toString(36).slice(2), 
        role, 
        text, 
        time, 
        isDone: true, 
        agentName: rawAgentName, 
        modelUsed: modelUsed || null,
        steps: steps // Adicionado suporte a steps visuais
      });
      if (agentId === this.activeAgent) {
        this.currentMessages = this.messagesByAgent[agentId].slice();
        this.scrollToBottom();
      }
    },

    send() {
      const text = this.input.trim();
      if (!text && this.chatFiles.length === 0) return;
      if (this.thinking) return;

      this.input = ''; 

      if (text.startsWith('/')) {
        this.sendCommand(text);
        this.chatFiles = [];
        return;
      }

      this.thinking = true;
      const agentId = this.activeAgent;
      
      // Salva mensagem do usuário
      this.pushMessage(agentId, 'user', text, 'Você', null);
      this.thinkingAgents[agentId] = true;

      // 1. Renderiza o bloco do Planner em formato de "step"
      const plannerMsgId = Math.random().toString(36).slice(2);
      if (!this.messagesByAgent[agentId]) this.messagesByAgent[agentId] = [];
      const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      
      if (this.cfg.showThoughtFlow) {
        this.messagesByAgent[agentId].push({
          id: plannerMsgId,
          role: 'step',
          text: '',
          time: time,
          isDone: false,
          open: false,
          stepInfo: { status: 'loading', title: '🧠 PlannerAgent analisando o contexto...' }
        });
        this.currentMessages = this.messagesByAgent[agentId].slice();
        this.scrollToBottom();
      }

      const payload = {
        message: text,
        conversation_id: this.sessionId,
        agent_id: this.activeAgent
      };
      
      console.log("[CHAT] Payload enviado:", payload);

      fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }).then(async r => {
        if (!r.ok) {
           const errText = await r.text();
           console.error("[CHAT] Erro HTTP:", r.status, errText);
           throw new Error(`HTTP ${r.status}`);
        }
        return r.json();
      }).then(data => {
        console.log("[CHAT] Resposta recebida:", data);
        
        if (!data || typeof data !== 'object') {
           throw new Error("Resposta da API em formato inválido.");
        }
        
        if (!this.cfg.showThoughtFlow) {
           this.pushMessage(agentId, 'assistant', data.response || "Sem resposta.", this.currentAgentName, data.model_used || this.cfg.ollamaModel);
           this.thinking = false;
           this.thinkingAgents[agentId] = false;
           return;
        }

        try {
            // 2. Preenche o Planner (que estava carregando)
            const plannerMsg = this.messagesByAgent[agentId].find(m => m.id === plannerMsgId);
            if (plannerMsg) {
                plannerMsg.text = data.planner || 'Sem plano gerado.';
                plannerMsg.stepInfo.status = data.planner ? 'done' : 'error';
                plannerMsg.stepInfo.title = '🧠 Planejamento concluído';
                plannerMsg.isDone = true;
            }
            this.currentMessages = this.messagesByAgent[agentId].slice();
            this.scrollToBottom();
            
            // 3. Renderiza Specialist em "loading"
            const specMsgId = Math.random().toString(36).slice(2);
            this.messagesByAgent[agentId].push({
                id: specMsgId,
                role: 'step',
                text: '',
                time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
                isDone: false,
                open: false,
                stepInfo: { status: 'loading', title: `⚙️ ${data.selected_specialist || 'SpecialistAgent'} elaborando resposta...` }
            });
            this.currentMessages = this.messagesByAgent[agentId].slice();
            this.scrollToBottom();
            
            setTimeout(() => {
              try {
                // 4. Preenche Specialist
                const specMsg = this.messagesByAgent[agentId].find(m => m.id === specMsgId);
                if (specMsg) {
                    specMsg.text = data.specialist || 'Sem resposta do especialista.';
                    specMsg.stepInfo.status = 'done';
                    specMsg.stepInfo.title = `⚙️ ${data.selected_specialist || 'SpecialistAgent'} finalizou a análise`;
                    specMsg.isDone = true;
                }
                this.currentMessages = this.messagesByAgent[agentId].slice();
                this.scrollToBottom();
                
                // 5. Renderiza Reviewer em "loading"
                const revMsgId = Math.random().toString(36).slice(2);
                this.messagesByAgent[agentId].push({
                    id: revMsgId,
                    role: 'step',
                    text: '',
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
                    isDone: false,
                    open: false,
                    stepInfo: { status: 'loading', title: '🔍 ReviewerAgent processando revisão...' }
                });
                this.currentMessages = this.messagesByAgent[agentId].slice();
                this.scrollToBottom();
                
                setTimeout(() => {
                  try {
                    // 6. Preenche Reviewer
                    const revMsg = this.messagesByAgent[agentId].find(m => m.id === revMsgId);
                    if (revMsg) {
                        revMsg.text = data.reviewer || 'Sem revisão.';
                        revMsg.stepInfo.status = 'done';
                        revMsg.stepInfo.title = '🔍 Revisão concluída';
                        revMsg.isDone = true;
                    }
                    this.currentMessages = this.messagesByAgent[agentId].slice();
                    this.scrollToBottom();
                    
                    // 7. Renderiza resposta final
                    setTimeout(() => {
                        this.pushMessage(agentId, 'assistant', data.response || "Sem resposta.", this.currentAgentName, data.model_used || this.cfg.ollamaModel);
                        this.thinking = false;
                        this.thinkingAgents[agentId] = false;
                    }, 400);
                  } catch (e) {
                      console.error("[CHAT] Erro ao renderizar Reviewer/Final:", e);
                      this.thinking = false;
                      this.thinkingAgents[agentId] = false;
                  }
                }, 600);
              } catch (e) {
                  console.error("[CHAT] Erro ao renderizar Specialist:", e);
                  this.thinking = false;
                  this.thinkingAgents[agentId] = false;
              }
            }, 600);
        } catch (e) {
            console.error("[CHAT] Erro no fluxo de steps:", e);
            this.thinking = false;
            this.thinkingAgents[agentId] = false;
        }
        
      }).catch((err) => {
        console.error("[CHAT] Erro no Fetch/JSON:", err);
        this.thinking = false;
        this.thinkingAgents[agentId] = false;
        
        if (this.cfg.showThoughtFlow) {
            const plannerMsg = this.messagesByAgent[agentId].find(m => m.id === plannerMsgId);
            if (plannerMsg) {
               plannerMsg.text = 'Ocorreu um erro na requisição: ' + err.message;
               plannerMsg.stepInfo.status = 'error';
               plannerMsg.stepInfo.title = '🧠 Erro no Planner';
               plannerMsg.isDone = true;
            }
        }
        this.pushMessage(agentId, 'assistant', 'Erro ao processar a resposta do servidor.', this.currentAgentName);
        this.currentMessages = this.messagesByAgent[agentId].slice();
        this.scrollToBottom();
      });
    },

    sendCommand(cmd) {
      if (cmd === '/stop' || cmd === '/reset') {
        this.thinking = false;
        this.thinkingAgents[this.activeAgent] = false;
      }
      
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: cmd, conversation_id: this.sessionId, agent_id: this.activeAgent })
      }).then(r => r.json()).then(data => {
        if (!data.response) this.pushMessage(this.activeAgent, 'system', 'Erro ao executar comando.');
        else this.pushMessage(this.activeAgent, 'system', data.response);
        
        if (cmd === '/reset') {
          delete this.messagesByAgent[this.activeAgent];
          delete this.loadedHistoryByAgent[this.activeAgent];
          this.currentMessages = [];
          this.thinking = false;
          this.thinkingAgents[this.activeAgent] = false;
        }
        
      }).catch(() => {
          this.pushMessage(this.activeAgent, 'system', 'Erro ao executar comando.')
          this.thinking = false;
          this.thinkingAgents[this.activeAgent] = false;
      });
    },

    loadAgents() {
      return fetch('/api/agents').then(r => r.json()).then(d => {
        this.agents = d.agents || [{ id: 'main', name: 'Principal', description: '' }];
        this.agents.forEach(ag => { if (!this.messagesByAgent[ag.id]) this.messagesByAgent[ag.id] = []; });
        this.updateCurrentAgent();
      }).catch(() => { this.agents = [{ id: 'main', name: 'Principal', description: '' }]; this.updateCurrentAgent(); });
    },

    loadSkills() {
      return fetch('/api/skills').then(r => r.json()).then(d => {
        this.skills = d.skills || [];
      }).catch(() => { this.skills = []; });
    },

    openSkillsModal() {
      this.showSkillsModal = true;
      this.loadSkills();
      this.loadAssignedSkillsCurrentAgent();
    },

    selectSkill(skillName) { this.selectedSkillName = skillName; },

    editSkill(skillName) {
      this.selectedSkillName = skillName;
      fetch(`/api/skills/${encodeURIComponent(skillName)}`)
        .then(r => r.json())
        .then(d => {
          if (!d.ok || !d.skill) return;
          this.newSkillName = d.skill.name;
          this.newSkillContent = d.skill.content || '';
        }).catch(() => {});
    },

    deleteSkill(skillName) {
      if (!skillName) return;
      if (!confirm(`Excluir skill '${skillName}'?`)) return;
      fetch(`/api/skills/${encodeURIComponent(skillName)}`, { method: 'DELETE' }).then(r => r.json()).then(d => {
        if (!d.ok) return;
        if (this.selectedSkillName === skillName) this.selectedSkillName = '';
        if (this.newSkillName === skillName) { this.newSkillName = ''; this.newSkillContent = ''; }
        this.loadSkills();
        this.loadAssignedSkillsCurrentAgent();
      }).catch(() => {});
    },

    loadAssignedSkillsCurrentAgent() {
      if (!this.activeAgent) return;
      fetch(`/api/agents/${this.activeAgent}/skills`).then(r => r.json()).then(d => {
        this.assignedSkillsCurrentAgent = d.skills || [];
      }).catch(() => { this.assignedSkillsCurrentAgent = []; });
    },

    createSkillFromModal() {
      const name = (this.newSkillName || '').trim();
      const content = (this.newSkillContent || '').trim();
      if (!name || !content) return;
      fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, content })
      }).then(r => r.json()).then(d => {
        if (!d.ok) return;
        this.newSkillName = ''; this.newSkillContent = '';
        this.selectedSkillName = d.skill?.name || name;
        this.loadSkills();
      }).catch(() => {});
    },

    assignSelectedSkillToCurrentAgent() {
      if (!this.selectedSkillName || !this.activeAgent) return;
      fetch(`/api/agents/${this.activeAgent}/skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skillName: this.selectedSkillName })
      }).then(r => r.json()).then(d => {
        if (!d.ok) return;
        this.loadAssignedSkillsCurrentAgent();
      }).catch(() => {});
    },

    removeSkillFromCurrentAgent(skillName) {
      if (!this.activeAgent || !skillName) return;
      fetch(`/api/agents/${this.activeAgent}/skills/${encodeURIComponent(skillName)}`, { method: 'DELETE' })
      .then(r => r.json()).then(d => {
        if (!d.ok) return;
        this.loadAssignedSkillsCurrentAgent();
      }).catch(() => {});
    },

    createAgent() {
      const name = this.newAgentName.trim();
      if (!name) return;
      
      const payload = {
        name: this.newAgentName,
        description: this.newAgentPrompt,
        model: this.newAgentLlmModel || "llama3",
        type: "mysql-specialist",
        prompt_file: "base.txt",
        database: null
      };

      fetch('/api/agents', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(r => r.json()).then(d => {
        if (d.ok) {
          this.agents.push(d.agent);
          this.messagesByAgent[d.agent.id] = [];
          this.switchAgent(d.agent.id);
          this.showNewAgent = false;
          this.newAgentName = ''; this.newAgentPrompt = ''; this.newAgentLlmModel = ''; this.newAgentFiles = [];
        }
      }).catch(() => { });
    },

    switchAgent(id) {
      this.activeAgent = id;
      this.thinking = !!this.thinkingAgents[id];
      this.updateCurrentAgent();
      this.loadChatHistory(id);
      if (this.showSkillsModal) this.loadAssignedSkillsCurrentAgent();
    },

    loadChatHistory(agentId) {
      if (this.loadedHistoryByAgent[agentId]) {
        this.currentMessages = (this.messagesByAgent[agentId] || []).slice();
        this.scrollToBottom();
        return;
      }
      fetch(`/api/chat/history/${this.sessionId}/${agentId}`).then(r => r.json()).then(d => {
        if (d.ok && d.messages) {
          const serverMessages = d.messages.map(m => ({
            id: Math.random().toString(36).slice(2),
            role: m.role, text: m.content,
            time: new Date(m.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
            isDone: true, agentName: m.agentName, modelUsed: m.modelUsed || null
          }));
          const localMessages = this.messagesByAgent[agentId] || [];
          const merged = [...serverMessages];
          for (const msg of localMessages) {
            const exists = merged.some(s => s.role === msg.role && s.text === msg.text && s.time === msg.time);
            if (!exists) merged.push(msg);
          }
          this.messagesByAgent[agentId] = merged;
          this.loadedHistoryByAgent[agentId] = true;
          if (agentId === this.activeAgent) {
            this.currentMessages = this.messagesByAgent[agentId].slice();
            this.scrollToBottom();
          }
        }
      }).catch(() => { });
    },

    updateCurrentAgent() {
      const ag = this.agents.find(a => a.id === this.activeAgent);
      this.currentAgentName = ag ? ag.name : 'Agent';
      this.currentMessages = (this.messagesByAgent[this.activeAgent] || []).slice();
    },

    openAgentDetails(ag) {
      this.editAgentData = { id: ag.id, name: ag.name, description: ag.description, llmModel: ag.llmModel || '' };
      this.rightPanelMode = 'agentDetails';
      this.showRightPanel = true;
    },

    openCurrentAgentDetails() {
      const ag = this.agents.find(a => a.id === this.activeAgent);
      if (ag) this.openAgentDetails(ag);
    },

    saveAgentDetails() {
      if (!this.editAgentData) return;
      this.editAgentSaving = true;
      fetch('/api/agents/' + this.editAgentData.id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: this.editAgentData.name, description: this.editAgentData.description, llmModel: this.editAgentData.llmModel
        })
      }).then(r => r.json()).then(d => {
        if (d.ok) {
          const ag = this.agents.find(a => a.id === this.editAgentData.id);
          if (ag) {
            ag.name = this.editAgentData.name; ag.description = this.editAgentData.description; ag.llmModel = this.editAgentData.llmModel;
            if (this.activeAgent === ag.id) this.updateCurrentAgent();
          }
        }
      }).catch(() => { }).finally(() => { this.editAgentSaving = false; });
    },

    toggleConfigPanel() {
      if (this.showRightPanel && this.rightPanelMode === 'config') this.showRightPanel = false;
      else { this.rightPanelMode = 'config'; this.showRightPanel = true; }
    },

    deleteAgent(agentId) {
      if (agentId === 'main') return;
      if (!confirm('Excluir agente ' + agentId + '?')) return;
      fetch('/api/agents/' + agentId, { method: 'DELETE' }).catch(() => { });
      this.agents = this.agents.filter(a => a.id !== agentId);
      delete this.messagesByAgent[agentId];
      if (this.activeAgent === agentId) this.switchAgent('main');
    },

    loadConfig() {
      return fetch('/api/config').then(r => r.json()).then(d => {
        if (d.ok) {
          this.cfg.ollamaProvider = d.config.ollamaProvider || 'ollama';
          this.cfg.ollamaBaseUrl = d.config.ollamaBaseUrl;
          this.cfg.ollamaModel = d.config.ollamaModel;
          this.cfg.telegramAllowedUser = d.config.telegramAllowedUser || '';
          this.cfg.enableTelegram = d.config.enableTelegram;
          this.cfg.enableWebChat = d.config.enableWebChat;
          this.cfg.showThoughtFlow = d.config.showThoughtFlow !== false;
          this.cfg.typewriterEffect = d.config.typewriterEffect !== false;
        }
      }).catch(() => { });
    },

    saveConfig() {
      this.cfgSaving = true;
      this.cfgSaved = false;
      fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.cfg)
      }).then(r => r.json()).then(res => {
        if (res.ok) { this.cfgSaved = true; setTimeout(() => { this.cfgSaved = false; }, 2000); }
      }).catch(() => { }).finally(() => { this.cfgSaving = false; });
    },

    copyMessage(text, id) {
      navigator.clipboard.writeText(text).then(() => {
        this.copiedId = id; setTimeout(() => { this.copiedId = null; }, 2000);
      });
    },

    autoResize(event) {
      const el = event.target;
      el.style.height = 'auto';
      el.style.height = el.scrollHeight + 'px';
    },

    renderMd(text) {
      if (!text) return '';
      try { return window.marked.parse(text); } catch(e) { return text; }
    }
  }
}
window.chatApp = chatApp;
