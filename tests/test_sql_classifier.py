"""
Tests: SQL Classifier
"""
import pytest
from app.core.sql_classifier import classify_sql


def test_select_is_low_risk():
    result = classify_sql("SELECT * FROM users")
    assert result.sql_type == "SELECT"
    assert result.risk_level == "low"
    assert result.has_where is True  # não se aplica, default True


def test_delete_without_where_is_high_risk():
    result = classify_sql("DELETE FROM users")
    assert result.sql_type == "DELETE"
    assert result.risk_level == "high"
    assert result.has_where is False


def test_delete_with_where_is_high_risk():
    result = classify_sql("DELETE FROM users WHERE id = 1")
    assert result.sql_type == "DELETE"
    assert result.risk_level == "high"  # DELETE é sempre high
    assert result.has_where is True


def test_update_without_where_is_high():
    result = classify_sql("UPDATE users SET name = 'test'")
    assert result.sql_type == "UPDATE"
    assert result.risk_level == "high"
    assert result.has_where is False


def test_update_with_where_is_medium():
    result = classify_sql("UPDATE users SET name = 'test' WHERE id = 1")
    assert result.sql_type == "UPDATE"
    assert result.risk_level == "medium"
    assert result.has_where is True


def test_drop_is_high_risk():
    result = classify_sql("DROP TABLE users")
    assert result.sql_type == "DROP"
    assert result.risk_level == "high"
    assert result.is_destructive is True


def test_truncate_is_high_risk():
    result = classify_sql("TRUNCATE TABLE orders")
    assert result.sql_type == "TRUNCATE"
    assert result.risk_level == "high"


def test_insert_is_medium():
    result = classify_sql("INSERT INTO users (name) VALUES ('test')")
    assert result.sql_type == "INSERT"
    assert result.risk_level == "medium"


def test_show_is_low():
    result = classify_sql("SHOW TABLES")
    assert result.sql_type == "SHOW"
    assert result.risk_level == "low"


def test_describe_is_low():
    result = classify_sql("DESCRIBE users")
    assert result.sql_type == "DESCRIBE"
    assert result.risk_level == "low"


def test_create_is_low():
    result = classify_sql("CREATE TABLE test (id INT PRIMARY KEY)")
    assert result.sql_type == "CREATE"
    assert result.risk_level == "low"


def test_alter_with_drop_column_is_high():
    result = classify_sql("ALTER TABLE users DROP COLUMN email")
    assert result.sql_type == "ALTER"
    assert result.is_destructive is True
    assert result.risk_level == "high"


def test_alter_add_column_is_medium():
    result = classify_sql("ALTER TABLE users ADD COLUMN age INT")
    assert result.sql_type == "ALTER"
    assert result.is_destructive is False
    assert result.risk_level == "medium"


def test_affected_objects_extracted():
    result = classify_sql("DELETE FROM pedidos WHERE id = 5")
    assert "pedidos" in result.affected_objects


def test_multi_statement_elevates_risk():
    sql = "SELECT 1; SELECT 2;"
    result = classify_sql(sql)
    assert result.is_multi_statement is True
    # multi-statement SELECT ainda é pelo menos medium
    assert result.risk_level in ("medium", "high")


def test_empty_sql():
    result = classify_sql("")
    assert result.sql_type == "EMPTY"
    assert result.risk_level == "low"
