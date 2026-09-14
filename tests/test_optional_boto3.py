"""boto3 is an optional dependency (extras `s3`, `redshift`, `glue`), not a core one.

These tests run the imports in a subprocess where boto3/botocore cannot be
imported, so they hold regardless of what the test environment has installed.
"""

import subprocess
import sys
import textwrap

_BLOCK_BOTO3 = textwrap.dedent(
    """
    import sys

    class _Block:
        def find_spec(self, name, path=None, target=None):
            if name == "boto3" or name.startswith("boto3.") or name == "botocore" or name.startswith("botocore."):
                raise ImportError("boto3 blocked for this test")
            return None

    sys.meta_path.insert(0, _Block())
    """
)


def _run_without_boto3(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _BLOCK_BOTO3 + textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cli_and_connections_import_without_boto3():
    result = _run_without_boto3(
        """
        import datacontract.cli
        import datacontract.engines.ibis.connections.connect
        import datacontract.engines.ibis.connections.duckdb_connection
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_aws_client_without_boto3_points_to_the_extras():
    result = _run_without_boto3(
        """
        from datacontract.engines.ibis.connections import aws_credentials
        try:
            aws_credentials.client("glue", "eu-central-1")
        except ImportError as e:
            print(e)
        """
    )
    assert result.returncode == 0, result.stderr
    assert "datacontract-cli[s3]" in result.stdout
    assert "[glue]" in result.stdout


def test_resolve_aws_credentials_without_boto3_is_anonymous_not_an_error():
    result = _run_without_boto3(
        """
        from datacontract.engines.ibis.connections import aws_credentials
        print(aws_credentials.resolve_aws_credentials())
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "None"
