"""The session headers reach katana.

A scan can name an identity: the task carries the identity's cookies and
headers, and the worker has to hand them to katana, because a target
that needs a session answers an anonymous request with a login page.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import katanam.katanam as katanam_module  # noqa: E402
from katanam.katanam import katanam  # noqa: E402


class _Task:
    """A task that carries nothing but a payload."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload


class _Worker(katanam):
    """A worker without a configuration file and without a database."""

    def __init__(self) -> None:
        pass


class _Completed:
    """What a finished katana run reports."""

    stdout = ""
    stderr = ""
    returncode = 0


class _Subprocess:
    """A subprocess module that records the commands instead of running them."""

    PIPE = subprocess.PIPE

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, argv: list[str], **kwargs: Any) -> _Completed:
        self.commands.append(argv)
        return _Completed()


def _worker(monkeypatch: Any) -> tuple[_Worker, _Subprocess]:
    worker = _Worker()
    subprocess = _Subprocess()
    monkeypatch.setattr(katanam_module, "subprocess", subprocess)
    return worker, subprocess


def test_the_session_headers_reach_katana(monkeypatch: Any) -> None:
    worker, subprocess = _worker(monkeypatch)
    task = _Task(payload={"auth": {"cookies": {"JSESSIONID": "abc"}, "headers": {"X-Test": "1"}}})

    worker.katanacommand("http://example.test", worker.auth_headers(task))

    assert "-H" in subprocess.commands[0]
    assert "X-Test: 1" in subprocess.commands[0]
    assert "Cookie: JSESSIONID=abc" in subprocess.commands[0]


def test_katana_gets_no_header_without_an_identity(monkeypatch: Any) -> None:
    worker, subprocess = _worker(monkeypatch)
    task = _Task(payload={})

    worker.katanacommand("http://example.test", worker.auth_headers(task))

    assert "-H" not in subprocess.commands[0]


def test_the_paths_task_carries_the_session() -> None:
    worker = _Worker()
    task = _Task(payload={"auth": {"cookies": {"JSESSIONID": "abc"}}})

    payload = worker.paths_payload(task, "example.test", "example.test")

    assert payload["auth"] == {"cookies": {"JSESSIONID": "abc"}}


def test_the_paths_task_carries_no_session_without_an_identity() -> None:
    worker = _Worker()
    task = _Task(payload={})

    payload = worker.paths_payload(task, "example.test", "example.test")

    assert payload["auth"] == {}
