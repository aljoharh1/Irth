"""Automated tests for Irth (run from the repository root with: pytest -q).

1. The team's own test cells from Irth.ipynb are executed unchanged, so the
   notebook results and the repository results can never disagree.
2. Extra system-level checks: every scenario runs, runs are repeatable, the
   free-roam museum stays stable, and irth/system.py matches the notebook.
"""

import contextlib
import io
import json
import os
import sys
from types import SimpleNamespace

import matplotlib
import pytest

matplotlib.use("Agg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import irth.system as system  # noqa: E402
from export_notebook import build, notebook_sections  # noqa: E402

NOTEBOOK_TESTS = {
    "Cell 7": "ALL SCENARIOS PASSED",                       # Student 2: S1-S3
    "Cell 9a": "Result: PASS",                              # Student 3: access control
    "Cell 9b": "Result: PASS",
    "Cell 9c": "Result: PASS",
    "Cell 19": "ALL SECURITY COORDINATION TESTS PASSED",    # Student 4
    "Cell 20": "ALL COVERAGE MANAGEMENT TESTS PASSED",      # Student 5
}


@pytest.fixture(scope="module")
def namespace(tmp_path_factory):
    """One shared namespace, like a notebook kernel (Cell 20 uses Cell 19)."""
    ns = dict(vars(system))
    ns["display"] = lambda *args, **kwargs: None
    ns["__workdir__"] = tmp_path_factory.mktemp("outputs")
    return ns


def notebook_cell(prefix):
    for heading, source in notebook_sections():
        if heading.startswith(prefix + " ") or heading.startswith(prefix + " —"):
            return source
    raise LookupError(prefix)


@pytest.mark.parametrize("cell, marker", NOTEBOOK_TESTS.items())
def test_notebook_test_cell(namespace, cell, marker):
    output = io.StringIO()
    cwd = os.getcwd()
    os.chdir(namespace["__workdir__"])          # CSV / PNG files go to a temp folder
    try:
        with contextlib.redirect_stdout(output):
            exec(notebook_cell(cell), namespace)
    finally:
        os.chdir(cwd)
    text = output.getvalue()
    assert marker in text
    assert "Result: FAIL" not in text


def play(mode, steps=6):
    sim = system.LiveMuseum(seed=42, spawn_every=0, max_visitors=1, dwell_threshold=3)
    sim.tours.clear()
    context = SimpleNamespace(mode=mode, sim=sim, visitor_agent_failed=False)
    for _ in range(steps):
        system.MuseumLiveDashboard.apply_scenario_event(context)
        sim.step()
    return sim


@pytest.mark.parametrize("mode", ["S1", "S2", "S3", "S5", "S6", "S7", "S8", "S9"])
def test_runs_are_repeatable(mode):
    def trace(sim):
        return [(m.tick, m.sender, m.performative, m.content.get("event"))
                for m in sim.bus.log]
    assert trace(play(mode)) == trace(play(mode))


def test_every_bus_message_is_valid_acl():
    for mode in ("S3", "S8", "S9"):
        assert all(system.validate_acl(m) for m in play(mode).bus.log)


def test_dashboard_plays_every_mode():
    dashboard = system.MuseumLiveDashboard(seed=42)
    dashboard.render = lambda: None             # no display outside Jupyter
    modes = [value for _, value in dashboard.scenario.options]
    assert modes == ["LIVE", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
    for mode in modes:
        dashboard.scenario.value = mode
        dashboard.load_mode()
        assert dashboard.sim.env.cameras["CAM_A"].active    # clean start every time
        for _ in range(8):
            dashboard.step_once()


def test_free_roam_long_run_is_stable():
    sim = system.LiveMuseum(seed=42)
    for _ in range(200):
        sim.step()
        assert all(sim.env.hall_for(v.position) for v in sim.env.visitors.values())
    assert sim.total_exited > 0
    assert sim.coverage_agent.coverage_ratio(sim.env) == 1.0
    assert not [d for d in sim.decisions if d.level == "ESCALATE"]


def test_package_matches_notebook():
    with open(os.path.join(ROOT, "irth", "system.py"), encoding="utf-8") as handle:
        assert handle.read() == build(), "run: python tools/export_notebook.py"
