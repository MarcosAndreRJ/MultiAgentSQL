/**
 * formatters.js — Formatadores de dados para exibição na UI
 */

/** Formata data/hora em pt-BR estilo compacto */
export function fmtDate(isoString) {
  if (!isoString) return '—';
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(isoString));
  } catch (_) { return isoString; }
}

/** Formata número de tokens/contexto */
export function fmtTokens(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

/** Formata duração em ms */
export function fmtLatency(ms) {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/** Formata custo ($) */
export function fmtCost(val) {
  if (val == null) return '—';
  if (val === 0) return 'Grátis';
  return `$${Number(val).toFixed(4)}`;
}

/** Retorna tipo badge para status genérico */
export function statusBadgeType(status) {
  const map = {
    ok: 'success', healthy: 'success', active: 'success', online: 'success',
    error: 'danger', fail: 'danger', inactive: 'danger', offline: 'danger',
    warning: 'warning', degraded: 'warning', slow: 'warning',
    unknown: 'muted', pending: 'muted',
  };
  return map[(status || '').toLowerCase()] || 'muted';
}

/** Trunca string longa */
export function truncate(str, len = 40) {
  if (!str) return '—';
  return str.length > len ? str.slice(0, len) + '…' : str;
}

/** Formata hora atual HH:MM */
export function nowTime() {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

/** Formata data relativa ao tempo atual (ex: "há 2 minutos") */
export function formatRelativeTime(isoString) {
  if (!isoString) return '—';
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const seconds = Math.floor(diff / 1000);
    if (seconds < 60) return 'agora';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `há ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `há ${hours}h`;
    return fmtDate(isoString);
  } catch (_) { return isoString; }
}
