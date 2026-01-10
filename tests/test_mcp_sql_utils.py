"""Unit tests for MCP SQL utilities."""

import pytest

from datacontract.mcp.sql_utils import validate_read_only


class TestValidateReadOnly:
    """Tests for validate_read_only function."""

    def test_simple_select(self):
        """Simple SELECT should pass."""
        validate_read_only("SELECT * FROM users")

    def test_select_with_where(self):
        """SELECT with WHERE clause should pass."""
        validate_read_only("SELECT id, name FROM users WHERE active = true")

    def test_select_with_join(self):
        """SELECT with JOIN should pass."""
        validate_read_only("""
            SELECT u.name, o.total
            FROM users u
            JOIN orders o ON u.id = o.user_id
        """)

    def test_select_with_cte(self):
        """SELECT with CTE should pass."""
        validate_read_only("""
            WITH active_users AS (
                SELECT * FROM users WHERE active = true
            )
            SELECT * FROM active_users
        """)

    def test_select_with_subquery(self):
        """SELECT with subquery should pass."""
        validate_read_only("""
            SELECT * FROM users
            WHERE id IN (SELECT user_id FROM orders WHERE total > 100)
        """)

    def test_select_with_aggregation(self):
        """SELECT with aggregation should pass."""
        validate_read_only("""
            SELECT user_id, COUNT(*), SUM(total)
            FROM orders
            GROUP BY user_id
            HAVING COUNT(*) > 5
        """)

    def test_insert_rejected(self):
        """INSERT should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("INSERT INTO users (name) VALUES ('test')")

    def test_update_rejected(self):
        """UPDATE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("UPDATE users SET name = 'test' WHERE id = 1")

    def test_delete_rejected(self):
        """DELETE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("DELETE FROM users WHERE id = 1")

    def test_drop_table_rejected(self):
        """DROP TABLE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("DROP TABLE users")

    def test_create_table_rejected(self):
        """CREATE TABLE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("CREATE TABLE users (id INT, name VARCHAR(255))")

    def test_alter_table_rejected(self):
        """ALTER TABLE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("ALTER TABLE users ADD COLUMN email VARCHAR(255)")

    def test_truncate_rejected(self):
        """TRUNCATE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("TRUNCATE TABLE users")

    def test_merge_rejected(self):
        """MERGE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("""
                MERGE INTO target t
                USING source s ON t.id = s.id
                WHEN MATCHED THEN UPDATE SET t.name = s.name
            """)

    def test_grant_rejected(self):
        """GRANT should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("GRANT SELECT ON users TO public")

    def test_revoke_rejected(self):
        """REVOKE should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("REVOKE SELECT ON users FROM public")

    def test_multiple_selects_allowed(self):
        """Multiple SELECT statements should pass."""
        validate_read_only("SELECT 1; SELECT 2")

    def test_mixed_select_and_insert_rejected(self):
        """Mix of SELECT and INSERT should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("SELECT * FROM users; INSERT INTO users (name) VALUES ('test')")

    def test_empty_sql_rejected(self):
        """Empty SQL should be rejected."""
        with pytest.raises(ValueError):
            validate_read_only("")

    def test_whitespace_only_rejected(self):
        """Whitespace-only SQL should be rejected."""
        with pytest.raises(ValueError):
            validate_read_only("   \n\t  ")

    def test_invalid_sql_rejected(self):
        """Invalid SQL syntax should be rejected."""
        # sqlglot is lenient with parsing, but result won't be a SELECT
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("SELEKT * FORM users")

    def test_cte_with_insert_rejected(self):
        """CTE followed by INSERT should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_read_only("""
                WITH active AS (SELECT * FROM users WHERE active = true)
                INSERT INTO archive SELECT * FROM active
            """)
