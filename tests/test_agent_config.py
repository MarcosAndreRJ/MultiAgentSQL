"""
Tests: Agent Config Loading (agent_registry)
"""
import pytest
from pathlib import Path
import tempfile
import yaml

from app.core import agent_registry
from app.schemas.agent import AgentConfig


def _write_yaml(content: dict, dir: Path, filename: str) -> Path:
    file = dir / filename
    with open(file, "w") as f:
        yaml.dump(content, f)
    return file


def test_load_principal_agent(tmp_path):
    config = {
        "id": "principal",
        "name": "Agente Principal",
        "description": "Teste",
        "type": "principal",
        "model": "llama3.1:8b",
        "prompt_file": "principal.md",
        "skills": ["mysql-defaults"],
        "database": None,
        "permissions": {
            "can_read_db": False,
            "can_write_db": False,
            "can_ddl": False,
            "can_execute": False,
        },
        "guards": {
            "require_confirmation_for": [],
            "auto_approve": ["SELECT"],
        },
        "behavior": {
            "max_loop_steps": 3,
            "response_style": "technical",
            "language": "pt-BR",
            "max_result_rows": 500,
            "introspect_before_ddl": True,
        }
    }
    _write_yaml(config, tmp_path, "principal.yaml")
    agent_registry.load_agents(tmp_path)

    agent = agent_registry.get("principal")
    assert agent is not None
    assert agent.type == "principal"
    assert agent.database is None
    assert agent.permissions.can_execute is False


def test_load_mysql_specialist_agent(tmp_path):
    config = {
        "id": "mysql-test",
        "name": "Test MySQL Agent",
        "description": "Test",
        "type": "mysql-specialist",
        "model": "llama3.1:8b",
        "prompt_file": "mysql-specialist.md",
        "skills": [],
        "database": {
            "host": "localhost",
            "port": 3306,
            "name": "testdb",
            "user": "root",
            "password": "",
        },
        "permissions": {
            "can_read_db": True,
            "can_write_db": True,
            "can_ddl": True,
            "can_execute": True,
        },
        "guards": {
            "require_confirmation_for": ["DELETE", "DROP"],
            "auto_approve": ["SELECT"],
        },
        "behavior": {
            "max_loop_steps": 5,
            "response_style": "technical",
            "language": "pt-BR",
            "max_result_rows": 500,
            "introspect_before_ddl": True,
        }
    }
    _write_yaml(config, tmp_path, "mysql-test.yaml")
    agent_registry.load_agents(tmp_path)

    agent = agent_registry.get("mysql-test")
    assert agent is not None
    assert agent.database is not None
    assert agent.database.name == "testdb"
    assert agent.permissions.can_execute is True
    assert "DELETE" in agent.guards.require_confirmation_for


def test_invalid_yaml_skipped(tmp_path):
    # YAML sem 'id' deve ser ignorado
    with open(tmp_path / "invalid.yaml", "w") as f:
        f.write("name: sem id")
    agent_registry.load_agents(tmp_path)
    # Não deve lançar exceção


def test_add_remove_skill_runtime(tmp_path):
    config = {
        "id": "skill-test",
        "name": "Skill Test",
        "description": "Test",
        "type": "principal",
        "model": "llama3.1:8b",
        "prompt_file": "",
        "skills": [],
        "database": None,
        "permissions": {"can_read_db": False, "can_write_db": False, "can_ddl": False, "can_execute": False},
        "guards": {"require_confirmation_for": [], "auto_approve": []},
        "behavior": {"max_loop_steps": 3, "response_style": "technical", "language": "pt-BR", "max_result_rows": 500, "introspect_before_ddl": True}
    }
    _write_yaml(config, tmp_path, "skill-test.yaml")
    agent_registry.load_agents(tmp_path)

    agent_registry.add_skill_to_agent("skill-test", "new-skill")
    agent = agent_registry.get("skill-test")
    assert "new-skill" in agent.skills

    agent_registry.remove_skill_from_agent("skill-test", "new-skill")
    assert "new-skill" not in agent.skills
