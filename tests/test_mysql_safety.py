import pytest

from app.services.mysql import is_safe_query


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM users",
        "  select id, name from table_a  ",
        "SELECT * FROM logs WHERE action = 'update'",
        "SELECT * FROM table; ",
    ],
)
def test_is_safe_query_valid(query: str):
    assert is_safe_query(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "",
        None,
        "UPDATE users SET name='x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN age INT",
        "INSERT INTO t VALUES (1)",
        "SELECT * FROM update_log; DELETE FROM users",
    ],
)
def test_is_safe_query_invalid(query):
    assert is_safe_query(query) is False

