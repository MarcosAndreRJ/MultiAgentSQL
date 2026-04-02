import pytest
from unittest.mock import MagicMock, patch
from app.services.nl_sql_fastpath_service import translate_and_execute
from app.schemas.chat import Session

@pytest.mark.asyncio
async def test_translate_simple_select():
    agent_id = "mysql-expert"
    session = Session(session_id="sess_123", agent_id=agent_id)
    run_id = "run_123"
    message = "Liste Titulo, Descricao de @Projeto"
    
    # Mocks
    mock_config = MagicMock()
    mock_config.database = MagicMock()
    
    with patch("app.services.nl_sql_fastpath_service.agent_registry.get", return_value=mock_config), \
         patch("app.services.nl_sql_fastpath_service.load_digest") as mock_digest, \
         patch("app.services.nl_sql_fastpath_service.resolve_message_aliases") as mock_resolve, \
         patch("app.services.nl_sql_fastpath_service.db_execute.execute") as mock_exec:
        
        # Simular alias @Projeto -> Projeto
        # Agora o serviço normaliza tokens para lowercase na comparação, mas o mock deve retornar o que resolve_message_aliases retornaria
        mock_resolve.return_value = ("Liste Titulo, Descricao de Projeto", {"@Projeto": "Projeto"})
        
        # Simular digest
        mock_table = MagicMock()
        mock_table.name = "Projeto"
        mock_col1 = MagicMock(); mock_col1.name = "Titulo"
        mock_col2 = MagicMock(); mock_col2.name = "Descricao"
        mock_table.columns = [mock_col1, mock_col2]
        
        digest = MagicMock()
        digest.tables = [mock_table]
        digest.views = []
        mock_digest.return_value = digest
        
        # Simular resultado do banco
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rows = [{"Titulo": "P1", "Descricao": "D1"}]
        mock_result.model_dump.return_value = {"success": True}
        mock_exec.return_value = mock_result
        
        response = await translate_and_execute(agent_id, message, session, run_id)
        
        assert response is not None
        assert response.status == "completed"
        assert "SELECT `Titulo`, `Descricao` FROM `Projeto`" in response.sql_executed
        assert "Traduzi sua solicitação para SQL" in response.response

@pytest.mark.asyncio
async def test_translate_with_join():
    agent_id = "mysql-expert"
    message = "Liste @Projeto, @Empresa"
    session = Session(session_id="sess_123", agent_id=agent_id)
    run_id = "run_123"
    
    with patch("app.services.nl_sql_fastpath_service.agent_registry.get"), \
         patch("app.services.nl_sql_fastpath_service.load_digest") as mock_digest, \
         patch("app.services.nl_sql_fastpath_service.resolve_message_aliases") as mock_resolve, \
         patch("app.services.nl_sql_fastpath_service.join_resolver.resolve_join") as mock_join, \
         patch("app.services.nl_sql_fastpath_service.db_execute.execute") as mock_exec:
        
        mock_resolve.return_value = ("Liste Projeto, Empresa", {"@Projeto": "Projeto", "@Empresa": "Empresa"})
        
        # Mock Join
        from app.services.join_resolver import JoinPath
        mock_join.return_value = JoinPath(
            left_table="Projeto", right_table="Empresa", 
            left_col="idEmpresa", right_col="idEmpresa",
            direction="direct", confidence=1.0
        )
        
        # Simular digest com as colunas necessárias
        mock_table_p = MagicMock(); mock_table_p.name = "Projeto"
        mock_table_e = MagicMock(); mock_table_e.name = "Empresa"
        # Adicionar colunas PK/FK para o mock
        c1 = MagicMock(); c1.name = "idEmpresa"
        mock_table_p.columns = [c1]
        mock_table_e.columns = [c1]
        
        digest = MagicMock()
        digest.tables = [mock_table_p, mock_table_e]
        digest.views = []
        mock_digest.return_value = digest
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.model_dump.return_value = {}
        mock_exec.return_value = mock_result
        
        response = await translate_and_execute(agent_id, message, session, run_id)
        
        # Normalizar espaços para evitar erro de newline
        sql = response.sql_executed.replace("\n", " ").replace("  ", " ")
        assert "INNER JOIN `Empresa` ON `Projeto`.`idEmpresa` = `Empresa`.`idEmpresa`" in sql
