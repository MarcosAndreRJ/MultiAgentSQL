// ═══════════════════════════════════════════════════════════════════════════════
//  MultiAgent SQL — ERD Viewer  (diagram.js)
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Estado global ─────────────────────────────────────────────────────────────
const state = {
  agentId: null,
  payload: null,
  network: null,
  nodesDataSet: null,
  edgesDataSet: null,
  allNodes: [],       
  allEdges: [],       
  selectedNodeIds: [], 
  selectedFrameId: null, 
  frames: [],          
  collapsedNodes: new Set(),
  relayoutSeed: 7,
  digestVersion: null, 
  visibleTypes: new Set(["table", "view", "draft"]), 
  generatedDDL: null,   
  draftTableName: null, 
  isDraggingFrame: false,
  isResizingFrame: false,
  dragStartPos: null,
  frameHandleSize: 12,
};

// ─── Inicialização ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  state.agentId = getAgentIdFromPath();
  bindUiEvents();
  bootstrapDiagram();
});

function getAgentIdFromPath() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (parts.length < 2) return null;
  return decodeURIComponent(parts[1]);
}

function bindUiEvents() {
  document.getElementById("btn-back").addEventListener("click", () => {
    window.location.href = "/";
  });

  document.getElementById("btn-search").addEventListener("click", searchTable);
  document.getElementById("search-table").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchTable();
    }
  });

  document.getElementById("btn-clear-selection").addEventListener("click", () => {
    state.selectedNodeIds = [];
    state.selectedFrameId = null;
    if (state.network) state.network.unselectAll();
    updateSelectedPanel();
    applyVisibilityAndHighlight();
  });

  document.getElementById("btn-zoom-in").addEventListener("click", () => changeZoom(1.12));
  document.getElementById("btn-zoom-out").addEventListener("click", () => changeZoom(0.88));
  document.getElementById("btn-fit").addEventListener("click", fitGraph);
  document.getElementById("btn-relayout").addEventListener("click", relayoutGraph);
  document.getElementById("btn-center").addEventListener("click", centerSelectedNode);

  document.getElementById("toggle-related-only").addEventListener("change", applyVisibilityAndHighlight);
  document.getElementById("toggle-hide-isolated").addEventListener("change", applyVisibilityAndHighlight);

  // Filtros de tipo na legenda
  document.getElementById("toggle-show-tables").addEventListener("change", (e) => {
    if (e.target.checked) state.visibleTypes.add("table");
    else state.visibleTypes.delete("table");
    applyVisibilityAndHighlight();
  });
  document.getElementById("toggle-show-views").addEventListener("change", (e) => {
    if (e.target.checked) state.visibleTypes.add("view");
    else state.visibleTypes.delete("view");
    applyVisibilityAndHighlight();
  });
  document.getElementById("toggle-show-drafts").addEventListener("change", (e) => {
    if (e.target.checked) state.visibleTypes.add("draft");
    else state.visibleTypes.delete("draft");
    applyVisibilityAndHighlight();
  });

  // Modal Nova Tabela
  document.getElementById("btn-new-table").addEventListener("click", openNewTableModal);
  document.getElementById("btn-modal-close").addEventListener("click", closeNewTableModal);
  document.getElementById("modal-new-table").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeNewTableModal();
  });
  document.getElementById("btn-add-column").addEventListener("click", addColumnRow);
  document.getElementById("btn-add-to-erd").addEventListener("click", createTableInERDOnly);
  document.getElementById("btn-generate-sql").addEventListener("click", generateCreateTableSQL);
  document.getElementById("btn-execute-ddl").addEventListener("click", executeCreateTableDDL);

  // Modal Moldura
  document.getElementById("btn-new-frame").addEventListener("click", openFrameModalForNew);
  document.getElementById("btn-frame-modal-close").addEventListener("click", closeFrameModal);
  document.getElementById("btn-save-frame").addEventListener("click", saveFrameFromModal);
  document.getElementById("btn-delete-frame").addEventListener("click", deleteSelectedFrame);
  document.getElementById("modal-frame").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeFrameModal();
  });
}

async function bootstrapDiagram() {
  if (!state.agentId) {
    setStatus("Agente invalido para visualizacao do diagrama.", "error");
    return;
  }

  if (!window.vis || !window.vis.Network) {
    setStatus("Biblioteca de grafo indisponivel no navegador.", "error");
    return;
  }

  try {
    const statusRes = await fetch(`/api/diagram/${encodeURIComponent(state.agentId)}/status`);
    if (!statusRes.ok) {
      setStatus("Nao foi possivel validar o digest deste agente.", "error");
      return;
    }

    const status = await statusRes.json();
    if (!status.exists) {
      setStatus("Digest nao encontrado. Gere o digest antes de visualizar a estrutura.", "warn");
      return;
    }
    if (!status.valid) {
      setStatus(status.message || "Digest invalido para visualizacao.", "error");
      return;
    }

    const res = await fetch(`/api/diagram/${encodeURIComponent(state.agentId)}`);
    if (!res.ok) {
      const err = await safeJson(res);
      setStatus(err?.detail || "Falha ao carregar diagrama.", "error");
      return;
    }

    state.payload = await res.json();
    // Chave de versão para invalidação de layout salvo
    state.digestVersion = state.payload.generated_at || "unknown";

    renderMetadata();
    initializeNetwork();
    setStatus(
      state.payload.summary.edges > 0
        ? `Diagrama carregado — ${state.payload.summary.nodes} objetos, ${state.payload.summary.edges} relacionamentos.`
        : `Diagrama carregado — ${state.payload.summary.nodes} objetos (sem FKs detectadas no digest).`,
      "ok"
    );
  } catch (err) {
    setStatus("Erro de rede ao carregar diagrama.", "error");
    console.error("[ERD] bootstrapDiagram:", err);
  }
}

function renderMetadata() {
  const payload = state.payload;
  const generated = payload.generated_at
    ? new Date(payload.generated_at).toLocaleString("pt-BR")
    : "-";

  document.getElementById("meta-agent").textContent = `Agente: ${payload.agent_name || payload.agent_id}`;
  document.getElementById("meta-db").textContent = `Database: ${payload.database || "-"}`;
  document.getElementById("meta-generated").textContent = `Digest: ${generated}`;
  const draftLine = (payload.summary.drafts || 0) > 0
    ? `<div>${payload.summary.drafts} rascunho(s) ERD</div>`
    : "";
  document.getElementById("diagram-summary").innerHTML =
    `<div>${payload.summary.tables} tabelas</div>` +
    `<div>${payload.summary.views} views</div>` +
    draftLine +
    `<div>${payload.summary.nodes} objetos</div>` +
    `<div>${payload.summary.edges} relacionamentos (FK)</div>`;
}

function initializeNetwork() {
  const canvas = document.getElementById("diagram-canvas");
  const payload = state.payload;

  // Carregar posições salvas (se existirem e digest não mudou)
  const savedData = loadLayoutData();
  const hasPositions = savedData && savedData.positions;
  
  if (savedData && savedData.frames) {
    state.frames = savedData.frames;
  }

  state.allNodes = payload.nodes.map((node) => {
    const pos = hasPositions ? savedData.positions[node.id] : null;
    const base = buildNodeDefinition(node);
    if (pos) {
      base.x = pos.x;
      base.y = pos.y;
    }
    return base;
  });

  state.allEdges = payload.edges.map((edge) => buildEdgeDefinition(edge));

  state.nodesDataSet = new vis.DataSet(state.allNodes);
  state.edgesDataSet = new vis.DataSet(state.allEdges);

  // Se já há posições salvas, desativa física de imediato — nenhum nó deve se
  // mover ao abrir o diagrama. Se não há posições, deixa barnesHut organizar.
  const physicsOpts = hasPositions ? { enabled: false } : makePhysicsOptions(false);

  state.network = new vis.Network(
    canvas,
    { nodes: state.nodesDataSet, edges: state.edgesDataSet },
    {
      autoResize: true,
      layout: {
        improvedLayout: false,  // desativado: usamos barnesHut + avoidOverlap
        randomSeed: state.relayoutSeed,
      },
      interaction: {
        hover: true,
        dragNodes: true,
        dragView: true,
        zoomView: true,
        multiselect: true, // Habilitar multi-select nativo
        navigationButtons: false,
        keyboard: { enabled: true, speed: { x: 10, y: 10, zoom: 0.02 } },
        tooltipDelay: 150,
      },
      physics: physicsOpts,
      edges: {
        smooth: {
          enabled: true,
          type: "continuous",
          roundness: 0.25,
        },
        color: {
          inherit: false,
        },
      },
      nodes: {
        // defaults aplicados via buildNodeDefinition
      },
    }
  );

  const _readyMsg =
    payload.summary.edges > 0
      ? `Diagrama pronto — ${payload.summary.nodes} objetos, ${payload.summary.edges} relacionamentos.`
      : `Diagrama pronto — ${payload.summary.nodes} objetos (sem FKs detectadas no digest).`;

  if (hasPositions) {
    // Posições já conhecidas → mostrar imediatamente, sem física
    fitGraph();
    setStatus(_readyMsg, "ok");
  } else {
    // Primeira vez (sem layout salvo) → aguardar estabilização barnesHut
    state.network.once("stabilized", () => {
      state.network.setOptions({ physics: { enabled: false } });
      fitGraph();
      saveLayoutPositions();
      setStatus(_readyMsg, "ok");
    });
  }

  // Salvar posições ao terminar de arrastar um nó
  state.network.on("dragEnd", ({ nodes }) => {
    if (nodes && nodes.length > 0) {
      saveLayoutPositions();
    }
  });

  // Eventos de seleção unificados
  state.network.on("select", ({ nodes }) => {
    state.selectedNodeIds = nodes || [];
    state.selectedFrameId = null; // desmarcar frame ao selecionar nós
    updateSelectedPanel();
    applyVisibilityAndHighlight();
  });

  state.network.on("deselectNode", ({ nodes }) => {
    state.selectedNodeIds = nodes || [];
    updateSelectedPanel();
    applyVisibilityAndHighlight();
  });

  // Evento de clique no background para hit-test de frames
  state.network.on("click", (params) => {
    if (params.nodes.length === 0) {
      // Clicou no vazio -> verificar se clicou em um frame
      const canvasPos = params.pointer.canvas;
      const hitFrame = findFrameAt(canvasPos.x, canvasPos.y);
      if (hitFrame) {
        state.selectedFrameId = hitFrame.id;
        state.selectedNodeIds = [];
        state.network.unselectAll();
      } else {
        state.selectedFrameId = null;
      }
      updateSelectedPanel();
      applyVisibilityAndHighlight();
    }
  });

  // Evento de Double Click no frame para editar
  state.network.on("doubleClick", (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      if (state.collapsedNodes.has(nodeId)) {
        state.collapsedNodes.delete(nodeId);
      } else {
        state.collapsedNodes.add(nodeId);
      }
      applyVisibilityAndHighlight();
    } else {
      const canvasPos = params.pointer.canvas;
      const hitFrame = findFrameAt(canvasPos.x, canvasPos.y);
      if (hitFrame) {
        openFrameModalForEdit(hitFrame);
      }
    }
  });

  // Lógica manual de drag de frames com eventos DOM e conversão de coordenadas
  const canvasEl = document.getElementById("diagram-canvas");

  canvasEl.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return; // Apenas clique esquerdo
    
    const rect = canvasEl.getBoundingClientRect();
    const domX = e.clientX - rect.left;
    const domY = e.clientY - rect.top;
    
    // Verifica se clicou num nó real do vis-network
    const nodeId = state.network.getNodeAt({ x: domX, y: domY });
    if (nodeId) return; // Deixa o vis-network cuidar do arraste do nó

    const canvasPos = state.network.DOMtoCanvas({ x: domX, y: domY });
    let frame = state.selectedFrameId ? state.frames.find(f => f.id === state.selectedFrameId) : null;
    
    if (!frame || (!isPosInHandle(canvasPos.x, canvasPos.y, frame) && !isPosInFrame(canvasPos.x, canvasPos.y, frame))) {
      const hit = findFrameAt(canvasPos.x, canvasPos.y);
      if (hit) frame = hit;
    }

    if (frame) {
      if (isPosInHandle(canvasPos.x, canvasPos.y, frame)) {
        // Só redimensiona se já estiver selecionado (mostrando o handle)
        if (frame.id !== state.selectedFrameId) return;
        state.isResizingFrame = true;
        state.network.setOptions({ interaction: { dragView: false } });
      } else if (isPosInFrame(canvasPos.x, canvasPos.y, frame)) {
        // Exigir CTRL ou META para mover a moldura
        if (!e.ctrlKey && !e.metaKey) {
          return; // Sai e deixa o vis-network cuidar do panning (e futuro clique de seleção)
        }

        // Se usar Ctrl+Drag sem estar selecionado, seleciona no ato
        if (state.selectedFrameId !== frame.id) {
          state.selectedFrameId = frame.id;
          state.selectedNodeIds = [];
          state.network.unselectAll();
          updateSelectedPanel();
        }

        state.isDraggingFrame = true;
        state.dragStartPos = {
          x: canvasPos.x - frame.x,
          y: canvasPos.y - frame.y
        };
        state.dragStartFramePos = { x: frame.x, y: frame.y };

        // Captura todos os nós filhos que estão contidos visualmente na moldura
        state.dragStartNodes = [];
        const positions = state.network.getPositions();
        for (const nid in positions) {
           const p = positions[nid];
           if (isPosInFrame(p.x, p.y, frame)) {
               state.dragStartNodes.push({ id: nid, startX: p.x, startY: p.y });
           }
        }
        
        state.network.setOptions({ interaction: { dragView: false } });
      }
    }
  });

  window.addEventListener("pointermove", (e) => {
    if (state.isDraggingFrame || state.isResizingFrame) {
      const rect = canvasEl.getBoundingClientRect();
      const domX = e.clientX - rect.left;
      const domY = e.clientY - rect.top;
      const canvasPos = state.network.DOMtoCanvas({ x: domX, y: domY });
      
      const frame = state.frames.find(f => f.id === state.selectedFrameId);
      if (frame) {
        if (state.isResizingFrame) {
          frame.w = Math.max(100, canvasPos.x - frame.x);
          frame.h = Math.max(60, canvasPos.y - frame.y);
        } else if (state.isDraggingFrame) {
          frame.x = canvasPos.x - state.dragStartPos.x;
          frame.y = canvasPos.y - state.dragStartPos.y;

          // Move os nós filhos junto com a moldura
          if (state.dragStartNodes && state.dragStartNodes.length > 0) {
            const dx = frame.x - state.dragStartFramePos.x;
            const dy = frame.y - state.dragStartFramePos.y;
            const updates = state.dragStartNodes.map(n => ({
              id: n.id,
              x: n.startX + dx,
              y: n.startY + dy
            }));
            state.nodesDataSet.update(updates);
          }
        }
        state.network.redraw();
      }
    }
  });

  window.addEventListener("pointerup", () => {
    if (state.isDraggingFrame || state.isResizingFrame) {
      state.isDraggingFrame = false;
      state.isResizingFrame = false;
      state.dragStartNodes = [];
      // Libera a câmera nativa do vis-network
      state.network.setOptions({ interaction: { dragView: true } });
      saveLayoutPositions();
    }
  });

  // Renderização customizada dos frames (atrás de tudo)
  state.network.on("beforeDrawing", (ctx) => {
    drawFrames(ctx);
  });

  applyVisibilityAndHighlight();
}

// ─── Construção de nó individual ──────────────────────────────────────────────
function buildNodeDefinition(node) {
  const isView = node.node_type === "view";
  return {
    id: node.id,
    label: buildNodeLabel(node, false),
    raw: node,
    shape: "box",
    margin: { top: 6, right: 12, bottom: 6, left: 12 },
    widthConstraint: { minimum: 180, maximum: 400 },
    color: nodeColor(node, false, false),
    font: {
      face: "IBM Plex Mono, Consolas, monospace",
      size: 11,
      color: "#dce8ff",
      multi: "html",
      align: "left",
      bold: { color: "#ffffff", size: 12, mod: "bold" },
    },
    borderWidth: isView ? 1.5 : 1.5,
    borderWidthSelected: 3,
    shadow: {
      enabled: true,
      color: "rgba(0,0,0,0.5)",
      size: 6,
      x: 2,
      y: 3,
    },
    level: undefined,
  };
}

// ─── Construção de aresta individual ─────────────────────────────────────────
function buildEdgeDefinition(edge) {
  const isFk = edge.relation_type === "foreign_key";
  return {
    id: edge.id,
    from: edge.source,
    to: edge.target,
    label: isFk && edge.fk_column ? edge.fk_column : (edge.label || ""),
    raw: edge,
    arrows: {
      to: {
        enabled: true,
        type: "arrow",
        scaleFactor: 0.7,
      },
    },
    dashes: !isFk,
    color: isFk
      ? { color: "#5b9bd5", highlight: "#9fd3ff", hover: "#9fd3ff", opacity: 1.0 }
      : { color: "#4a6680", highlight: "#7fb5e8", hover: "#7fb5e8", opacity: 0.7 },
    width: isFk ? 1.8 : 1.2,
    selectionWidth: 3,
    hoverWidth: 2.5,
    font: {
      color: "#8ab4d6",
      size: 9,
      face: "IBM Plex Mono, Consolas, monospace",
      strokeWidth: 3,
      strokeColor: "#0a1928",
      align: "middle",
      background: "none",
    },
    smooth: {
      enabled: true,
      type: isFk ? "curvedCCW" : "continuous",
      roundness: 0.15,
    },
  };
}

// ─── Label ERD estilo Workbench ────────────────────────────────────────────────
// vis-network suporta HTML básico nos labels quando font.multi = "html".
// Usamos <b> para o cabeçalho e marcadores PK/FK, e linha separadora via ─.
function buildNodeLabel(node, collapsed) {
  const isView  = node.node_type === "view";
  const isDraft = node.node_type === "draft";
  const typeTag = isView ? " [VIEW]" : isDraft ? " [RASCUNHO]" : "";

  // Cabeçalho: nome em negrito + tipo
  const header = `<b>${escLabel(node.label)}${typeTag}</b>`;

  const columns = node.columns || [];
  if (collapsed || columns.length === 0) {
    const count = columns.length > 0 ? `  ${columns.length} col.` : "  (sem colunas)";
    return header + "\n" + "─".repeat(28) + "\n" + count;
  }

  const MAX_COLS = 20;
  const visible = columns.slice(0, MAX_COLS);
  const lines = [header, "─".repeat(30)];

  for (const col of visible) {
    let marker = "   ";
    if (col.is_pk) marker = "<b>PK</b>";
    else if (col.is_fk) marker = "<b>FK</b>";

    const name = truncate(col.name, 22);
    const type = truncate(col.type, 16);
    lines.push(`${marker} ${escLabel(name)} <i>${escLabel(type)}</i>`);
  }

  if (columns.length > MAX_COLS) {
    lines.push(`   <i>+${columns.length - MAX_COLS} mais...</i>`);
  }

  return lines.join("\n");
}

// Escapa caracteres especiais do HTML nos labels do vis-network
function escLabel(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function truncate(value, maxLen) {
  const str = String(value ?? "");
  if (str.length <= maxLen) return str;
  return `${str.slice(0, maxLen - 1)}…`;
}

// ─── Cores dos nós ────────────────────────────────────────────────────────────
//  table  → azul profundo  (#1a3d5c border azul-claro)
//  view   → âmbar/ouro escuro (#3d3000 border #c8a227)
//  faded  → versão com baixa opacidade
//  selected → azul-cyan brilhante
function nodeColor(node, faded, selected) {
  if (selected) {
    return {
      background: "#1a5fa8",
      border: "#7dc3ff",
      highlight: { background: "#1a5fa8", border: "#b6ddff" },
      hover:      { background: "#1a5fa8", border: "#b6ddff" },
    };
  }

  const isView = node.node_type === "view";
  const isDraft = node.node_type === "draft";

  if (faded) {
    if (isDraft) return {
      background: "rgba(50, 38, 10, 0.45)",
      border: "rgba(160, 110, 20, 0.30)",
      highlight: { background: "#3d2e06", border: "#c87f10" },
      hover:      { background: "#3d2e06", border: "#c87f10" },
    };
    return isView
      ? {
          background: "rgba(58, 46, 8, 0.45)",
          border: "rgba(160, 130, 30, 0.30)",
          highlight: { background: "#3d3000", border: "#c8a227" },
          hover:      { background: "#3d3000", border: "#c8a227" },
        }
      : {
          background: "rgba(18, 42, 70, 0.45)",
          border: "rgba(80, 130, 190, 0.30)",
          highlight: { background: "#162d4a", border: "#5b9bd5" },
          hover:      { background: "#162d4a", border: "#5b9bd5" },
        };
  }

  // Draft: laranja-enferrujado, borda pontilhada simulada com cor contrastante
  if (isDraft) {
    return {
      background: "#2a1a00",
      border: "#c87f10",
      highlight: { background: "#3d2800", border: "#f5a020" },
      hover:      { background: "#3d2800", border: "#f5a020" },
    };
  }

  if (isView) {
    return {
      background: "#2e2300",
      border: "#c09820",
      highlight: { background: "#3d3000", border: "#e8ba28" },
      hover:      { background: "#3a2c00", border: "#e8ba28" },
    };
  }

  return {
    background: "#0f2d4a",
    border: "#3a7ab8",
    highlight: { background: "#162d4a", border: "#6db3ff" },
    hover:      { background: "#162d4a", border: "#6db3ff" },
  };
}

function getNeighborNodeIds(nodeId) {
  const neighbors = new Set();
  for (const edge of state.allEdges) {
    if (edge.from === nodeId) neighbors.add(edge.to);
    if (edge.to === nodeId) neighbors.add(edge.from);
  }
  return neighbors;
}

function hasRelationship(nodeId) {
  return state.allEdges.some((edge) => edge.from === nodeId || edge.to === nodeId);
}

// ─── Lógica de Molduras (Frames) ──────────────────────────────────────────────

function findFrameAt(x, y) {
  // Retorna a moldura sob a posição (x, y) no canvas, priorizando a menor/mais recente
  for (let i = state.frames.length - 1; i >= 0; i--) {
    const f = state.frames[i];
    if (isPosInFrame(x, y, f)) return f;
  }
  return null;
}

function isPosInFrame(x, y, frame) {
  return x >= frame.x && x <= frame.x + frame.w &&
         y >= frame.y && y <= frame.y + frame.h;
}

function drawFrames(ctx) {
  state.frames.forEach(f => {
    const isSelected = f.id === state.selectedFrameId;
    
    // Fundo da moldura
    ctx.fillStyle = f.color || "rgba(100, 149, 237, 0.1)";
    ctx.beginPath();
    ctx.roundRect(f.x, f.y, f.w, f.h, 8);
    ctx.fill();

    // Borda
    ctx.strokeStyle = isSelected ? "#4da8ff" : "rgba(74, 105, 138, 0.4)";
    ctx.lineWidth = isSelected ? 3 : 1.5;
    if (!isSelected) ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Título (header)
    ctx.fillStyle = isSelected ? "#4da8ff" : "rgba(127, 163, 200, 0.8)";
    ctx.font = "bold 13px IBM Plex Sans, sans-serif";
    ctx.fillText(f.title.toUpperCase(), f.x + 10, f.y + 22);
  });
}

function openFrameModalForNew() {
  const modal = document.getElementById("modal-frame");
  document.getElementById("frame-modal-title-text").textContent = "Nova Moldura";
  document.getElementById("frame-title").value = "";
  document.getElementById("frame-color").selectedIndex = 0;
  document.getElementById("btn-delete-frame").hidden = true;
  modal.hidden = false;
  document.getElementById("frame-title").focus();
}

function openFrameModalForEdit(frame) {
  const modal = document.getElementById("modal-frame");
  document.getElementById("frame-modal-title-text").textContent = "Editar Moldura";
  document.getElementById("frame-title").value = frame.title;
  document.getElementById("frame-color").value = frame.color;
  document.getElementById("btn-delete-frame").hidden = false;
  modal.hidden = false;
}

function closeFrameModal() {
  document.getElementById("modal-frame").hidden = true;
}

function saveFrameFromModal() {
  const title = document.getElementById("frame-title").value.trim() || "Grupo";
  const color = document.getElementById("frame-color").value;
  
  if (state.selectedFrameId) {
    // Editar existente
    const frame = state.frames.find(f => f.id === state.selectedFrameId);
    if (frame) {
      frame.title = title;
      frame.color = color;
    }
  } else {
    // Criar nova
    let x = 0, y = 0, w = 400, h = 300;

    // Se houver nós selecionados, criar ao redor deles
    if (state.selectedNodeIds.length > 0) {
      const pos = state.network.getPositions(state.selectedNodeIds);
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      Object.values(pos).forEach(p => {
        minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
        minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
      });
      const padding = 60;
      x = minX - padding - 80;
      y = minY - padding - 40;
      w = (maxX - minX) + padding * 2 + 160;
      h = (maxY - minY) + padding * 2 + 80;
    } else {
      // Posição central da tela
      const center = state.network.getViewPosition();
      x = center.x - 200;
      y = center.y - 150;
    }

    state.frames.push({
      id: "frame_" + Date.now(),
      title, color, x, y, w, h
    });
  }

  closeFrameModal();
  state.network.redraw();
  saveLayoutPositions();
}

function deleteSelectedFrame() {
  if (!state.selectedFrameId) return;
  if (!confirm("Excluir esta moldura?")) return;
  state.frames = state.frames.filter(f => f.id !== state.selectedFrameId);
  state.selectedFrameId = null;
  closeFrameModal();
  state.network.redraw();
  saveLayoutPositions();
}

function applyVisibilityAndHighlight() {
  if (!state.nodesDataSet || !state.edgesDataSet) return;

  const showRelatedOnly = document.getElementById("toggle-related-only").checked;
  const hideIsolated = document.getElementById("toggle-hide-isolated").checked;

  const allNodeIds = state.allNodes.map((node) => node.id);
  const visibleNodeIds = new Set(allNodeIds);

  // Filtro de tipo (Tabela / View via checkboxes da legenda)
  for (const node of state.allNodes) {
    const nodeType = node.raw.node_type || "table"; // "table" | "view"
    if (!state.visibleTypes.has(nodeType)) {
      visibleNodeIds.delete(node.id);
    }
  }

  // Se houver multi-seleção, "showRelatedOnly" usa o primeiro da lista ou todos?
  // User pediu "related only of selected". Se houver vários, pegamos a união.
  if (showRelatedOnly && state.selectedNodeIds.length > 0) {
    const keep = new Set(state.selectedNodeIds);
    state.selectedNodeIds.forEach(id => {
      getNeighborNodeIds(id).forEach(neighId => keep.add(neighId));
    });
    for (const id of [...visibleNodeIds]) {
      if (!keep.has(id)) visibleNodeIds.delete(id);
    }
  }

  if (hideIsolated) {
    for (const nodeId of [...visibleNodeIds]) {
      if (!hasRelationship(nodeId)) visibleNodeIds.delete(nodeId);
    }
  }

  // Highlight logic
  const selectedSet = new Set(state.selectedNodeIds);
  const neighborsSet = new Set();
  if (selectedSet.size > 0) {
    selectedSet.forEach(id => {
      getNeighborNodeIds(id).forEach(neighId => neighborsSet.add(neighId));
    });
  }

  const nodeUpdates = state.allNodes.map((node) => {
    const visible = visibleNodeIds.has(node.id);
    const isSelected = selectedSet.has(node.id);
    const isNeighbor = neighborsSet.has(node.id);
    const hasSelection = selectedSet.size > 0;
    const faded = hasSelection ? !(isSelected || isNeighbor) : false;
    const collapsed = state.collapsedNodes.has(node.id);

    return {
      id: node.id,
      hidden: !visible,
      label: buildNodeLabel(node.raw, collapsed),
      color: nodeColor(node.raw, faded, isSelected),
    };
  });
  state.nodesDataSet.update(nodeUpdates);

  const edgeUpdates = state.allEdges.map((edge) => {
    const endpointsVisible = visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to);
    const hasSelection = selectedSet.size > 0;
    const connectedToSelected = hasSelection
      ? (selectedSet.has(edge.from) || selectedSet.has(edge.to))
      : false;
    const faded = hasSelection ? !connectedToSelected : false;
    const isFk = edge.raw.relation_type === "foreign_key";

    return {
      id: edge.id,
      hidden: !endpointsVisible,
      width: connectedToSelected ? 3.0 : (isFk ? 1.8 : 1.2),
      color: faded
        ? { color: "rgba(60, 90, 120, 0.25)", highlight: "#6db3ff", hover: "#6db3ff", opacity: 0.25 }
        : (isFk
            ? { color: "#5b9bd5", highlight: "#9fd3ff", hover: "#9fd3ff", opacity: 1.0 }
            : { color: "#4a6680", highlight: "#7fb5e8", hover: "#7fb5e8", opacity: 0.7 }),
    };
  });
  state.edgesDataSet.update(edgeUpdates);
}

function updateSelectedPanel() {
  const el = document.getElementById("selected-table");
  
  // Caso 1: Frame selecionado
  if (state.selectedFrameId) {
    const frame = state.frames.find(f => f.id === state.selectedFrameId);
    if (frame) {
      el.innerHTML = 
        `<div><strong>MOLDURA: ${frame.title}</strong></div>` +
        `<div style="margin-top:8px; color:var(--text-muted)">Clique duplo na moldura para editar título ou cor.</div>` +
        `<div style="margin-top:4px; color:var(--text-muted)">Arraste para mover.</div>`;
      return;
    }
  }

  // Caso 2: Múltiplos nós selecionados
  if (state.selectedNodeIds.length > 1) {
    el.innerHTML = 
      `<div><strong>${state.selectedNodeIds.length} objetos selecionados</strong></div>` +
      `<div style="margin-top:8px">Você pode mover todos juntos arrastando um deles.</div>` +
      `<div style="margin-top:4px">Clique em "Nova Moldura" para agrupar estes objetos.</div>`;
    return;
  }

  // Caso 3: Um nó selecionado (comportamento original)
  if (state.selectedNodeIds.length === 1) {
    const nodeId = state.selectedNodeIds[0];
    const node = state.payload.nodes.find((item) => item.id === nodeId);
    if (!node) {
      el.textContent = "Objeto selecionado nao encontrado.";
      return;
    }

    const relations = state.payload.edges.filter(
      (edge) => edge.source === node.id || edge.target === node.id
    );
    const pk = node.primary_key?.length ? node.primary_key.join(", ") : "-";
    const fkCount = node.columns.filter((column) => column.is_fk).length;
    const type = node.table_type || "BASE TABLE";

    el.innerHTML =
      `<div><strong>${node.label}</strong></div>` +
      `<div>Tipo: <code>${type}</code></div>` +
      `<div>PK: <code>${pk}</code></div>` +
      `<div>Colunas: ${node.columns.length}</div>` +
      `<div>FKs: ${fkCount}</div>` +
      `<div>Relacionamentos: ${relations.length}</div>`;
    return;
  }

  el.textContent = "Nenhum objeto selecionado.";
}

function searchTable() {
  const input = document.getElementById("search-table");
  const term = (input.value || "").trim().toLowerCase();
  if (!term) {
    setStatus("Informe um nome de tabela para buscar.", "warn");
    return;
  }

  const hit = state.payload.nodes.find((node) => node.label.toLowerCase().includes(term));
  if (!hit) {
    setStatus(`Nenhuma tabela encontrada para: ${term}`, "warn");
    return;
  }

  state.selectedNodeIds = [hit.id];
  state.network.selectNodes([hit.id]);
  updateSelectedPanel();
  applyVisibilityAndHighlight();
  centerSelectedNode();
  setStatus(`Tabela localizada: ${hit.label}`, "ok");
}

function centerSelectedNode() {
  if (!state.network || state.selectedNodeIds.length === 0) {
    setStatus("Selecione objetos para centralizar.", "warn");
    return;
  }
  // Centraliza o primeiro ou a seleção
  state.network.focus(state.selectedNodeIds[0], {
    scale: Math.max(state.network.getScale(), 0.75),
    animation: { duration: 450, easingFunction: "easeInOutQuad" },
  });
}

function fitGraph() {
  if (!state.network) return;
  state.network.fit({ animation: { duration: 300, easingFunction: "easeInOutQuad" } });
}

function changeZoom(factor) {
  if (!state.network) return;
  const currentScale = state.network.getScale();
  const nextScale = Math.min(2.5, Math.max(0.15, currentScale * factor));
  state.network.moveTo({ scale: nextScale, animation: { duration: 180 } });
}

function relayoutGraph() {
  if (!state.network) return;
  state.relayoutSeed += 1;
  setStatus("Reorganizando layout técnico...", "ok");
  clearLayoutPositions();

  const nodes = state.nodesDataSet.get();
  const edges = state.edgesDataSet.get();
  
  // 1. Calcular componentes conectados (ilhas)
  const components = findConnectedComponents(nodes, edges);
  
  // 2. Distribuir ilhas em uma grade global
  const updates = [];
  let currentGroupX = 0;
  let currentGroupY = 0;
  let maxColumnHeight = 0;
  const COLUMN_WIDTH_LIMIT = 2000; // largura sugerida para a grade de ilhas
  const GROUP_SPACING = 350;

  for (const comp of components) {
    const compNodes = nodes.filter(n => comp.has(n.id));
    const compEdges = edges.filter(e => comp.has(e.from) && comp.has(e.to));
    
    // Organiza a ilha localmente (Algoritmo Sugiyama via Dagre)
    const localCoords = computeDagreLayout(compNodes, compEdges);
    
    // Aplica offsets globais para a ilha (Sistema de Grade para evitar sobreposição de grupos)
    for (const id in localCoords) {
      updates.push({
        id,
        x: currentGroupX + localCoords[id].x,
        y: currentGroupY + localCoords[id].y
      });
    }

    // Calcula dimensões reais ocupadas pela ilha para a grade global
    const coordsArr = Object.values(localCoords);
    const minX = Math.min(...coordsArr.map(c => c.x));
    const maxX = Math.max(...coordsArr.map(c => c.x));
    const minY = Math.min(...coordsArr.map(c => c.y));
    const maxY = Math.max(...coordsArr.map(c => c.y));
    
    const w = (maxX - minX) || 0;
    const h = (maxY - minY) || 0;

    currentGroupX += w + GROUP_SPACING;
    maxColumnHeight = Math.max(maxColumnHeight, h);

    if (currentGroupX > COLUMN_WIDTH_LIMIT) {
      currentGroupX = 0;
      currentGroupY += maxColumnHeight + GROUP_SPACING;
      maxColumnHeight = 0;
    }
  }

  state.nodesDataSet.update(updates);

  // 3. Ativar física brevemente para estabilização (evitar overlapping fino)
  state.network.setOptions(makePhysicsOptions(true));
  state.network.once("stabilized", () => {
    state.network.setOptions({ physics: { enabled: false } });
    fitGraph();
    saveLayoutPositions();
    setStatus("Layout técnico aplicado.", "ok");
  });
}

/**
 * Agrupa nós em componentes conectados (ilhas).
 */
function findConnectedComponents(nodes, edges) {
  const adj = {};
  nodes.forEach(n => adj[n.id] = []);
  edges.forEach(e => {
    if (adj[e.from] && adj[e.to]) {
      adj[e.from].push(e.to);
      adj[e.to].push(e.from);
    }
  });

  const components = [];
  const visited = new Set();

  nodes.forEach(node => {
    if (!visited.has(node.id)) {
      const comp = new Set();
      const stack = [node.id];
      visited.add(node.id);
      
      while (stack.length) {
        const u = stack.pop();
        comp.add(u);
        (adj[u] || []).forEach(v => {
          if (!visited.has(v)) {
            visited.add(v);
            stack.push(v);
          }
        });
      }
      components.push(comp);
    }
  });
  
  // Ordena componentes: maiores primeiro (mais tabelas)
  return components.sort((a,b) => b.size - a.size);
}

/**
 * Calcula layout avançado (Dagre/Sugiyama) para uma ilha específica.
 */
function computeDagreLayout(nodes, edges) {
  if (!window.dagre) {
    console.warn("[ERD] Dagre indisponível, usando layout fallback.");
    const coords = {};
    nodes.forEach((n, i) => coords[n.id] = { x: (i%3)*300, y: Math.floor(i/3)*250 });
    return coords;
  }

  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "TB",    // Top to Bottom
    nodesep: 80,      // Distância horizontal entre nós
    ranksep: 120,     // Distância vertical entre níveis
    marginx: 50,
    marginy: 50
  });

  g.setDefaultEdgeLabel(() => ({}));

  // Adicionar nós à calculadora Dagre
  nodes.forEach(n => {
    // Estimativa de largura/altura baseada no conteúdo do nó box
    const colCount = n.raw?.columns?.length || 0;
    const estimatedW = 240;
    const estimatedH = 60 + (colCount > 0 ? Math.min(colCount, 20) * 18 : 30);
    g.setNode(n.id, { width: estimatedW, height: estimatedH });
  });

  // Adicionar arestas (FKs) para determinar hierarquia
  edges.forEach(e => {
    g.setEdge(e.from, e.to);
  });

  // Executar o cálculo matemático
  dagre.layout(g);

  // Extrair resultados
  const coords = {};
  g.nodes().forEach(id => {
    const node = g.node(id);
    if (node) {
      coords[id] = { x: node.x, y: node.y };
    }
  });

  return coords;
}

// ─── Parâmetros de física do layout ERD ──────────────────────────────────────
// Estratégia: barnesHut com avoidOverlap e springLength generoso
//   - evita nós amontoados no centro (problema original)
//   - nós relacionados ficam próximos (springLength = comprimento de mola)
//   - nós sem relação se afastam (gravitationalConstant negativo forte)
//   - avoidOverlap garante que bounding boxes nunca se sobreponham
function makePhysicsOptions(forRelayout) {
  return {
    enabled: true,
    stabilization: {
      enabled: true,
      iterations: forRelayout ? 450 : 280,
      updateInterval: 25,
      fit: true,
    },
    solver: "barnesHut",
    barnesHut: {
      gravitationalConstant: -20000,
      centralGravity: 0.0,
      springLength: 150,
      springConstant: 0.05,
      damping: 0.09,
      avoidOverlap: 1.0,
    },
    minVelocity: 0.75,
    maxVelocity: 50,
    timestep: 0.4,
  };
}

// ─── Persistência de layout (localStorage) ────────────────────────────────────
// Chave: erd_layout_<agentId>_<digestVersion_hash>
// Formato: { "<nodeId>": { x: number, y: number }, ... }
// A versão do digest é hasheada para invalidar layouts de digests antigos.
// Se o digest mudar, o layout antigo é ignorado (não apagado: o usuário pode ter
// vários digests no histórico e queremos evitar conflitos).

function _layoutKey() {
  const vh = hashStr(state.digestVersion || "");
  return `erd_layout_${state.agentId}_${vh}`;
}

// FNV-1a 32-bit hash simples — evita colisões sem dependências externas
function hashStr(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h * 0x01000193) >>> 0;
  }
  return h.toString(16);
}

function saveLayoutPositions() {
  if (!state.network || !state.agentId) return;
  try {
    const positions = state.network.getPositions();
    const frames = state.frames;
    localStorage.setItem(_layoutKey(), JSON.stringify({ positions, frames }));
  } catch (err) {
    console.warn("[ERD] Nao foi possivel salvar layout:", err);
  }
}

function loadLayoutData() {
  if (!state.agentId) return null;
  try {
    const raw = localStorage.getItem(_layoutKey());
    if (!raw) return null;
    const data = JSON.parse(raw);
    
    // Compatibilidade: se for o formato antigo (apenas posições), migra
    if (data && !data.positions && typeof data === "object") {
       return { positions: data, frames: [] };
    }
    
    return data;
  } catch (err) {
    console.warn("[ERD] Nao foi possivel ler layout salvo:", err);
    return null;
  }
}

function clearLayoutPositions() {
  if (!state.agentId) return;
  try {
    localStorage.removeItem(_layoutKey());
  } catch (_) {}
}

function setStatus(message, kind) {
  const el = document.getElementById("diagram-status");
  el.textContent = message;
  el.classList.remove("ok", "warn", "error");
  if (kind) el.classList.add(kind);
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch (_) {
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Modal — Nova Tabela
// ═══════════════════════════════════════════════════════════════════════════════

const COLUMN_TYPES = [
  "INT", "BIGINT", "SMALLINT", "TINYINT",
  "VARCHAR(255)", "VARCHAR(100)", "VARCHAR(50)",
  "TEXT", "MEDIUMTEXT", "LONGTEXT",
  "DECIMAL(10,2)", "FLOAT", "DOUBLE",
  "DATE", "DATETIME", "TIMESTAMP",
  "BOOLEAN", "TINYINT(1)",
  "JSON", "BLOB", "CHAR(36)",
];

let _columnCounter = 0;

function openNewTableModal() {
  _columnCounter = 0;
  document.getElementById("new-table-name").value = "";
  document.getElementById("columns-list").innerHTML = "";
  document.getElementById("sql-preview-wrap").hidden = true;
  document.getElementById("sql-preview").textContent = "";
  document.getElementById("ddl-result").hidden = true;
  document.getElementById("btn-execute-ddl").disabled = true;
  state.generatedDDL = null;
  state.draftTableName = null;
  // Adiciona uma linha de coluna id padrão
  addColumnRow({ name: "id", type: "INT", notNull: true, pk: true, ai: true });
  document.getElementById("modal-new-table").hidden = false;
  document.getElementById("new-table-name").focus();
}

function closeNewTableModal() {
  document.getElementById("modal-new-table").hidden = true;
}

function addColumnRow(defaults = {}) {
  _columnCounter++;
  const idx = _columnCounter;
  const list = document.getElementById("columns-list");
  const row = document.createElement("div");
  row.className = "col-row";
  row.dataset.idx = idx;

  const typeOptions = COLUMN_TYPES.map(
    (t) => `<option value="${t}" ${t === (defaults.type || "VARCHAR(255)") ? "selected" : ""}>${t}</option>`
  ).join("");

  row.innerHTML = `
    <input class="col-name form-input" type="text" placeholder="nome_coluna" value="${escAttr(defaults.name || "")}">
    <select class="col-type form-select">${typeOptions}</select>
    <label class="col-check" title="NOT NULL"><input type="checkbox" class="col-notnull" ${defaults.notNull !== false ? "checked" : ""}> NN</label>
    <label class="col-check" title="PRIMARY KEY"><input type="radio" class="col-pk" name="col-pk-radio" ${defaults.pk ? "checked" : ""}> PK</label>
    <label class="col-check" title="AUTO_INCREMENT"><input type="checkbox" class="col-ai" ${defaults.ai ? "checked" : ""}> AI</label>
    <input class="col-default form-input col-default-input" type="text" placeholder="default (opt.)" value="${escAttr(defaults.defaultVal || "")}">
    <button class="btn-remove-col" data-idx="${idx}" title="Remover coluna">✕</button>
  `;

  row.querySelector(".btn-remove-col").addEventListener("click", () => {
    row.remove();
  });

  list.appendChild(row);
}

function _collectColumns() {
  const rows = document.querySelectorAll(".col-row");
  const cols = [];
  for (const row of rows) {
    const name = row.querySelector(".col-name").value.trim();
    if (!name) continue;
    cols.push({
      name,
      type: row.querySelector(".col-type").value,
      notNull: row.querySelector(".col-notnull").checked,
      pk: row.querySelector(".col-pk").checked,
      ai: row.querySelector(".col-ai").checked,
      defaultVal: row.querySelector(".col-default-input").value.trim(),
    });
  }
  return cols;
}

function generateCreateTableSQL() {
  const tableName = document.getElementById("new-table-name").value.trim();
  if (!tableName) {
    alert("Informe o nome da tabela.");
    return;
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName)) {
    alert("Nome de tabela inválido. Use apenas letras, números e underscore.");
    return;
  }

  const cols = _collectColumns();
  if (cols.length === 0) {
    alert("Adicione ao menos uma coluna.");
    return;
  }

  const pkCols = cols.filter((c) => c.pk).map((c) => c.name);
  const lines = cols.map((col) => {
    const parts = [`  \`${col.name}\` ${col.type}`];
    if (col.notNull) parts.push("NOT NULL");
    if (col.ai) parts.push("AUTO_INCREMENT");
    if (col.defaultVal) parts.push(`DEFAULT ${col.defaultVal}`);
    return parts.join(" ");
  });

  if (pkCols.length > 0) {
    lines.push(`  PRIMARY KEY (\`${pkCols.join("`, `")}\`)`);
  }

  const sql = `CREATE TABLE \`${tableName}\` (\n${lines.join(",\n")}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;`;

  state.generatedDDL = sql;
  state.draftTableName = tableName;
  document.getElementById("sql-preview").textContent = sql;
  document.getElementById("sql-preview-wrap").hidden = false;
  document.getElementById("ddl-result").hidden = true;
  document.getElementById("btn-execute-ddl").disabled = false;
}

async function executeCreateTableDDL() {
  if (!state.generatedDDL) return;
  const btn = document.getElementById("btn-execute-ddl");
  const resultEl = document.getElementById("ddl-result");
  btn.disabled = true;
  btn.textContent = "Executando...";
  resultEl.hidden = true;
  resultEl.className = "ddl-result";

  try {
    const res = await fetch(`/api/diagram/${encodeURIComponent(state.agentId)}/execute-ddl`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql: state.generatedDDL, promote_draft: state.draftTableName }),
    });
    const data = await safeJson(res);
    if (res.ok && data?.success) {
      resultEl.textContent = `✔ ${data.message || "Tabela criada com sucesso."}`;
      resultEl.classList.add("ddl-ok");
      btn.textContent = "Executado ✔";
      state.draftTableName = null;
      await reloadDiagram();
    } else {
      const msg = data?.detail || data?.error || data?.message || "Falha ao executar DDL.";
      resultEl.textContent = `✖ ${msg}`;
      resultEl.classList.add("ddl-error");
      btn.disabled = false;
      btn.textContent = "Executar no banco";
    }
  } catch (err) {
    resultEl.textContent = `✖ Erro de rede: ${err.message}`;
    resultEl.classList.add("ddl-error");
    btn.disabled = false;
    btn.textContent = "Executar no banco";
  }

  resultEl.hidden = false;
}

async function createTableInERDOnly() {
  const tableName = document.getElementById("new-table-name").value.trim();
  if (!tableName) {
    alert("Informe o nome da tabela.");
    return;
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName)) {
    alert("Nome de tabela inválido. Use apenas letras, números e underscore.");
    return;
  }

  const cols = _collectColumns();
  if (cols.length === 0) {
    alert("Adicione ao menos uma coluna.");
    return;
  }

  const btn = document.getElementById("btn-add-to-erd");
  btn.disabled = true;
  btn.textContent = "Salvando...";

  const columns = cols.map((c) => ({
    name: c.name,
    sql_type: c.type,
    pk: c.pk,
    nullable: !c.notNull,
    auto_increment: c.ai,
    default_val: c.defaultVal || null,
  }));

  try {
    const res = await fetch(`/api/diagram/${encodeURIComponent(state.agentId)}/drafts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: tableName, columns }),
    });
    const data = await safeJson(res);
    if (res.ok) {
      closeNewTableModal();
      setStatus(`Rascunho '${tableName}' adicionado ao ERD.`, "ok");
      await reloadDiagram();
    } else {
      alert(data?.detail || "Falha ao criar rascunho.");
    }
  } catch (err) {
    alert(`Erro de rede: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Criar só no ERD";
  }
}

async function reloadDiagram() {
  const saved = loadLayoutData(); // preservar frames ao recarregar
  try {
    const res = await fetch(`/api/diagram/${encodeURIComponent(state.agentId)}`);
    if (!res.ok) return;
    const payload = await res.json();
    state.payload = payload;
    state.digestVersion = payload.generated_at || "unknown";
    
    const positions = saved?.positions || {};
    state.allNodes = payload.nodes.map((n) => {
      const base = buildNodeDefinition(n);
      if (positions[n.id]) {
        base.x = positions[n.id].x;
        base.y = positions[n.id].y;
      }
      return base;
    });
    state.allEdges = payload.edges.map((e) => buildEdgeDefinition(e));
    
    state.nodesDataSet.clear();
    state.nodesDataSet.add(state.allNodes);
    state.edgesDataSet.clear();
    state.edgesDataSet.add(state.allEdges);
    
    // Restaurar frames
    state.frames = saved?.frames || [];
    
    applyVisibilityAndHighlight();
    renderMetadata();
  } catch (_) { /* silently fail */ }
}

// ─── Lógica de Molduras (Helpers) ───────────────────────────────────────────

function findFrameAt(x, y) {
  // Varre do último (topo) para o primeiro (fundo)
  for (let i = state.frames.length - 1; i >= 0; i--) {
    if (isPosInFrame(x, y, state.frames[i])) return state.frames[i];
  }
  return null;
}

function isPosInFrame(x, y, f) {
  return x >= f.x && x <= f.x + f.w && y >= f.y && y <= f.y + f.h;
}

function isPosInHandle(x, y, f) {
  const s = state.frameHandleSize;
  return x >= f.x + f.w - s && x <= f.x + f.w + s && 
         y >= f.y + f.h - s && y <= f.y + f.h + s;
}

function drawFrames(ctx) {
  state.frames.forEach(f => {
    const isSelected = state.selectedFrameId === f.id;
    
    // Fundo
    ctx.fillStyle = f.color || "rgba(77, 168, 255, 0.1)";
    ctx.beginPath();
    ctx.roundRect(f.x, f.y, f.w, f.h, 8);
    ctx.fill();
    
    // Borda
    ctx.strokeStyle = isSelected ? "#4da8ff" : "rgba(74, 105, 138, 0.4)";
    ctx.lineWidth = isSelected ? 3 : 1.5;
    ctx.stroke();
    
    // Título
    ctx.fillStyle = isSelected ? "#ffffff" : "#7fa3c8";
    ctx.font = "bold 14px IBM Plex Sans, sans-serif";
    ctx.fillText(f.title, f.x + 10, f.y + 22);

    // Resize Handle (se selecionado)
    if (isSelected) {
      ctx.fillStyle = "#4da8ff";
      ctx.fillRect(f.x + f.w - 6, f.y + f.h - 6, 12, 12);
    }
  });
}

function openFrameModalForNew() {
  let initialW = 350;
  let initialH = 250;
  let initialX = state.network.getViewPosition().x - initialW/2;
  let initialY = state.network.getViewPosition().y - initialH/2;

  // Se houver seleção, calcular BB
  if (state.selectedNodeIds.length > 0) {
    const positions = state.network.getPositions(state.selectedNodeIds);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    for (const id in positions) {
      const p = positions[id];
      // Padding aproximado baseado no tamanho médio dos nós
      minX = Math.min(minX, p.x - 120);
      maxX = Math.max(maxX, p.x + 120);
      minY = Math.min(minY, p.y - 80);
      maxY = Math.max(maxY, p.y + 120);
    }
    initialX = minX;
    initialY = minY;
    initialW = maxX - minX;
    initialH = maxY - minY;
  }

  state.editingFrameId = null;
  document.getElementById("frame-modal-title-text").textContent = "Nova Moldura";
  document.getElementById("frame-title").value = "";
  document.getElementById("btn-delete-frame").hidden = true;
  
  // Guardar posição temporária
  state.tempFramePos = { x: initialX, y: initialY, w: initialW, h: initialH };
  
  document.getElementById("modal-frame").hidden = false;
  document.getElementById("frame-title").focus();
}

function openFrameModalForEdit(f) {
  state.editingFrameId = f.id;
  document.getElementById("frame-modal-title-text").textContent = "Editar Moldura";
  document.getElementById("frame-title").value = f.title;
  document.getElementById("frame-color").value = f.color || "rgba(100, 149, 237, 0.15)";
  document.getElementById("btn-delete-frame").hidden = false;
  document.getElementById("modal-frame").hidden = false;
}

function closeFrameModal() {
  document.getElementById("modal-frame").hidden = true;
}

function saveFrameFromModal() {
  const title = document.getElementById("frame-title").value.trim() || "Grupo";
  const color = document.getElementById("frame-color").value;
  
  if (state.editingFrameId) {
    const f = state.frames.find(frame => frame.id === state.editingFrameId);
    if (f) {
      f.title = title;
      f.color = color;
    }
  } else {
    const newFrame = {
      id: "frame_" + Date.now(),
      title: title,
      color: color,
      ...state.tempFramePos
    };
    state.frames.push(newFrame);
    state.selectedFrameId = newFrame.id;
  }
  
  closeFrameModal();
  state.network.redraw();
  saveLayoutPositions();
  updateSelectedPanel();
}

function deleteSelectedFrame() {
  if (!state.editingFrameId) return;
  state.frames = state.frames.filter(f => f.id !== state.editingFrameId);
  state.selectedFrameId = null;
  closeFrameModal();
  state.network.redraw();
  saveLayoutPositions();
  updateSelectedPanel();
}

function escAttr(str) {
  return String(str ?? "").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
