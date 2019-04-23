# pylint: disable=protected-access

from __future__ import generator_stop

import textwrap
import collections
import os
import string
import urllib
import subprocess
import time
import sys

import click.testing
import pytest
import hypothesis
import hypothesis.strategies as st


import mario
import mario.app
import mario.cli
import mario._version
from mario import utils
from mario import interpret


from tests import config
from tests import helpers


hypothesis.settings.register_profile("ci", max_examples=1000)
hypothesis.settings.register_profile("dev", max_examples=10)
hypothesis.settings.register_profile(
    "debug", max_examples=10, verbosity=hypothesis.Verbosity.verbose
)
hypothesis.settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


def assert_exception_equal(e1, e2):
    assert type(e1) == type(e2)
    assert e1.args == e2.args


@pytest.mark.parametrize("option", ["--invented-option", "-J"])
def test_raises_on_nonexistent_option(option, runner):
    args = [option, "print"]
    in_stream = "a.b.c\n"

    result = runner.invoke(mario.cli.cli, args, input=in_stream)

    assert_exception_equal(result.exception, SystemExit(2))


def test_eval_main(capsys):
    mario.app.main([[{"name": "eval", "pipeline": "1+1"}]])
    assert capsys.readouterr().out == "2\n"


def test_eval_cli():
    assert helpers.run(["eval", "1+1"]).decode() == "2\n"


def test_stack():
    args = [sys.executable, "-m", "mario", "stack", "len(x)"]
    stdin = "1\n2\n".encode()
    output = subprocess.check_output(args, input=stdin).decode()
    assert output == "4\n"


def test_exec_before():
    args = [
        sys.executable,
        "-m",
        "mario",
        "--exec-before",
        "from collections import Counter as c",
        "stack",
        "c(x)",
    ]
    stdin = "1\n2\n".encode()
    output = subprocess.check_output(args, input=stdin).decode()
    assert output.startswith("Counter")


def test_cli_version(runner):
    args = ["--version"]

    result = runner.invoke(mario.cli.cli, args)

    assert result.output == f"mario, version {mario._version.__version__}\n"
    assert result.output.rstrip()[-1].isdigit()
    assert not result.exception
    assert result.exit_code == 0


def test_config_file(tmp_path):
    config_body = """
    exec_before = "from collections import Counter as C"
    """

    config_file_path = tmp_path / "config.toml"

    config_file_path.write_text(config_body)

    args = ["stack", "C(x)"]
    stdin = "1\n2\n".encode()
    env = dict(os.environ)
    env.update({f"{utils.NAME}_CONFIG_DIR".upper().encode(): str(tmp_path).encode()})
    output = helpers.run(args, input=stdin, env=env).decode()
    assert output.startswith("Counter")


def test_exec_before():
    exec_before = textwrap.dedent(
        """\
    import csv
    def func(line):
        return next(csv.reader([line]))
    """
    )

    assert (
        helpers.run(
            ["--exec-before", exec_before, "map", "func"], input=b"a,b\n"
        ).decode()
        == "['a', 'b']\n"
    )