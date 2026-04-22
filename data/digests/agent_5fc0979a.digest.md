# DB Digest — devhacks_site
**Agente:** `agent_5fc0979a`  
**Banco:** `devhacks_site`  
**Gerado em:** 2026-04-15 21:42:18 UTC  

## Resumo
| Objeto | Qtd |
|--------|-----|
| Tabelas | 52 |
| Views | 34 |
| Triggers | 13 |
| Procedures | 8 |
| Functions | 3 |

## Tabelas

### `Ambiente`
_8 coluna(s). Relacionada a: BancoDeDados_
**PK:** `idAmbiente`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idAmbiente` | `int(11)` | Não |
| `Nome` | `enum('DEV','HOMOLOG','PROD')` | Não |
| `Descricao` | `varchar(255)` | Sim |
| `idBancoDeDados` | `int(11)` | Sim |
| `idCliente` | `int(11)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idBancoDeDados` → `BancoDeDados.idBancoDeDados`

### `BancoDeDados`
_13 coluna(s). Relacionada a: Projeto, Empresa_
**PK:** `idBancoDeDados`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idBancoDeDados` | `int(11)` | Não |
| `Titulo` | `varchar(60)` | Não |
| `idProjeto` | `int(11)` | Sim |
| `idEmpresa` | `int(11)` | Sim |
| `Servidor` | `varchar(255)` | Não |
| `Linguagem` | `enum('MySQL','PostgreSQL','SQLServer','Oracle','SQLite')` | Não |
| `VersaoBD` | `varchar(20)` | Não |
| `AmbienteCriacao` | `enum('DEV','HOMOLOG','PROD')` | Sim |
| `UltimaAtualizacao` | `timestamp` | Sim |
| `Status` | `enum('ATIVO','INATIVO')` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idProjeto` → `Projeto.idProjeto`
- `idEmpresa` → `Empresa.idEmpresa`

### `Dica`
_10 coluna(s). Relacionada a: Projeto, Usuario, DicaCategoria_
**PK:** `idDica`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idDica` | `int(11)` | Não |
| `Titulo` | `varchar(60)` | Não |
| `Descricao` | `longtext` | Sim |
| `Codigo` | `longtext` | Sim |
| `idDicaCategoria` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Sim |
| `idUsuario` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idDicaCategoria` → `DicaCategoria.idDicaCategoria`
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Usuario.idUsuario`

### `DicaCategoria`
_Categoria/classificação. 7 coluna(s). Relacionada a: Empresa_
**PK:** `idDicaCategoria`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idDicaCategoria` | `int(11)` | Não |
| `Descricao` | `varchar(255)` | Não |
| `isGlobal` | `tinyint(1)` | Não |
| `idEmpresa` | `int(11)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`

### `DicaCodigo`
_9 coluna(s). Relacionada a: Dica, DicaLinguagem_
**PK:** `idDicaCodigo`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idDicaCodigo` | `int(11)` | Não |
| `Descricao` | `text` | Sim |
| `Codigo` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idDicaLinguagem` | `int(11)` | Não |
| `idDica` | `int(11)` | Não |
| `Titulo` | `varchar(60)` | Não |

**FKs:**
- `idDica` → `Dica.idDica`
- `idDicaLinguagem` → `DicaLinguagem.idDicaLinguagem`

### `DicaComentario`
_7 coluna(s). Relacionada a: Dica, Usuario_
**PK:** `idDicaComentario`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idDicaComentario` | `int(11)` | Não |
| `Descricao` | `varchar(255)` | Não |
| `idDica` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idDica` → `Dica.idDica`
- `idUsuario` → `Usuario.idUsuario`

### `DicaLinguagem`
_5 coluna(s)_
**PK:** `idDicaLinguagem`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idDicaLinguagem` | `int(11)` | Não |
| `Descricao` | `varchar(255)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `Empresa`
_6 coluna(s). Relacionada a: Usuario_
**PK:** `idEmpresa`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idEmpresa` | `int(11)` | Não |
| `Nome` | `varchar(60)` | Sim |
| `RazaoSocial` | `varchar(120)` | Sim |
| `Site` | `varchar(225)` | Sim |
| `CNPJ` | `varchar(14)` | Sim |
| `idUsuario` | `int(11)` | Não |

**FKs:**
- `idUsuario` → `Usuario.idUsuario`

### `EmpresaConvite`
_12 coluna(s). Relacionada a: Usuario, Empresa_
**PK:** `idEmpresaConvite`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idEmpresaConvite` | `int(11)` | Não |
| `Nome` | `varchar(60)` | Sim |
| `Email` | `varchar(255)` | Sim |
| `Telefone` | `varchar(11)` | Sim |
| `isConfirmado` | `smallint(1)` | Sim |
| `dtExpiracao` | `timestamp` | Sim |
| `CodigoAceite` | `varchar(10)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idEmpresa` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idUsuario` → `Usuario.idUsuario`

### `EmpresaDica`
_10 coluna(s). Relacionada a: Empresa, DicaCategoria_
**PK:** `idEmpresaDica`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idEmpresaDica` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Sim |
| `idDicaCategoria` | `int(11)` | Não |
| `Titulo` | `varchar(60)` | Não |
| `Descricao` | `longtext` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idEmpresa` | `int(11)` | Não |
| `isPublica` | `smallint(1)` | Não |

**FKs:**
- `idDicaCategoria` → `DicaCategoria.idDicaCategoria`
- `idEmpresa` → `Empresa.idEmpresa`

### `EmpresaSenha`
_12 coluna(s). Relacionada a: Usuario, Empresa_
**PK:** `idEmpresaSenha`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idEmpresaSenha` | `int(11)` | Não |
| `idEmpresa` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `Login` | `varchar(45)` | Sim |
| `Senha` | `varchar(120)` | Sim |
| `Titulo` | `varchar(60)` | Sim |
| `Token` | `varchar(255)` | Sim |
| `Observacao` | `text` | Sim |
| `isPublica` | `smallint(1)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idUsuario` → `Usuario.idUsuario`

### `LockedTableByTrigger`
_6 coluna(s)_
**PK:** `idLockedTableByTrigger`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idLockedTableByTrigger` | `int(11)` | Não |
| `TableName` | `varchar(255)` | Não |
| `idLocked` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `LogErro`
_Tabela de log/auditoria. 16 coluna(s)_
**PK:** `idLogErro`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idLogErro` | `int(11)` | Não |
| `Modulo` | `varchar(255)` | Não |
| `Mensagem` | `varchar(255)` | Sim |
| `Sistema` | `varchar(120)` | Não |
| `idUsuario` | `int(11)` | Não |
| `Type` | `enum('ERRO','AVISO','LOG','OK')` | Sim |
| `Rota` | `varchar(255)` | Sim |
| `Usuario` | `varchar(255)` | Sim |
| `SQL` | `text` | Sim |
| `DataHora` | `timestamp` | Não |
| `JsonRetorno` | `text` | Sim |
| `Metodo` | `varchar(255)` | Sim |
| `Erro` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `LogProcessos`
_Tabela de log/auditoria. 7 coluna(s)_
**PK:** `idLogProcesso`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idLogProcesso` | `int(11)` | Não |
| `processo` | `varchar(100)` | Não |
| `etapa` | `varchar(200)` | Não |
| `variavel` | `varchar(100)` | Sim |
| `valor` | `text` | Sim |
| `idUsuario` | `int(11)` | Sim |
| `insertedAt` | `timestamp` | Não |

### `ObjetoBD`
_19 coluna(s). Relacionada a: Projeto, BancoDeDados, Empresa_
**PK:** `idObjetoBD`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idObjetoBD` | `int(11)` | Não |
| `idProjetoModulo` | `int(11)` | Sim |
| `NomeObjeto` | `varchar(255)` | Não |
| `TipoObjeto` | `enum('TABLE','VIEW','PROCEDURE','FUNCTION','TRIGGER')` | Sim |
| `Modulo` | `varchar(255)` | Sim |
| `VersaoInicial` | `varchar(20)` | Sim |
| `Comentario` | `text` | Sim |
| `ComandoCriacao` | `text` | Não |
| `ComandoAtual` | `text` | Sim |
| `DataCriacao` | `datetime` | Sim |
| `AutorCriacao` | `varchar(255)` | Sim |
| `AmbienteCriacao` | `enum('DEV','HOMOLOG','PROD')` | Sim |
| `Status` | `enum('ATIVO','INATIVO')` | Sim |
| `idBancoDeDados` | `int(11)` | Sim |
| `idProjeto` | `int(11)` | Sim |
| `idEmpresa` | `int(11)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idBancoDeDados` → `BancoDeDados.idBancoDeDados`
- `idProjeto` → `Projeto.idProjeto`
- `idEmpresa` → `Empresa.idEmpresa`
- `idProjetoModulo` → `ProjetoModulo.idProjetoModulo`

### `ObjetoBDAlteracao`
_18 coluna(s). Relacionada a: ObjetoBD_
**PK:** `idObjetoBDAlteracao`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idObjetoBDAlteracao` | `int(11)` | Não |
| `idObjetoBD` | `int(11)` | Não |
| `TipoAlteracao` | `enum('ADD_COL','MOD_COL','DEL_COL','ADD_PK','DEL_PK','ADD_UNIQUE_INDEX','DEL_UNIQUE_INDEX','ADD_FK','DEL_FK','ADD_INDEX','DEL_INDEX','ADD_TRIGGER','DEL_TRIGGER','CUSTOM_SQL')` | Sim |
| `NomeElemento` | `varchar(255)` | Sim |
| `TipoDado` | `varchar(255)` | Sim |
| `AtributosAdicionais` | `text` | Sim |
| `VersaoAplicada` | `varchar(20)` | Não |
| `DataAlteracao` | `datetime` | Sim |
| `AutorAlteracao` | `varchar(255)` | Sim |
| `AmbienteAlteracao` | `enum('DEV','HOMOLOG','PROD')` | Sim |
| `DependenciaAlteracao` | `int(11)` | Sim |
| `ComandoValidacao` | `text` | Sim |
| `ComandoRollback` | `text` | Sim |
| `ComandoSQL` | `text` | Sim |
| `Comentario` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idObjetoBD` → `ObjetoBD.idObjetoBD`

### `ObjetoBDAlteracaoPendente`
_9 coluna(s). Relacionada a: Ambiente, ObjetoBDAlteracao_
**PK:** `idObjetoBDAlteracaoPendente`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idObjetoBDAlteracaoPendente` | `int(11)` | Não |
| `idObjetoBDAlteracao` | `int(11)` | Não |
| `idAmbiente` | `int(11)` | Não |
| `Status` | `enum('PENDENTE','APROVADA','REJEITADA')` | Sim |
| `DataStatus` | `datetime` | Sim |
| `Comentario` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idAmbiente` → `Ambiente.idAmbiente`
- `idObjetoBDAlteracao` → `ObjetoBDAlteracao.idObjetoBDAlteracao`

### `ObjetoBDPendente`
_9 coluna(s). Relacionada a: Ambiente, ObjetoBD_
**PK:** `idObjetoBDPendente`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idObjetoBDPendente` | `int(11)` | Não |
| `idAmbiente` | `int(11)` | Não |
| `idObjetoBD` | `int(11)` | Não |
| `Status` | `enum('PENDENTE','APROVADA','REJEITADA')` | Sim |
| `DataStatus` | `datetime` | Sim |
| `Comentario` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idAmbiente` → `Ambiente.idAmbiente`
- `idObjetoBD` → `ObjetoBD.idObjetoBD`

### `PaginationConfig`
_Tabela de configurações/parâmetros. 7 coluna(s)_
**PK:** `id`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `id` | `int(11)` | Não |
| `module` | `varchar(255)` | Não |
| `method` | `varchar(255)` | Não |
| `records_per_page` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `Projeto`
_18 coluna(s). Relacionada a: Usuario_
**PK:** `idProjeto`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjeto` | `int(11)` | Não |
| `idEmpresa` | `int(11)` | Sim |
| `Titulo` | `varchar(60)` | Não |
| `Descricao` | `varchar(255)` | Não |
| `Status` | `enum('Aberto','Entregue','Em Andamento','Fechado','Cancelado','Suspenso')` | Sim |
| `dtTermino` | `date` | Sim |
| `vrOrcamento` | `decimal(8,2)` | Sim |
| `vrAprovado` | `decimal(8,2)` | Sim |
| `dtPrazoEstimado` | `date` | Sim |
| `qtdHorasOrcadas` | `time` | Sim |
| `qtdHorasAprovadas` | `time` | Sim |
| `dtInicio` | `date` | Sim |
| `isFavorite` | `tinyint(1)` | Não |
| `dtLastView` | `timestamp` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idUsuario` | `int(11)` | Não |

**FKs:**
- `idUsuario` → `Usuario.idUsuario`

### `ProjetoDicaTemplate`
_8 coluna(s). Relacionada a: DicaCategoria, ProjetoTemplate_
**PK:** `idProjetoDicaTemplate`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoDicaTemplate` | `int(11)` | Não |
| `idProjetoTemplate` | `int(11)` | Não |
| `Titulo` | `varchar(60)` | Não |
| `Descricao` | `longtext` | Sim |
| `idDicaCategoria` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idDicaCategoria` → `DicaCategoria.idDicaCategoria`
- `idProjetoTemplate` → `ProjetoTemplate.idProjetoTemplate`

### `ProjetoModulo`
_6 coluna(s). Relacionada a: Projeto_
**PK:** `idProjetoModulo`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoModulo` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Não |
| `Descricao` | `varchar(80)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idProjeto` → `Projeto.idProjeto`

### `ProjetoSenha`
_10 coluna(s). Relacionada a: Projeto_
**PK:** `idProjetoSenha`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoSenha` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Não |
| `Login` | `varchar(45)` | Não |
| `Senha` | `varchar(120)` | Não |
| `Titulo` | `varchar(60)` | Não |
| `Token` | `varchar(255)` | Sim |
| `Observacao` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idProjeto` → `Projeto.idProjeto`

### `ProjetoSenhaTemplate`
_10 coluna(s). Relacionada a: ProjetoTemplate_
**PK:** `idProjetoSenhaTemplate`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoSenhaTemplate` | `int(11)` | Não |
| `idProjetoTemplate` | `int(11)` | Não |
| `Login` | `varchar(45)` | Não |
| `Senha` | `varchar(120)` | Não |
| `Titulo` | `varchar(60)` | Não |
| `Token` | `varchar(255)` | Sim |
| `Observacao` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idProjetoTemplate` → `ProjetoTemplate.idProjetoTemplate`

### `ProjetoTarefaEtapaTemplate`
_6 coluna(s). Relacionada a: ProjetoTarefaTemplate_
**PK:** `idProjetoTarefaEtapaTemplate`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoTarefaEtapaTemplate` | `int(11)` | Não |
| `idProjetoTarefaTemplate` | `int(11)` | Não |
| `Titulo` | `varchar(80)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idProjetoTarefaTemplate` → `ProjetoTarefaTemplate.idProjetoTarefaTemplate`

### `ProjetoTarefaTemplate`
_11 coluna(s). Relacionada a: ProjetoTemplate, TarefaCategoria_
**PK:** `idProjetoTarefaTemplate`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoTarefaTemplate` | `int(11)` | Não |
| `idProjetoTemplate` | `int(11)` | Não |
| `Titulo` | `varchar(80)` | Não |
| `Modulo` | `varchar(60)` | Sim |
| `Descricao` | `text` | Sim |
| `idTarefaCategoria` | `int(11)` | Sim |
| `NivelComplexidade` | `enum('Baixa','Média','Alta','Muito Alta')` | Sim |
| `Prioridade` | `decimal(1,0)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idProjetoTemplate` → `ProjetoTemplate.idProjetoTemplate`
- `idTarefaCategoria` → `TarefaCategoria.idTarefaCategoria`

### `ProjetoTemplate`
_9 coluna(s). Relacionada a: Usuario, Empresa_
**PK:** `idProjetoTemplate`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoTemplate` | `int(11)` | Não |
| `idEmpresa` | `int(11)` | Sim |
| `idUsuario` | `int(11)` | Não |
| `Nome` | `varchar(60)` | Não |
| `Descricao` | `varchar(255)` | Sim |
| `isPublico` | `tinyint(1)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idUsuario` → `Usuario.idUsuario`

### `Projeto_Usuario`
_Entidade de usuário/pessoa. 8 coluna(s). Relacionada a: Projeto, Usuario_
**PK:** `idProjetoUsuario`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoUsuario` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Sim |
| `idUsuario` | `int(11)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `isFavorite` | `smallint(1)` | Sim |
| `dtLastView` | `timestamp` | Sim |

**FKs:**
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Usuario.idUsuario`

### `Scripts`
_9 coluna(s). Relacionada a: Projeto, BancoDeDados, Usuario_
**PK:** `idScripts`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idScripts` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `idBancoDeDados` | `int(11)` | Sim |
| `idProjeto` | `int(11)` | Sim |
| `Descricao` | `varchar(120)` | Sim |
| `SQL` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idBancoDeDados` → `BancoDeDados.idBancoDeDados`
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Usuario.idUsuario`

### `ScriptVersao`
_11 coluna(s). Relacionada a: VersaoBd_
**PK:** `idScriptVersao`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idScriptVersao` | `int(11)` | Não |
| `Titulo` | `varchar(90)` | Não |
| `Descricao` | `text` | Sim |
| `Ordem` | `int(11)` | Não |
| `SQL` | `text` | Sim |
| `SQLDown` | `text` | Sim |
| `Entidade` | `varchar(45)` | Sim |
| `idVersaoBd` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idVersaoBd` → `VersaoBd.idVersaoBd`

### `ScriptVersao_Ambiente`
_6 coluna(s). Relacionada a: Ambiente, ScriptVersao_
**PK:** `idScriptVersao`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idScriptVersao` | `int(11)` | Não |
| `idVersaoBd` | `int(11)` | Não |
| `idAmbiente` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idAmbiente` → `Ambiente.idAmbiente`
- `idScriptVersao` → `ScriptVersao.idScriptVersao`

### `Tarefa`
_15 coluna(s). Relacionada a: Projeto, ProjetoModulo, TarefaCategoria_
**PK:** `idTarefa`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTarefa` | `int(11)` | Não |
| `Titulo` | `varchar(80)` | Sim |
| `Modulo` | `varchar(60)` | Sim |
| `Descricao` | `text` | Sim |
| `Status` | `enum('Aberta','Em Andamento','Fechada','Atrasada','Nova','Cancelada')` | Sim |
| `Prioridade` | `decimal(1,0)` | Sim |
| `isFavorite` | `tinyint(1)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idTarefaCategoria` | `int(11)` | Sim |
| `idProjeto` | `int(11)` | Sim |
| `idUsuario` | `int(11)` | Sim |
| `NivelComplexidade` | `enum('Baixa','Média','Alta','Extrema')` | Sim |
| `idProjetoModulo` | `int(11)` | Sim |

**FKs:**
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Projeto.idUsuario`
- `idTarefaCategoria` → `TarefaCategoria.idTarefaCategoria`
- `idProjetoModulo` → `ProjetoModulo.idProjetoModulo`

### `TarefaCategoria`
_Categoria/classificação. 7 coluna(s). Relacionada a: Empresa_
**PK:** `idTarefaCategoria`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTarefaCategoria` | `int(11)` | Não |
| `Descricao` | `varchar(255)` | Não |
| `isGlobal` | `tinyint(1)` | Não |
| `idEmpresa` | `int(11)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`

### `TarefaEtapa`
_9 coluna(s). Relacionada a: Tarefa_
**PK:** `idTarefaEtapa`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTarefaEtapa` | `int(11)` | Não |
| `Titulo` | `varchar(80)` | Sim |
| `Status` | `enum('Aberta','Em Andamento','Fechada','Atrasada','Nova','Cancelada')` | Sim |
| `dtAbertura` | `date` | Sim |
| `dtTermino` | `date` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idTarefa` | `int(11)` | Não |

**FKs:**
- `idTarefa` → `Tarefa.idTarefa`

### `TemplateFile`
_11 coluna(s). Relacionada a: Projeto, Usuario, DicaLinguagem_
**PK:** `idTemplateFile`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTemplateFile` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Sim |
| `idUsuario` | `int(11)` | Não |
| `idTemplateGroup` | `int(11)` | Sim |
| `idEmpresa` | `int(11)` | Sim |
| `idDicaLinguagem` | `int(11)` | Sim |
| `Titulo` | `varchar(60)` | Não |
| `Codigo` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idDicaLinguagem` → `DicaLinguagem.idDicaLinguagem`
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Usuario.idUsuario`

### `TemplateGroup`
_9 coluna(s). Relacionada a: Projeto, Empresa, Usuario_
**PK:** `idTemplateGroup`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTemplateGroup` | `int(11)` | Não |
| `Titulo` | `varchar(60)` | Sim |
| `Descricao` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idProjeto` | `int(11)` | Sim |
| `idUsuario` | `int(11)` | Sim |
| `idEmpresa` | `int(11)` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Usuario.idUsuario`

### `TimeSheet`
_13 coluna(s). Relacionada a: TimeSheetCategoria, TimeSheetAprovacao_
**PK:** `idTimeSheet`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTimeSheet` | `int(11)` | Não |
| `idTimeSheetAprovacao` | `int(11)` | Não |
| `idTimeSheetCategoria` | `int(11)` | Sim |
| `dtInicio` | `datetime` | Não |
| `dtFim` | `datetime` | Sim |
| `horasRegistradas` | `time` | Sim |
| `Descricao` | `text` | Não |
| `Status` | `enum('Rascunho','Enviado','Aprovado','Rejeitado')` | Sim |
| `isPrevisao` | `tinyint(1)` | Sim |
| `isFaturavel` | `tinyint(1)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idTimeSheetAprovacao` → `TimeSheetAprovacao.idTimeSheetAprovacao`
- `idTimeSheetCategoria` → `TimeSheetCategoria.idTimeSheetCategoria`

### `TimeSheetAprovacao`
_25 coluna(s). Relacionada a: ValorHora, Empresa, ProjetoModulo_
**PK:** `idTimeSheetAprovacao`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTimeSheetAprovacao` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `idUsuarioAprovador` | `int(11)` | Sim |
| `idUsuarioSolicitante` | `int(11)` | Sim |
| `idProjeto` | `int(11)` | Sim |
| `idEmpresa` | `int(11)` | Sim |
| `idProjetoModulo` | `int(11)` | Sim |
| `dtSolicitacao` | `datetime` | Sim |
| `dtAprovacao` | `datetime` | Sim |
| `dtPagamento` | `datetime` | Sim |
| `Status` | `enum('Aprovado','Rejeitado','Pendente','Solicitado','Pago')` | Sim |
| `Comentario` | `text` | Sim |
| `vrSolicitado` | `decimal(10,2)` | Sim |
| `vrAprovado` | `decimal(10,2)` | Sim |
| `hrSolicitado` | `time` | Sim |
| `hrAprovado` | `time` | Sim |
| `isFaturado` | `tinyint(1)` | Sim |
| `vrHora` | `decimal(10,2)` | Sim |
| `vrTotal` | `decimal(10,2)` | Sim |
| `dtFaturamento` | `date` | Sim |
| `nroFatura` | `varchar(60)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `idValorHora` | `int(11)` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idProjeto` → `Projeto.idProjeto`
- `idProjetoModulo` → `ProjetoModulo.idProjetoModulo`
- `idUsuarioAprovador` → `Usuario.idUsuario`
- `idUsuarioSolicitante` → `Usuario.idUsuario`
- `idUsuario` → `Usuario.idUsuario`
- `idValorHora` → `ValorHora.idValorHora`

### `TimeSheetAprovacaoSolicitacao`
_10 coluna(s). Relacionada a: TimeSheetAprovacao_
**PK:** `idTimeSheetAprovacaoSolicitacao`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTimeSheetAprovacaoSolicitacao` | `int(11)` | Não |
| `idTimeSheetAprovacao` | `int(11)` | Não |
| `AprovadorEmail` | `varchar(255)` | Sim |
| `AprovadorMensagem` | `text` | Sim |
| `AprovacaoToken` | `varchar(100)` | Sim |
| `AprovacaoCodigo` | `varchar(6)` | Sim |
| `ComentarioAprovador` | `text` | Sim |
| `StatusSolicitacao` | `enum('Enviado','Acessado','Finalizado')` | Sim |
| `dtCriacao` | `timestamp` | Não |
| `PodeAlterarValor` | `tinyint(1)` | Sim |

**FKs:**
- `idTimeSheetAprovacao` → `TimeSheetAprovacao.idTimeSheetAprovacao`

### `TimeSheetCategoria`
_Categoria/classificação. 7 coluna(s). Relacionada a: Empresa_
**PK:** `idTimeSheetCategoria`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTimeSheetCategoria` | `int(11)` | Não |
| `idEmpresa` | `int(11)` | Sim |
| `Descricao` | `varchar(80)` | Não |
| `isGlobal` | `tinyint(1)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`

### `TimeSheetNotificacao`
_9 coluna(s). Relacionada a: TimeSheet, Usuario_
**PK:** `idTimeSheetNotificacao`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idTimeSheetNotificacao` | `int(11)` | Não |
| `idTimeSheet` | `int(11)` | Não |
| `idUsuarioDestino` | `int(11)` | Não |
| `Mensagem` | `text` | Não |
| `isLido` | `tinyint(1)` | Sim |
| `Tipo` | `enum('Envio','Aprovacao','Rejeicao','Lembrete','Faturamento')` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idTimeSheet` → `TimeSheet.idTimeSheet`
- `idUsuarioDestino` → `Usuario.idUsuario`

### `Usuario`
_Entidade de usuário/pessoa. 12 coluna(s)_
**PK:** `idUsuario`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuario` | `int(11)` | Não |
| `Login` | `varchar(45)` | Não |
| `Nome` | `varchar(60)` | Sim |
| `email` | `varchar(255)` | Não |
| `password` | `varchar(60)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |
| `token` | `varchar(255)` | Sim |
| `isAprovado` | `smallint(1)` | Não |
| `isRoot` | `smallint(1)` | Sim |
| `lastLogin` | `timestamp` | Sim |

### `UsuarioGrupo`
_Entidade de usuário/pessoa. 6 coluna(s)_
**PK:** `idUsuarioGrupo`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioGrupo` | `int(11)` | Não |
| `Titulo` | `varchar(45)` | Sim |
| `Descricao` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `UsuarioSenha`
_Entidade de usuário/pessoa. 26 coluna(s). Relacionada a: Usuario, UsuarioSenhaCategoria_
**PK:** `idUsuarioSenha`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioSenha` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `idUsuarioSenhaCategoria` | `int(11)` | Sim |
| `Titulo` | `varchar(100)` | Não |
| `URL` | `varchar(2048)` | Sim |
| `Login` | `varchar(255)` | Não |
| `Senha` | `varchar(2048)` | Não |
| `Email` | `varchar(255)` | Sim |
| `Categoria` | `enum('Site','App','Email','Sistema','API','Servidor','Database','Cartão','Documento','Outro')` | Sim |
| `Tags` | `varchar(255)` | Sim |
| `dtExpiracao` | `date` | Sim |
| `dtUltimaModificacao` | `timestamp` | Sim |
| `forcaSenha` | `tinyint(4)` | Sim |
| `codigoMFA` | `varchar(255)` | Sim |
| `tipoMFA` | `enum('Nenhum','TOTP','SMS','Email','App','Outro')` | Sim |
| `notasSeguras` | `text` | Sim |
| `camposPersonalizados` | `longtext` | Sim |
| `iconePath` | `varchar(255)` | Sim |
| `isFavorito` | `tinyint(1)` | Sim |
| `isCompartilhada` | `tinyint(1)` | Sim |
| `metodoEncriptacao` | `varchar(50)` | Sim |
| `Observacao` | `text` | Sim |
| `Detalhes` | `text` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idUsuario` → `Usuario.idUsuario`
- `idUsuarioSenhaCategoria` → `UsuarioSenhaCategoria.idUsuarioSenhaCategoria`

### `UsuarioSenhaAcesso`
_Entidade de usuário/pessoa. 7 coluna(s). Relacionada a: UsuarioSenha, Usuario_
**PK:** `idUsuarioSenhaAcesso`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioSenhaAcesso` | `int(11)` | Não |
| `idUsuarioSenha` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `tipoAcesso` | `enum('Visualização','Cópia','Edição','Exclusão','Compartilhamento','Restauração')` | Não |
| `dataAcesso` | `timestamp` | Não |
| `ipAcesso` | `varchar(45)` | Sim |
| `dispositivo` | `varchar(255)` | Sim |

**FKs:**
- `idUsuario` → `Usuario.idUsuario`
- `idUsuarioSenha` → `UsuarioSenha.idUsuarioSenha`

### `UsuarioSenhaCategoria`
_Entidade de usuário/pessoa. 9 coluna(s). Relacionada a: Usuario_
**PK:** `idUsuarioSenhaCategoria`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioSenhaCategoria` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `Nome` | `varchar(100)` | Não |
| `Descricao` | `varchar(255)` | Sim |
| `Cor` | `varchar(7)` | Sim |
| `Icone` | `varchar(50)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idUsuario` → `Usuario.idUsuario`

### `UsuarioSenhaCompartilhamento`
_Entidade de usuário/pessoa. 10 coluna(s). Relacionada a: UsuarioSenha, Usuario_
**PK:** `idUsuarioSenhaCompartilhamento`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioSenhaCompartilhamento` | `int(11)` | Não |
| `idUsuarioSenha` | `int(11)` | Não |
| `idUsuarioCompartilhado` | `int(11)` | Não |
| `nivelAcesso` | `enum('Somente leitura','Leitura e uso','Edição','Controle total')` | Sim |
| `dataInicio` | `datetime` | Não |
| `dataExpiracao` | `datetime` | Sim |
| `notificacaoUso` | `tinyint(1)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idUsuarioCompartilhado` → `Usuario.idUsuario`
- `idUsuarioSenha` → `UsuarioSenha.idUsuarioSenha`

### `UsuarioSenhaHistorico`
_Tabela de log/auditoria. 5 coluna(s). Relacionada a: UsuarioSenha_
**PK:** `idUsuarioSenhaHistorico`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioSenhaHistorico` | `int(11)` | Não |
| `idUsuarioSenha` | `int(11)` | Não |
| `SenhaAntiga` | `varchar(2048)` | Não |
| `dataAlteracao` | `timestamp` | Não |
| `motivoAlteracao` | `varchar(255)` | Sim |

**FKs:**
- `idUsuarioSenha` → `UsuarioSenha.idUsuarioSenha`

### `Usuario_Empresa`
_Entidade de usuário/pessoa. 6 coluna(s). Relacionada a: Usuario, Empresa_
**PK:** `idUsuarioEmpresa`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioEmpresa` | `int(11)` | Não |
| `idEmpresa` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idUsuario` → `Usuario.idUsuario`

### `ValorHora`
_11 coluna(s). Relacionada a: Projeto, Empresa, Usuario_
**PK:** `idValorHora`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idValorHora` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Sim |
| `idEmpresa` | `int(11)` | Sim |
| `vrHora` | `decimal(10,2)` | Não |
| `dataInicio` | `date` | Não |
| `dataFim` | `date` | Sim |
| `descricao` | `varchar(120)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idEmpresa` → `Empresa.idEmpresa`
- `idProjeto` → `Projeto.idProjeto`
- `idUsuario` → `Usuario.idUsuario`

### `VersaoBd`
_9 coluna(s). Relacionada a: BancoDeDados_
**PK:** `idVersaoBd`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idVersaoBd` | `int(11)` | Não |
| `idBancoDeDados` | `int(11)` | Não |
| `Nome` | `varchar(45)` | Sim |
| `NroVersao` | `varchar(45)` | Sim |
| `dtVersao` | `date` | Sim |
| `isAtiva` | `smallint(6)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idBancoDeDados` → `BancoDeDados.idBancoDeDados`

### `VersaoSistema`
_9 coluna(s). Relacionada a: VersaoBd_
**PK:** `idVersaoSistema`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idVersaoSistema` | `int(11)` | Não |
| `Nome` | `varchar(45)` | Sim |
| `NroVersao` | `varchar(45)` | Sim |
| `dtVersao` | `varchar(45)` | Sim |
| `isAtiva` | `smallint(6)` | Sim |
| `idVersaoBd` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

**FKs:**
- `idVersaoBd` → `VersaoBd.idVersaoBd`

## Relacionamentos
| Origem | Coluna FK | Destino | Coluna ref. | Constraint |
|--------|-----------|---------|-------------|------------|
| `Ambiente` | `idBancoDeDados` | `BancoDeDados` | `idBancoDeDados` | `fk_Ambiente_BancoDeDados1` |
| `BancoDeDados` | `idProjeto` | `Projeto` | `idProjeto` | `BancoDeDados_ibfk_1` |
| `BancoDeDados` | `idEmpresa` | `Empresa` | `idEmpresa` | `BancoDeDados_ibfk_2` |
| `Dica` | `idDicaCategoria` | `DicaCategoria` | `idDicaCategoria` | `fk_Dica_DicasCategoria1` |
| `Dica` | `idProjeto` | `Projeto` | `idProjeto` | `fk_Dica_Projeto1` |
| `Dica` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Dica_Usuario1` |
| `DicaCategoria` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_DicaCategoria_Empresa1` |
| `DicaCodigo` | `idDica` | `Dica` | `idDica` | `fk_DicaCodigo_Dica1` |
| `DicaCodigo` | `idDicaLinguagem` | `DicaLinguagem` | `idDicaLinguagem` | `fk_DicaCodigo_DicaLinguagem` |
| `DicaComentario` | `idDica` | `Dica` | `idDica` | `fk_DicaComentario_Dica1` |
| `DicaComentario` | `idUsuario` | `Usuario` | `idUsuario` | `fk_DicaComentario_Usuario1` |
| `Empresa` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Empresa_Usuario1` |
| `EmpresaConvite` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_EmpresaConvite_Empresa1` |
| `EmpresaConvite` | `idUsuario` | `Usuario` | `idUsuario` | `fk_EmpresaConvite_Usuario1` |
| `EmpresaDica` | `idDicaCategoria` | `DicaCategoria` | `idDicaCategoria` | `fk_EmpresaDica_DicaCategoria1` |
| `EmpresaDica` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_EmpresaDica_Empresa1` |
| `EmpresaSenha` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_EmpresaSenha_Empresa1` |
| `EmpresaSenha` | `idUsuario` | `Usuario` | `idUsuario` | `fk_EmpresaSenha_Usuario1` |
| `ObjetoBD` | `idBancoDeDados` | `BancoDeDados` | `idBancoDeDados` | `ObjetoBD_ibfk_1` |
| `ObjetoBD` | `idProjeto` | `Projeto` | `idProjeto` | `ObjetoBD_ibfk_2` |
| `ObjetoBD` | `idEmpresa` | `Empresa` | `idEmpresa` | `ObjetoBD_ibfk_3` |
| `ObjetoBD` | `idProjetoModulo` | `ProjetoModulo` | `idProjetoModulo` | `fk_objetobd_projetomodulo1` |
| `ObjetoBDAlteracao` | `idObjetoBD` | `ObjetoBD` | `idObjetoBD` | `ObjetoBDAlteracao_ibfk_1` |
| `ObjetoBDAlteracaoPendente` | `idAmbiente` | `Ambiente` | `idAmbiente` | `fk_AlteracaoPendente_Ambiente1` |
| `ObjetoBDAlteracaoPendente` | `idObjetoBDAlteracao` | `ObjetoBDAlteracao` | `idObjetoBDAlteracao` | `fk_AlteracaoPendente_ObjetoBDAlteracao1` |
| `ObjetoBDPendente` | `idAmbiente` | `Ambiente` | `idAmbiente` | `fk_ObjetoBDPendente_Ambiente1` |
| `ObjetoBDPendente` | `idObjetoBD` | `ObjetoBD` | `idObjetoBD` | `fk_ObjetoBDPendente_ObjetoBD1` |
| `Projeto` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Projeto_Usuario1` |
| `ProjetoDicaTemplate` | `idDicaCategoria` | `DicaCategoria` | `idDicaCategoria` | `fk_ProjetoDicaTemplate_DicaCategoria1` |
| `ProjetoDicaTemplate` | `idProjetoTemplate` | `ProjetoTemplate` | `idProjetoTemplate` | `fk_ProjetoDicaTemplate_ProjetoTemplate1` |
| `ProjetoModulo` | `idProjeto` | `Projeto` | `idProjeto` | `fk_ProjetoModulo_Projeto1` |
| `ProjetoSenha` | `idProjeto` | `Projeto` | `idProjeto` | `fk_ProjetoSenha_Projeto1` |
| `ProjetoSenhaTemplate` | `idProjetoTemplate` | `ProjetoTemplate` | `idProjetoTemplate` | `fk_ProjetoSenhaTemplate_ProjetoTemplate1` |
| `ProjetoTarefaEtapaTemplate` | `idProjetoTarefaTemplate` | `ProjetoTarefaTemplate` | `idProjetoTarefaTemplate` | `fk_ProjetoTarefaEtapaTemplate_ProjetoTarefaTemplate1` |
| `ProjetoTarefaTemplate` | `idProjetoTemplate` | `ProjetoTemplate` | `idProjetoTemplate` | `fk_ProjetoTarefaTemplate_ProjetoTemplate1` |
| `ProjetoTarefaTemplate` | `idTarefaCategoria` | `TarefaCategoria` | `idTarefaCategoria` | `fk_ProjetoTarefaTemplate_TarefaCategoria1` |
| `ProjetoTemplate` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_ProjetoTemplate_Empresa1` |
| `ProjetoTemplate` | `idUsuario` | `Usuario` | `idUsuario` | `fk_ProjetoTemplate_Usuario1` |
| `Projeto_Usuario` | `idProjeto` | `Projeto` | `idProjeto` | `fk_Projeto_Usuario_Projeto1` |
| `Projeto_Usuario` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Projeto_Usuario_Usuario1` |
| `Scripts` | `idBancoDeDados` | `BancoDeDados` | `idBancoDeDados` | `fk_Scripts_BancoDeDados1` |
| `Scripts` | `idProjeto` | `Projeto` | `idProjeto` | `fk_Scripts_Projeto1` |
| `Scripts` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Scripts_Usuario1` |
| `ScriptVersao` | `idVersaoBd` | `VersaoBd` | `idVersaoBd` | `fk_ScriptVersao_VersaoBd1` |
| `ScriptVersao_Ambiente` | `idAmbiente` | `Ambiente` | `idAmbiente` | `fk_ScriptVersao_Ambiente_Ambiente1` |
| `ScriptVersao_Ambiente` | `idScriptVersao` | `ScriptVersao` | `idScriptVersao` | `fk_ScriptVersao_Ambiente_ScriptVersao1` |
| `Tarefa` | `idProjeto` | `Projeto` | `idProjeto` | `fk_Tarefa_Projeto1` |
| `Tarefa` | `idUsuario` | `Projeto` | `idUsuario` | `fk_Tarefa_Projeto1` |
| `Tarefa` | `idTarefaCategoria` | `TarefaCategoria` | `idTarefaCategoria` | `fk_Tarefa_TarefaCategoria1` |
| `Tarefa` | `idProjetoModulo` | `ProjetoModulo` | `idProjetoModulo` | `fk_tarefa_projetomodulo1` |
| `TarefaCategoria` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_TarefaCategoria_Empresa1` |
| `TarefaEtapa` | `idTarefa` | `Tarefa` | `idTarefa` | `fk_TarefaEtapa_Tarefa1` |
| `TemplateFile` | `idDicaLinguagem` | `DicaLinguagem` | `idDicaLinguagem` | `fk_TemplateFile_DicaLinguagem1` |
| `TemplateFile` | `idProjeto` | `Projeto` | `idProjeto` | `fk_Template_Projeto1` |
| `TemplateFile` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Template_Usuario1` |
| `TemplateGroup` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_TemplateGroup_Empresa1` |
| `TemplateGroup` | `idProjeto` | `Projeto` | `idProjeto` | `fk_TemplateGroup_Projeto1` |
| `TemplateGroup` | `idUsuario` | `Usuario` | `idUsuario` | `fk_TemplateGroup_Usuario1` |
| `TimeSheet` | `idTimeSheetAprovacao` | `TimeSheetAprovacao` | `idTimeSheetAprovacao` | `fk_TimeSheet_TimeSheetAprovacao1` |
| `TimeSheet` | `idTimeSheetCategoria` | `TimeSheetCategoria` | `idTimeSheetCategoria` | `fk_TimeSheet_TimeSheetCategoria1` |
| `TimeSheetAprovacao` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_TimeSheetAprovacao_Empresa1` |
| `TimeSheetAprovacao` | `idProjeto` | `Projeto` | `idProjeto` | `fk_TimeSheetAprovacao_Projeto1` |
| `TimeSheetAprovacao` | `idProjetoModulo` | `ProjetoModulo` | `idProjetoModulo` | `fk_TimeSheetAprovacao_ProjetoModulo1` |
| `TimeSheetAprovacao` | `idUsuarioAprovador` | `Usuario` | `idUsuario` | `fk_TimeSheetAprovacao_Usuario1` |
| `TimeSheetAprovacao` | `idUsuarioSolicitante` | `Usuario` | `idUsuario` | `fk_TimeSheetAprovacao_Usuario2` |
| `TimeSheetAprovacao` | `idUsuario` | `Usuario` | `idUsuario` | `fk_TimeSheetAprovacao_Usuario3` |
| `TimeSheetAprovacao` | `idValorHora` | `ValorHora` | `idValorHora` | `fk_TimeSheetAprovacao_ValorHora` |
| `TimeSheetAprovacaoSolicitacao` | `idTimeSheetAprovacao` | `TimeSheetAprovacao` | `idTimeSheetAprovacao` | `fk_TSA_Solicitacao` |
| `TimeSheetCategoria` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_TimeSheetCategoria_Empresa1` |
| `TimeSheetNotificacao` | `idTimeSheet` | `TimeSheet` | `idTimeSheet` | `fk_TimeSheetNotificacao_TimeSheet1` |
| `TimeSheetNotificacao` | `idUsuarioDestino` | `Usuario` | `idUsuario` | `fk_TimeSheetNotificacao_Usuario1` |
| `UsuarioSenha` | `idUsuario` | `Usuario` | `idUsuario` | `fk_UsuarioSenha_Usuario1` |
| `UsuarioSenha` | `idUsuarioSenhaCategoria` | `UsuarioSenhaCategoria` | `idUsuarioSenhaCategoria` | `fk_UsuarioSenha_UsuarioSenhaCategoria1` |
| `UsuarioSenhaAcesso` | `idUsuario` | `Usuario` | `idUsuario` | `fk_UsuarioSenhaAcesso_Usuario1` |
| `UsuarioSenhaAcesso` | `idUsuarioSenha` | `UsuarioSenha` | `idUsuarioSenha` | `fk_UsuarioSenhaAcesso_UsuarioSenha1` |
| `UsuarioSenhaCategoria` | `idUsuario` | `Usuario` | `idUsuario` | `fk_UsuarioSenhaCategoria_Usuario1` |
| `UsuarioSenhaCompartilhamento` | `idUsuarioCompartilhado` | `Usuario` | `idUsuario` | `fk_UsuarioSenhaCompartilhamento_Usuario1` |
| `UsuarioSenhaCompartilhamento` | `idUsuarioSenha` | `UsuarioSenha` | `idUsuarioSenha` | `fk_UsuarioSenhaCompartilhamento_UsuarioSenha1` |
| `UsuarioSenhaHistorico` | `idUsuarioSenha` | `UsuarioSenha` | `idUsuarioSenha` | `fk_UsuarioSenhaHistorico_UsuarioSenha1` |
| `Usuario_Empresa` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_Usuario_Empresa_Empresa1` |
| `Usuario_Empresa` | `idUsuario` | `Usuario` | `idUsuario` | `fk_Usuario_Empresa_Usuario1` |
| `ValorHora` | `idEmpresa` | `Empresa` | `idEmpresa` | `fk_ValorHora_Empresa1` |
| `ValorHora` | `idProjeto` | `Projeto` | `idProjeto` | `fk_ValorHora_Projeto1` |
| `ValorHora` | `idUsuario` | `Usuario` | `idUsuario` | `fk_ValorHora_Usuario1` |
| `VersaoBd` | `idBancoDeDados` | `BancoDeDados` | `idBancoDeDados` | `fk_VersaoBd_BancoDeDados1` |
| `VersaoSistema` | `idVersaoBd` | `VersaoBd` | `idVersaoBd` | `fk_VersaoSistema_VersaoBd1` |

## Views
- `AmbientesSemObjetosVw` — 9 coluna(s)
- `DicaCodigoVw` — 10 coluna(s)
- `DicaVw` — 10 coluna(s)
- `EmpresaDicaVw` — 11 coluna(s)
- `EmpresaOfUsuarioVw` — Entidade de usuário/pessoa. 9 coluna(s)
- `EmpresaUsuarioVw` — Entidade de usuário/pessoa. 7 coluna(s)
- `EmpresaVw` — 7 coluna(s)
- `EstatisticasPorAmbienteVw` — 9 coluna(s)
- `ObjetoBDAlteracaoPendenteVw` — 26 coluna(s)
- `ObjetoBDPendenteOrfaosVw` — 18 coluna(s)
- `ObjetoBDPendenteVw` — 23 coluna(s)
- `ProjetoAtivosVw` — 23 coluna(s)
- `ProjetoEncerradosVw` — 23 coluna(s)
- `ProjetoEntreguesVw` — 23 coluna(s)
- `ProjetoMembroFavoritoVw` — Entidade de usuário/pessoa. 26 coluna(s)
- `ProjetoQtdResumoVw` — 9 coluna(s)
- `ProjetoQtdVw` — 6 coluna(s)
- `ProjetoStatusVw` — 8 coluna(s)
- `ProjetoUsuarioFavoritoVw` — Entidade de usuário/pessoa. 26 coluna(s)
- `ProjetoVw` — 24 coluna(s)
- `Projeto_UsuarioVw` — Entidade de usuário/pessoa. 8 coluna(s)
- `qtdObjetoBDAmbienteVw` — 5 coluna(s)
- `qtdObjetoBDOrfaosVw` — 2 coluna(s)
- `TarefaDetailVw` — 23 coluna(s)
- `TarefaEtapaQtdVw` — 7 coluna(s)
- `TarefaQtdVw` — 5 coluna(s)
- `TarefaStatusCountVw` — 11 coluna(s)
- `TarefaStatusEmpresaCountVw` — 10 coluna(s)
- `TarefaVw` — 13 coluna(s)
- `TemplateFileVw` — 13 coluna(s)
- `TemplateGroupVw` — 12 coluna(s)
- `TimeSheetAprovacaoVw` — 29 coluna(s)
- `UsuarioEmpresaVw` — Entidade de usuário/pessoa. 15 coluna(s)
- `vwEmpresasUsuarioAtividade` — Entidade de usuário/pessoa. 9 coluna(s)

## Triggers
- `after_insert_ObjetoBDAlteracao1` (AFTER INSERT ON `ObjetoBDAlteracao`)
- `trg_ScriptVersao_bi1` (BEFORE INSERT ON `ScriptVersao`)
- `trg_timesheet_bi1_calcular_valor` (BEFORE INSERT ON `TimeSheet`)
- `trg_timesheet_bu1_calcular_valor` (BEFORE UPDATE ON `TimeSheet`)
- `trt_timesheet_ad1_atualizar_horas` (AFTER DELETE ON `TimeSheet`)
- `trg_timesheetaprovacao_bi1_validar_dados` (BEFORE INSERT ON `TimeSheetAprovacao`)
- `trg_timesheetaprovacao_bu1_validar_atualizar` (BEFORE UPDATE ON `TimeSheetAprovacao`)
- `trg_timesheetaprovacao_au1_atualizar_detalhes` (AFTER UPDATE ON `TimeSheetAprovacao`)
- `trg_timesheetaprovacao_ad1_desassociar_timesheet` (AFTER DELETE ON `TimeSheetAprovacao`)
- `before_insert_Usuario_Empresa1` (BEFORE INSERT ON `Usuario_Empresa`)
- `trg_valorhora_bi` (BEFORE INSERT ON `ValorHora`)
- `trg_valorhora_bu` (BEFORE UPDATE ON `ValorHora`)
- `trg_valorhora_bd` (BEFORE DELETE ON `ValorHora`)

## Procedures
- `sp_CleanOldLocks`
- `sp_CriarProjetoPorTemplate`
- `sp_GetLockedRecords`
- `sp_LockRecordByTrigger`
- `sp_LogProcesso`
- `sp_RecalcularTimeSheetAprovacao`
- `sp_ReordenarScriptVersao`
- `sp_UnlockRecordByTrigger`

## Functions
- `fn_GerarScriptUpgrade`
- `fn_GetValorHoraAtivo`
- `fn_IsRecordLocked`