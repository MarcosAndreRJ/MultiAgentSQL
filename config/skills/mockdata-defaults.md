# Mock Data Defaults Skill
# Estratégias e regras para geração de mock data em MySQL.

## Objetivo
Orientar o agente a gerar dados fictícios coerentes respeitando a estrutura real do banco.

## Regras de Mock Data

### Antes de Gerar
- Sempre consultar DESCRIBE ou INFORMATION_SCHEMA antes de gerar mock data
- Respeitar tipos de coluna exatamente
- Respeitar constraints NOT NULL
- Respeitar tamanhos de VARCHAR e INT

### Durante Geração
- Gerar valores plausíveis, não apenas "teste1", "teste2"
- Respeitar FKs quando houver dados referenciados
- Datas: usar CURRENT_TIMESTAMP ou datas recentes realistas
- Emails: formato válido (ex: nome@dominio.com)
- CPF/CNPJ: se necessário, usar geradores simples ou placeholders válidos
- Floats/Decimais: valores dentro de ranges razoáveis

### VARCHARs por Tipo Comum
- nome: nomes realistas em português
- email: formato@dominio.com
- telefone: formato (XX) XXXX-XXXX
- CEP: formato XXXXX-XXX
- descricao: texto curto e coerente com domínio

### Estratégia de Volume
- Para testes rápidos: 5-10 linhas
- Para carga: 100-1000 linhas (via loop ou VALUES múltiplos)
- Para tabelas com FK: sempre inserir dados na tabela pai primeiro

## Padrão de INSERT em Lote

```sql
INSERT INTO nome_tabela (col1, col2, col3) VALUES
  (val1a, val2a, val3a),
  (val1b, val2b, val3b),
  (val1c, val2c, val3c);
```

## Proibições
- Não inserir valores que violem constraints sem avisar
- Não assumir que colunas com nomes genéricos têm um tipo específico
- Não inventar estrutura — sempre consultar DESCRIBE primeiro
- Não gerar dados sensíveis reais (CPFs reais, senhas reais, etc.)

## Observações
- Verificar AUTO_INCREMENT antes de inserir IDs manuais
- Em tabelas com trigger BEFORE INSERT, inserir pode ter efeitos colaterais
- Em tabelas auditadas, mock data pode acionar triggers de log
