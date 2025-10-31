import importlib
import os
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("runtime", [None, "mock", "real"])
def test_get_docker_client_runtime_selection(runtime, monkeypatch):
    if runtime is None:
        monkeypatch.delenv("DOCKER_RUNTIME", raising=False)
    else:
        monkeypatch.setenv("DOCKER_RUNTIME", runtime)

    module = importlib.import_module("bd_stockevaluator.container.runtime")
    importlib.reload(module)

    if runtime == "real" and os.environ.get("DOCKER_AVAILABLE") != "1":
        pytest.skip("Real Docker tests require DOCKER_AVAILABLE=1")

    fake_client = object()
    monkeypatch.setattr(module, "_create_real_docker_client", lambda: fake_client)

    client = module.get_docker_client()

    if runtime == "real":
        assert client is fake_client
    else:
        MockDockerClient = module.MockDockerClient
        assert isinstance(client, MockDockerClient)


def test_get_docker_client_invalid_runtime(monkeypatch):
    monkeypatch.setenv("DOCKER_RUNTIME", "invalid")
    module = importlib.import_module("bd_stockevaluator.container.runtime")
    importlib.reload(module)

    with pytest.raises(ValueError):
        module.get_docker_client()


def test_app_module_main_invokes_uvicorn(monkeypatch):
    module = importlib.import_module("app.__main__")
    importlib.reload(module)

    calls = {}

    def fake_run(target, host, port, reload, factory, workers):
        calls["target"] = target
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload
        calls["factory"] = factory
        calls["workers"] = workers

    monkeypatch.setattr(module, "uvicorn", SimpleNamespace(run=fake_run))
    module.main()

    assert calls["target"] == "bd_stockevaluator.api.main:app"
    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 8000
    assert calls["factory"] is False
    assert calls["reload"] is False
    assert calls["workers"] == 1
