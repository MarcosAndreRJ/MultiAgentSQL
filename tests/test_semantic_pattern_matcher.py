import pytest
import re
from unittest.mock import MagicMock, patch

from app.schemas.semantic import SemanticPattern, PatternFilter
from app.services.semantic.pattern_matcher import match_and_execute
from app.schemas.agent import AgentConfig, AgentBehavior
from app.schemas.chat import Session

@pytest.fixture
def mock_agent():
    return AgentConfig(
        id="test_agent",
        type="database",
        name="Test",
        behavior=AgentBehavior(),
        model="gpt-4",
        db_connection_id="db_1"
    )

@pytest.fixture
def mock_session():
    return Session(session_id="session_1")

@pytest.fixture
def sample_pattern():
    return SemanticPattern(
        id="ptn_123",
        agent_id="test_agent",
        intent_family="SELECT",
        mode="list",
        tables=["Projeto"],
        filters=[
            PatternFilter(field="status", op="=", slot_name="p0", slot_value="suspenso")
        ],
        sql_template="SELECT * FROM `Projeto` WHERE `status` = %(p0)s LIMIT 50",
        examples=[]
    )

@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@patch("app.services.semantic.pattern_matcher.db_execute.execute")
@pytest.mark.asyncio
async def test_successful_match_different_value(
    mock_execute, mock_parse_slots, mock_find_tables, mock_resolve_aliases, 
    mock_load_digest, mock_load_patterns, mock_agent, mock_session, sample_pattern
):
    """1. match bem-sucedido com mesmo pattern e valor diferente (slot extraction e sql preenchido)"""
    mock_load_patterns.return_value = [sample_pattern]
    mock_load_digest.return_value = MagicMock()
    mock_resolve_aliases.return_value = ("liste projetos em execução", [])
    mock_find_tables.return_value = ["Projeto"]
    
    # Mock do parse_slots: mesmo campo, novo valor
    mock_slots = MagicMock()
    mock_slots.filters = [
        MagicMock(field="status", op="=", value="execução")
    ]
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    # Mock execution success
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.rows = [{"id": 1, "nome": "Proj X"}]
    mock_execute.return_value = mock_result

    with patch("app.services.semantic.pattern_matcher.update_pattern_usage") as mock_update:
        result = await match_and_execute(mock_agent, "liste projetos em execução", mock_session)
        
        assert result is not None
        assert result.intent == "SEMANTIC_SELECT"
        
        # 4. Slot extraction funcionou e 5. Sql preenchido (verificando params chamados no DBExecuteRequest)
        args, kwargs = mock_execute.call_args
        req = args[0]
        assert req.sql == sample_pattern.sql_template
        assert req.params == {"p0": "execução"}  # Slot preenchido corretamente
        mock_update.assert_called_with("test_agent", "ptn_123", success=True)


@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@pytest.mark.asyncio
async def test_miss_different_table(
    mock_parse_slots, mock_find_tables, mock_resolve_aliases, 
    mock_load_digest, mock_load_patterns, mock_agent, mock_session, sample_pattern
):
    """2. miss quando a tabela for diferente"""
    mock_load_patterns.return_value = [sample_pattern]
    mock_load_digest.return_value = MagicMock()
    mock_resolve_aliases.return_value = ("liste usuarios", [])
    mock_find_tables.return_value = ["Usuario"]  # Tabela diferente de "Projeto"
    
    mock_slots = MagicMock()
    mock_slots.filters = [MagicMock(field="status", op="=", value="ativo")]
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    result = await match_and_execute(mock_agent, "liste usuarios", mock_session)
    assert result is None  # 7. fallback quando pattern não for aplicável


@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@pytest.mark.asyncio
async def test_miss_different_filter_structure(
    mock_parse_slots, mock_find_tables, mock_resolve_aliases, 
    mock_load_digest, mock_load_patterns, mock_agent, mock_session, sample_pattern
):
    """3. miss quando a estrutura de filtros não bater"""
    mock_load_patterns.return_value = [sample_pattern]
    mock_load_digest.return_value = MagicMock()
    mock_resolve_aliases.return_value = ("liste projetos", [])
    mock_find_tables.return_value = ["Projeto"]  # Mesma Tabela
    
    # Filtro falta ou é diferente
    mock_slots = MagicMock()
    # Usuário pediu sem WHERE
    mock_slots.filters = []
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    result = await match_and_execute(mock_agent, "liste projetos", mock_session)
    assert result is None
    
    # Usuário pediu com campo diferente
    mock_slots.filters = [MagicMock(field="nome", op="=", value="X")]
    result = await match_and_execute(mock_agent, "liste projetos nome X", mock_session)
    assert result is None

@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@patch("app.services.semantic.pattern_matcher.db_execute.execute")
@pytest.mark.asyncio
async def test_execution_failure_fallback(
    mock_execute, mock_parse_slots, mock_find_tables, mock_resolve_aliases, 
    mock_load_digest, mock_load_patterns, mock_agent, mock_session, sample_pattern
):
    """Simula falha (SQL runtime error) na execução direta do match, garantindo fallback."""
    mock_load_patterns.return_value = [sample_pattern]
    mock_load_digest.return_value = MagicMock()
    mock_resolve_aliases.return_value = ("liste projetos", [])
    mock_find_tables.return_value = ["Projeto"]
    mock_slots = MagicMock()
    mock_slots.filters = [MagicMock(field="status", op="=", value="xyz")]
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    # db_execute retorna erro no SQL
    mock_result = MagicMock()
    mock_result.success = False
    mock_result.error = "Unknown column"
    mock_execute.return_value = mock_result

    with patch("app.services.semantic.pattern_matcher.update_pattern_usage") as mock_update:
        result = await match_and_execute(mock_agent, "liste projetos", mock_session)
        assert result is None
        mock_update.assert_called_with("test_agent", "ptn_123", success=False)
