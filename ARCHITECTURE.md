# Arquitetura de Domínios de Banco de Dados

Este documento define a separação conceitual e técnica entre os bancos de dados do sistema MultiAgentSQL.

---

## 1. O que é o `platform_db` (Banco da Plataforma)

O `platform_db` é o coração administrativo do sistema. Ele reside em um servidor MySQL compartilhado (atualmente em `192.168.0.5`) e sua responsabilidade é gerenciar a configuração e o monitoramento.

**Responsabilidades:**
- Cadastro de Provedores LLM (`llm_providers`) e Modelos (`llm_models`).
- Definição de Agentes e seus comportamentos.
- Vínculos (Bindings) entre agentes e seus recursos.
- Logs de saúde do sistema e de consultas.
- Dashboard administrativo.

**Regra de Ouro:** Os agentes **NUNCA** escrevem diretamente no `platform_db`. Ele é exclusivo para metadados e controle.

---

## 2. O que é o `target_db` (Banco do Alvo)

O `target_db` é o banco operacional que o agente manipula em tempo real. Cada bot possui um ou mais `target_db` vinculados a ele.

**Responsabilidades:**
- Introspecção de schema para geração de SQL.
- Execução de queries de consulta de dados de negócio.
- Contexto operacional específico da missão do agente.

**Regra de Ouro:** O sistema deve tratar o `target_db` como um recurso externo e volátil. O acesso deve ser feito sempre via abstrações do `TargetDatabaseConnection`.

---

## 3. Os Vínculos (Bindings)

A ponte entre os domínios é feita via tabelas de binding no `platform_db`:

- `agent_database_bindings`: Define as credenciais e localidade de um `target_db` operacional.
- `agent_llm_bindings`: Define qual provider e modelo o agente está autorizado a usar.

---

## 4. Diferenciação de Monitoramento (Health)

- **System Health**: Monitora a conectividade do backend com o `platform_db`.
- **Target Health**: Monitora se o agente consegue alcançar o seu banco operacional alvo.

---

> [!IMPORTANT]
> A mistura destes domínios é considerada uma falha grave de arquitetura. O código deve sempre explicitar qual banco está manipulando através da nomenclatura de variáveis (`platform_db` vs `target_db`).
