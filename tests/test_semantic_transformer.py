import pytest
from unittest.mock import MagicMock, patch

from app.schemas.semantic import SemanticPattern, PatternFilter
from app.services.semantic.pattern_matcher import match_and_execute
from app.schemas.agent import AgentConfig, AgentBehavior
from app.schemas.chat import Session
from app.services.query_builder import BuildResult

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
def select_pattern():
    return SemanticPattern(
        id="ptn_list",
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

@pytest.fixture
def count_pattern():
    return SemanticPattern(
        id="ptn_count",
        agent_id="test_agent",
        intent_family="COUNT",
        mode="count",
        tables=["Projeto"],
        filters=[
            PatternFilter(field="status", op="=", slot_name="p0", slot_value="suspenso")
        ],
        sql_template="SELECT COUNT(*) AS total FROM `Projeto` WHERE `status` = %(p0)s",
        examples=[]
    )

@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@patch("app.services.semantic.pattern_matcher.db_execute.execute")
@patch("app.services.semantic.pattern_transformer.build_sql")
@pytest.mark.asyncio
async def test_transform_list_to_count(
    mock_build_sql, mock_execute, mock_parse_slots, mock_find_tables, 
    mock_resolve_aliases, mock_load_digest, mock_load_patterns, 
    mock_agent, mock_session, select_pattern
):
    """1. list -> count"""
    mock_load_patterns.return_value = [select_pattern] # Memória só tem SELECT
    mock_load_digest.return_value = MagicMock()
    # Usuário pede COUNT
    mock_resolve_aliases.return_value = ("quantos projetos em execução", [])
    mock_find_tables.return_value = ["Projeto"]
    
    mock_slots = MagicMock()
    mock_slots.filters = [MagicMock(field="status", op="=", value="execução")]
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    # Mock transformer return
    mock_build_result = BuildResult(
        sql="SELECT COUNT(*) AS total FROM `Projeto` WHERE `status` = %(p0)s",
        params={"p0": "execução"},
        tables_used=["Projeto"]
    )
    mock_build_sql.return_value = mock_build_result

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.rows = [{"total": 5}]
    mock_execute.return_value = mock_result

    with patch("app.services.semantic.pattern_matcher.update_pattern_usage") as mock_update:
        result = await match_and_execute(mock_agent, "quantos projetos em execução", mock_session)
        assert result is not None
        assert result.intent == "SEMANTIC_COUNT" 
        
        args, kwargs = mock_execute.call_args
        req = args[0]
        # SQL final deve ser o transformado
        assert "COUNT(*)" in req.sql


@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@patch("app.services.semantic.pattern_matcher.db_execute.execute")
@patch("app.services.semantic.pattern_transformer.build_sql")
@pytest.mark.asyncio
async def test_transform_count_to_list(
    mock_build_sql, mock_execute, mock_parse_slots, mock_find_tables, 
    mock_resolve_aliases, mock_load_digest, mock_load_patterns, 
    mock_agent, mock_session, count_pattern
):
    """2. count -> list"""
    mock_load_patterns.return_value = [count_pattern] # Memória só tem COUNT
    mock_load_digest.return_value = MagicMock()
    # Usuário pede LIST
    mock_resolve_aliases.return_value = ("liste projetos suspensos", [])
    mock_find_tables.return_value = ["Projeto"]
    
    mock_slots = MagicMock()
    mock_slots.filters = [MagicMock(field="status", op="=", value="suspenso")]
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    # Mock transformer return
    mock_build_result = BuildResult(
        sql="SELECT * FROM `Projeto` WHERE `status` = %(p0)s LIMIT 50",
        params={"p0": "suspenso"},
        tables_used=["Projeto"]
    )
    mock_build_sql.return_value = mock_build_result

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.rows = [{"id": 1}]
    mock_execute.return_value = mock_result

    result = await match_and_execute(mock_agent, "liste projetos suspensos", mock_session)
    assert result is not None
    assert result.intent == "SEMANTIC_SELECT" 
    
    args, kwargs = mock_execute.call_args
    req = args[0]
    assert "SELECT *" in req.sql


@patch("app.services.semantic.pattern_matcher.load_patterns")
@patch("app.services.semantic.pattern_matcher.load_digest")
@patch("app.services.semantic.pattern_matcher.resolve_message_aliases")
@patch("app.services.semantic.pattern_matcher._find_tables_in_message")
@patch("app.services.semantic.pattern_matcher.parse_slots")
@pytest.mark.asyncio
async def test_transform_filter_mismatch_fallback(
    mock_parse_slots, mock_find_tables, mock_resolve_aliases, 
    mock_load_digest, mock_load_patterns, mock_agent, mock_session, select_pattern
):
    """4. transformação falha quando filtros não batem"""
    # Mesmo baseando-se em transformação as cláusulas devem bater perfeitamente
    mock_load_patterns.return_value = [select_pattern]
    mock_load_digest.return_value = MagicMock()
    mock_resolve_aliases.return_value = ("quantos projetos com nome X", [])
    mock_find_tables.return_value = ["Projeto"]
    
    mock_slots = MagicMock()
    mock_slots.filters = [MagicMock(field="nome", op="=", value="X")] # slot diff "status"
    mock_slots.limit = None
    mock_parse_slots.return_value = mock_slots
    
    result = await match_and_execute(mock_agent, "quantos projetos", mock_session)
    assert result is None
