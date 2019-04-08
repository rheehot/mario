import subprocess
import sys
import time
import string


import pytest

from . import config


@pytest.fixture(name="reactor")
def _reactor():
    from twisted.internet import reactor

    return reactor


@pytest.fixture(name="server")
def _server():
    # TODO Replace subprocess with reactor
    command = ["python", config.TEST_DIR / "server.py"]
    proc = subprocess.Popen(command)
    time.sleep(1)
    yield
    proc.terminate()


class Timer:
    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.end = time.monotonic()
        self.elapsed = self.end - self.start


def test_cli_async_chain_map_apply(runner, reactor, server):
    base_url = "http://localhost:8080/?delay={}\n"

    in_stream = "".join(base_url.format(i) for i in [1, 2, 3, 4, 5] * 9)

    args = [
        "-m",
        "pype",
        "--max-concurrent",
        "100",
        "map",
        "await asks.get(x) ! x.json()",
        "filter",
        'x["id"] % 6 == 0',
        "map",
        "x['id']",
        "apply",
        "max(x)",
    ]

    expected = "42\n"

    with Timer() as t:
        output = subprocess.check_output(
            [sys.executable, *args], input=in_stream.encode()
        ).decode()

    assert output == expected
    limit_seconds = 6.0
    assert t.elapsed < limit_seconds