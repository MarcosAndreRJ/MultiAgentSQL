import pytest
from unittest.mock import MagicMock, patch
from app.services.sql_direct_service import is_sql_direct, execute_direct
from app.schemas.chat import Session

def test_is_sql_direct():
    assert is_sql_direct("SELECT * FROM table") is True
    assert is_sql_direct("  select id from x") is True
    assert is_sql_direct("SHOW TABLES") is True
    assert is_sql_direct("execsql: SELECT 1") is True
    assert is_sql_direct("Qual o status do projeto?") is False
    assert is_sql_direct("Me mostre os logs") is False

@pytest.mark.asyncio
async def test_execute_direct_select_with_alias():
    agent_id = "mysql-expert"
    session = Session(session_id="sess_123", agent_id=agent_id)
    run_id = "run_123"
    message = "SELECT * FROM @Projeto"
    
    # Mocking
    mock_config = MagicMock()
    mock_config.database = MagicMock()
    
    with patch("app.core.agent_registry.get", return_value=mock_config), \
         patch("app.services.alias_service.load_aliases") as mock_load, \
         patch("app.tools.db_execute.execute") as mock_exec:
        
        # Simular alias @Projeto -> ProjetoReal
        mock_data = MagicMock()
        mock_data.aliases = {"@Projeto": "ProjetoReal"}
        mock_data.manual_aliases = {}
        mock_load.return_value = mock_data
        
        # Simular resultado do banco
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rows = [{"id": 1, "nome": "Teste"}]
        mock_result.model_dump.return_value = {"success": True}
        mock_exec.return_value = mock_result
        
        response = await execute_direct(agent_id, message, session, run_id)
        
        assert response is not None
        assert response.status == "completed"
        assert "SELECT * FROM ProjetoReal" in response.sql_executed
        assert "Executei o SQL informado diretamente" in response.response

@pytest.mark.asyncio
async def test_execute_direct_guard_block():
    agent_id = "mysql-expert"
    session = Session(session_id="sess_123", agent_id=agent_id)
    run_id = "run_123"
    message = "DROP TABLE Projeto"
    
    mock_config = MagicMock()
    mock_config.database = MagicMock()
    
    with patch("app.core.agent_registry.get", return_value=mock_config), \
         patch("app.services.alias_service.load_aliases", return_value=None), \
         patch("app.tools.db_execute.execute") as mock_exec:
        
        # Simular bloqueio pelo guard
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Comando perigoso bloqueado pela política de segurança (GUARD)"
        mock_exec.return_value = mock_result
        
        response = await execute_direct(agent_id, message, session, run_id)
        
        assert response is not None
        assert response.status == "error"
        assert "bloqueado pela política de segurança" in response.response
