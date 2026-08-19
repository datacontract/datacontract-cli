from types import SimpleNamespace

from datacontract.command_api import _get_uvicorn_arguments


def _ctx(*extra_args):
    # _get_uvicorn_arguments only reads context.args
    return SimpleNamespace(args=list(extra_args))


def test_reload_is_off_by_default():
    args = _get_uvicorn_arguments(port=4242, host="127.0.0.1", reload=False, context=_ctx())
    assert args["reload"] is False


def test_reload_can_be_enabled():
    args = _get_uvicorn_arguments(port=4242, host="127.0.0.1", reload=True, context=_ctx())
    assert args["reload"] is True


def test_base_uvicorn_arguments():
    args = _get_uvicorn_arguments(port=1234, host="0.0.0.0", reload=False, context=_ctx())
    assert args["app"] == "datacontract.api:app"
    assert args["port"] == 1234
    assert args["host"] == "0.0.0.0"


def test_extra_uvicorn_arguments_are_merged():
    args = _get_uvicorn_arguments(
        port=4242, host="127.0.0.1", reload=False, context=_ctx("--root_path", "/datacontract")
    )
    assert args["root_path"] == "/datacontract"
