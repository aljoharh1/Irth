"""Irth - command-line entry point.

Runs the multi-agent system headlessly (no Jupyter needed) and prints, for each
scenario, the ACL messages exchanged on the Message Bus, the decisions of the
Security Coordination Agent and the final coverage state.
The interactive dashboard runs in Jupyter / Google Colab (open Irth.ipynb).

Examples:
    python main.py                       # all scenarios S1-S9, short log
    python main.py --scenario S8 -v      # one scenario with message contents
    python main.py --scenario S9 --save  # also save map frames to outputs/
    python main.py --live 80             # free-roam museum for 80 ticks
"""

import argparse
import json
import os
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")                     # headless rendering

from irth import LiveMuseum, MuseumLiveDashboard, museum_figure, plt  # noqa: E402

SCENARIOS = {
    "S1": "Normal visit - approach and lingering, no alarm",
    "S2": "Artifact tampering",
    "S3": "Camera + Visitor Monitoring Agent failure, backup under maintenance",
    "S4": "Unauthorized entry into a restricted zone",
    "S5": "Artifact moved without a permit",
    "S6": "Authorized staff relocates an artifact",
    "S7": "Artifact moved while the camera is down",
    "S8": "Camera failure - backup camera takes over",
    "S9": "Camera failure - no backup can reach the hall",
}
STEPS = 6
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


def save_frame(sim, label):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig = museum_figure(sim)
    path = os.path.join(OUTPUT_DIR, f"Irth_{label}_T{sim.env.tick:02d}.png")
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return path


def print_message(msg, verbose):
    print(f"  T{msg.tick:<2} {msg.msg_id} {msg.sender:<28} -> {msg.receiver:<28} "
          f"{msg.performative:<7} {msg.ontology:<17} {msg.content.get('event')}")
    if verbose:
        extra = {k: v for k, v in msg.content.items() if k != "event"}
        print(f"        {json.dumps(extra, ensure_ascii=False, default=str)}")


def summary(sim):
    report = sim.coverage_agent.report(sim.env)
    artifacts = {a: sim.env.read_artifact_sensor(a)["status"] for a in sim.env.artifacts}
    print("  Decisions:")
    for d in sim.decisions:
        if d.level != "LOG":
            extra = f" | {d.response}" if d.response else ""
            print(f"    T{d.tick} {d.rule} {d.level}: {d.summary}{extra}")
    if not [d for d in sim.decisions if d.level != "LOG"]:
        print("    only LOG decisions (no alarm)")
    print(f"  Artifacts: {artifacts} | Coverage: {report['coverage_ratio']:.0%}"
          f" | Blind halls: {report['blind_halls'] or 'none'}")


def run_scenario(mode, verbose=False, save=False):
    """Run a scripted scenario exactly as the dashboard plays it."""
    sim = LiveMuseum(seed=42, spawn_every=0, max_visitors=1, dwell_threshold=3)
    sim.tours.clear()
    context = SimpleNamespace(mode=mode, sim=sim, visitor_agent_failed=False)
    if mode == "S4":
        sim.env.move_visitor("V1", (8.5, 8.0))          # inside Storage A
    print(f"\n=== {mode} - {SCENARIOS[mode]} ===")
    shown = 0
    for _ in range(STEPS):
        MuseumLiveDashboard.apply_scenario_event(context)
        sim.step()
        for msg in sim.bus.log[shown:]:
            print_message(msg, verbose)
        shown = len(sim.bus.log)
        if save:
            save_frame(sim, mode)
    summary(sim)
    return sim


def run_live(ticks, save=False):
    """Free-roam museum with randomly generated visitors."""
    sim = LiveMuseum(seed=42)
    print(f"\n=== Free roam for {ticks} ticks ===")
    for _ in range(ticks):
        sim.step()
    for msg in sim.bus.log[-15:]:
        print_message(msg, verbose=False)
    print(f"  Entered: {sim.total_entered} | Exited: {sim.total_exited} | "
          f"Messages on the bus: {len(sim.bus.log)}")
    summary(sim)
    if save:
        print("  Frame saved:", save_frame(sim, "LIVE"))
    return sim


def main():
    parser = argparse.ArgumentParser(description="Irth multi-agent museum simulation")
    parser.add_argument("--scenario", choices=list(SCENARIOS),
                        help="run one scripted scenario (default: all)")
    parser.add_argument("--live", type=int, metavar="TICKS",
                        help="run the free-roam museum for TICKS ticks")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show message contents")
    parser.add_argument("--save", action="store_true",
                        help="save map frames to outputs/")
    args = parser.parse_args()

    if args.live:
        run_live(args.live, args.save)
    else:
        for mode in [args.scenario] if args.scenario else SCENARIOS:
            run_scenario(mode, args.verbose, args.save)


if __name__ == "__main__":
    main()
