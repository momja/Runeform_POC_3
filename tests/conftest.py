"""Shared fixtures for e2e tests."""

import multiprocessing
import time

import pytest
import requests
import uvicorn


def _run_server(port: int):
    uvicorn.run("server:app", host="127.0.0.1", port=port, log_level="warning")


@pytest.fixture(scope="session")
def server_url():
    """Start the Runeform server on a free port for the test session."""
    port = 18002
    proc = multiprocessing.Process(target=_run_server, args=(port,), daemon=True)
    proc.start()

    # Wait for server to be ready
    url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            requests.get(url, timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail("Server did not start in time")

    yield url

    proc.kill()
    proc.join(timeout=5)
