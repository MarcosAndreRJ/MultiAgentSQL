# DB Digest — devhacks_site
**Agente:** `mysql-mockup`  
**Banco:** `devhacks_site`  
**Gerado em:** 2026-03-24 12:17:53 UTC  

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
_8 coluna(s)_
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

### `BancoDeDados`
_13 coluna(s)_
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

### `Dica`
_10 coluna(s)_
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

### `DicaCategoria`
_Categoria/classificação. 7 coluna(s)_
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

### `DicaCodigo`
_9 coluna(s)_
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

### `DicaComentario`
_7 coluna(s)_
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
_6 coluna(s)_
**PK:** `idEmpresa`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idEmpresa` | `int(11)` | Não |
| `Nome` | `varchar(60)` | Sim |
| `RazaoSocial` | `varchar(120)` | Sim |
| `Site` | `varchar(225)` | Sim |
| `CNPJ` | `varchar(14)` | Sim |
| `idUsuario` | `int(11)` | Não |

### `EmpresaConvite`
_12 coluna(s)_
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

### `EmpresaDica`
_10 coluna(s)_
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

### `EmpresaSenha`
_12 coluna(s)_
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
_19 coluna(s)_
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

### `ObjetoBDAlteracao`
_18 coluna(s)_
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

### `ObjetoBDAlteracaoPendente`
_9 coluna(s)_
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

### `ObjetoBDPendente`
_9 coluna(s)_
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
_18 coluna(s)_
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

### `ProjetoDicaTemplate`
_8 coluna(s)_
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

### `ProjetoModulo`
_6 coluna(s)_
**PK:** `idProjetoModulo`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoModulo` | `int(11)` | Não |
| `idProjeto` | `int(11)` | Não |
| `Descricao` | `varchar(80)` | Sim |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `ProjetoSenha`
_10 coluna(s)_
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

### `ProjetoSenhaTemplate`
_10 coluna(s)_
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

### `ProjetoTarefaEtapaTemplate`
_6 coluna(s)_
**PK:** `idProjetoTarefaEtapaTemplate`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idProjetoTarefaEtapaTemplate` | `int(11)` | Não |
| `idProjetoTarefaTemplate` | `int(11)` | Não |
| `Titulo` | `varchar(80)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `ProjetoTarefaTemplate`
_11 coluna(s)_
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

### `ProjetoTemplate`
_9 coluna(s)_
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

### `Projeto_Usuario`
_Entidade de usuário/pessoa. 8 coluna(s)_
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

### `ScriptVersao`
_11 coluna(s)_
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

### `ScriptVersao_Ambiente`
_6 coluna(s)_

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idScriptVersao` | `int(11)` | Não |
| `idVersaoBd` | `int(11)` | Não |
| `idAmbiente` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `Scripts`
_9 coluna(s)_
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

### `Tarefa`
_15 coluna(s)_
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

### `TarefaCategoria`
_Categoria/classificação. 7 coluna(s)_
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

### `TarefaEtapa`
_9 coluna(s)_
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

### `TemplateFile`
_11 coluna(s)_
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

### `TemplateGroup`
_9 coluna(s)_
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

### `TimeSheet`
_13 coluna(s)_
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

### `TimeSheetAprovacao`
_25 coluna(s)_
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

### `TimeSheetAprovacaoSolicitacao`
_10 coluna(s)_
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

### `TimeSheetCategoria`
_Categoria/classificação. 7 coluna(s)_
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

### `TimeSheetNotificacao`
_9 coluna(s)_
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
_Entidade de usuário/pessoa. 26 coluna(s)_
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

### `UsuarioSenhaAcesso`
_Entidade de usuário/pessoa. 7 coluna(s)_
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

### `UsuarioSenhaCategoria`
_Entidade de usuário/pessoa. 9 coluna(s)_
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

### `UsuarioSenhaCompartilhamento`
_Entidade de usuário/pessoa. 10 coluna(s)_
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

### `UsuarioSenhaHistorico`
_Tabela de log/auditoria. 5 coluna(s)_
**PK:** `idUsuarioSenhaHistorico`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioSenhaHistorico` | `int(11)` | Não |
| `idUsuarioSenha` | `int(11)` | Não |
| `SenhaAntiga` | `varchar(2048)` | Não |
| `dataAlteracao` | `timestamp` | Não |
| `motivoAlteracao` | `varchar(255)` | Sim |

### `Usuario_Empresa`
_Entidade de usuário/pessoa. 6 coluna(s)_
**PK:** `idUsuarioEmpresa`

| Coluna | Tipo | Nullable |
|--------|------|----------|
| `idUsuarioEmpresa` | `int(11)` | Não |
| `idEmpresa` | `int(11)` | Não |
| `idUsuario` | `int(11)` | Não |
| `insertedAt` | `timestamp` | Não |
| `updatedAt` | `timestamp` | Sim |
| `deletedAt` | `timestamp` | Sim |

### `ValorHora`
_11 coluna(s)_
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

### `VersaoBd`
_9 coluna(s)_
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

### `VersaoSistema`
_9 coluna(s)_

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
- `qtdObjetoBDAmbienteVw` — 5 coluna(s)
- `qtdObjetoBDOrfaosVw` — 2 coluna(s)
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