"""Irth - multi-agent system for museum artifact protection.

AUTO-GENERATED from Irth.ipynb by tools/export_notebook.py - do not edit here;
edit the notebook and run the export again.
"""
# flake8: noqa


# ============================================================================
# Cell 1 — Museum environment and shared ACL entities (Student 1)
# ============================================================================

from dataclasses import dataclass, asdict
from math import dist
from collections import deque
import asyncio
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from IPython.display import display, clear_output
try:
    import ipywidgets as widgets
except ImportError:
    widgets = None  # Colab installs this; locally: pip install ipywidgets

@dataclass
class ACLMessage:
    sender: str
    receiver: str
    performative: str
    ontology: str
    content: dict
    tick: int

@dataclass
class Visitor:
    visitor_id: str
    position: tuple
    role: str = "visitor"

@dataclass
class Artifact:
    artifact_id: str
    name: str
    home_position: tuple
    position: tuple
    case_tampered: bool = False

@dataclass
class Camera:
    camera_id: str
    hall: str
    bounds: tuple
    active: bool = True
    def sees(self, point):
        xmin, xmax, ymin, ymax = self.bounds
        return self.active and xmin <= point[0] <= xmax and ymin <= point[1] <= ymax

class MuseumEnvironment:
    HALLS = {"Hall A": (0, 9, 0, 9), "Hall B": (10, 19, 0, 9)}
    PASSAGE = (9, 10, 3.35, 5.1)
    PROTECTION_RADIUS = 1.5
    RESTRICTED = {
        "Storage A": ((8, 9, 7, 9), {"staff"}),
        "Archive B": ((18, 19, 7, 9), {"staff"}),
    }
    def __init__(self, initial_visitors=True):
        self.tick = 0
        self.visitors = {
            "V1": Visitor("V1", (1, 4)),
            "V2": Visitor("V2", (12, 1)),
        } if initial_visitors else {}
        self.artifacts = {
            "A1": Artifact("A1", "Historic Vase", (4, 4), (4, 4)),
            "A2": Artifact("A2", "Rare Manuscript", (14, 4), (14, 4)),
        }
        self.cameras = {
            "CAM_A": Camera("CAM_A", "Hall A", (0, 9, 0, 9)),
            "CAM_B": Camera("CAM_B", "Hall B", (10, 19, 0, 9)),
            "CAM_BACKUP": Camera("CAM_BACKUP", "Hall A", (0, 9, 0, 9), False),
        }
    def hall_for(self, pos):
        for name, (xmin, xmax, ymin, ymax) in self.HALLS.items():
            if xmin <= pos[0] <= xmax and ymin <= pos[1] <= ymax:
                return name
        xmin, xmax, ymin, ymax = self.PASSAGE
        if xmin <= pos[0] <= xmax and ymin <= pos[1] <= ymax:
            return "Passage"
        return None
    def restricted_zone_for(self, pos):
        for name, (bounds, _allowed) in self.RESTRICTED.items():
            x1,x2,y1,y2 = bounds
            if x1 <= pos[0] <= x2 and y1 <= pos[1] <= y2:
                return name
        return None
    def advance(self):
        self.tick += 1
    def add_visitor(self, visitor_id, pos, role="visitor"):
        if visitor_id in self.visitors or self.hall_for(pos) is None:
            raise ValueError("Duplicate visitor or invalid position")
        self.visitors[visitor_id] = Visitor(visitor_id, tuple(pos), role)
    def move_visitor(self, visitor_id, pos):
        if self.hall_for(pos) is None:
            raise ValueError(f"Visitor moved outside walkable museum: {pos}")
        self.visitors[visitor_id].position = tuple(pos)
    def remove_visitor(self, visitor_id):
        del self.visitors[visitor_id]
    def move_artifact(self, artifact_id, pos):
        if self.hall_for(pos) is None:
            raise ValueError("Artifact position outside museum")
        self.artifacts[artifact_id].position = tuple(pos)
    def tamper_case(self, artifact_id, tampered=True):
        self.artifacts[artifact_id].case_tampered = bool(tampered)
    def set_camera(self, camera_id, active):
        self.cameras[camera_id].active = bool(active)
    def observed_visitors(self):
        result = []
        for v in self.visitors.values():
            for c in self.cameras.values():
                if c.sees(v.position):
                    result.append({"visitor_id": v.visitor_id,
                                   "position": v.position,
                                   "hall": self.hall_for(v.position),
                                   "camera_id": c.camera_id})
                    break
        return result
    def read_artifact_sensor(self, artifact_id):
        a = self.artifacts[artifact_id]
        moved = a.position != a.home_position
        status = "TAMPERED" if a.case_tampered else "MOVED" if moved else "IN_PLACE"
        return {"artifact_id": artifact_id, "status": status,
                "moved": moved, "case_tampered": a.case_tampered,
                "hall": self.hall_for(a.home_position)}


# ============================================================================
# Cell 2 — Visitor and Artifact Monitoring Agents (Students 1 & 2)
# ============================================================================

class VisitorMonitoringAgent:
    name = "visitor_monitoring_agent"
    agent_type = "Reactive"
    def __init__(self, dwell_threshold=3):
        self.dwell_threshold = dwell_threshold
        self.dwell = {}
        self.reported_lingering = set()
    def step(self, env):
        messages, currently_visible_near = [], set()
        for obs in env.observed_visitors():
            for a in env.artifacts.values():
                if obs["hall"] != env.hall_for(a.home_position):
                    continue
                if dist(obs["position"], a.home_position) > env.PROTECTION_RADIUS:
                    continue
                key = (obs["visitor_id"], a.artifact_id)
                currently_visible_near.add(key)
                self.dwell[key] = self.dwell.get(key, 0) + 1
                events = []
                if self.dwell[key] == 1:
                    events.append("ENTERED_PROTECTION_ZONE")
                if self.dwell[key] >= self.dwell_threshold and key not in self.reported_lingering:
                    events.append("LINGERING")
                    self.reported_lingering.add(key)
                for event in events:
                    messages.append(ACLMessage(
                        self.name, "security_coordination_agent", "INFORM",
                        "visitor_behavior", {"event": event,
                        "visitor_id": obs["visitor_id"], "artifact_id": a.artifact_id,
                        "camera_id": obs["camera_id"], "hall": obs["hall"],
                        "dwell_ticks": self.dwell[key], "confirmed_threat": False},
                        env.tick))
        for key in list(self.dwell):
            if key not in currently_visible_near:
                del self.dwell[key]
                self.reported_lingering.discard(key)
        return messages

class ArtifactMonitoringAgent:
    name = "artifact_monitoring_agent"
    agent_type = "Reactive"
    def __init__(self):
        self.previous = {}
    def step(self, env):
        messages = []
        for artifact_id in env.artifacts:
            current = env.read_artifact_sensor(artifact_id)
            previous = self.previous.get(artifact_id)
            if previous is not None and (current["moved"], current["case_tampered"]) != (previous["moved"], previous["case_tampered"]):
                messages.append(ACLMessage(
                    self.name, "security_coordination_agent", "INFORM", "artifact_status",
                    {"event": "ARTIFACT_STATUS_CHANGED", **current,
                     "previous_status": previous["status"]}, env.tick))
            self.previous[artifact_id] = current
        return messages
    def handle_request(self, env, request):
        if request.performative != "REQUEST" or request.ontology != "artifact_status":
            raise ValueError("Invalid request")
        return ACLMessage(self.name, request.sender, "INFORM", "artifact_status",
                          {"event": "ARTIFACT_STATUS_REPLY",
                           **env.read_artifact_sensor(request.content["artifact_id"])}, env.tick)


# ============================================================================
# Cell 3 — Visitor lifecycle and simulation engine (Student 1)
# ============================================================================

@dataclass
class Tour:
    waypoints: list
    waypoint_index: int = 0
    pause: int = 0

class LiveMuseum:
    """Simulation environment + Student 1/2 agents only. Not a security coordinator."""
    def __init__(self, seed=42, spawn_every=9, max_visitors=7, dwell_threshold=3):
        self.env = MuseumEnvironment(initial_visitors=False)
        self.visitor_agent = VisitorMonitoringAgent(dwell_threshold)
        self.artifact_agent = ArtifactMonitoringAgent()
        self.spawn_every = spawn_every
        self.max_visitors = max_visitors
        self.rng = random.Random(seed)
        self.next_id = 1
        self.total_entered = 0
        self.total_exited = 0
        self.tours = {}
        self.events = deque(maxlen=80)
        self.messages = deque(maxlen=100)
        self.artifact_agent.step(self.env)  # initial sensor baseline
        self.spawn_visitor()
        self.spawn_visitor()
    def make_tour(self):
        # Both routes cross the connecting passage at y=4.2.
        a_stop = ((4.1, 5.05), self.rng.randint(3, 6))
        b_stop = ((14.1, 5.05), self.rng.randint(3, 6))
        if self.rng.random() < .5:
            locations = [((3.0, 2.0),0), a_stop, ((8.3,4.2),0),
                         ((9.5,4.2),0), ((11.0,4.2),0), b_stop,
                         ((15.7,2.4),0), ((11.0,4.2),0), ((9.5,4.2),0),
                         ((8.3,4.2),0), ((3.0,2.0),0), ((1.0,1.2),0)]
        else:
            locations = [((3.0,2.0),0), ((8.3,4.2),0), ((9.5,4.2),0),
                         ((11.0,4.2),0), b_stop, ((11.0,4.2),0),
                         ((9.5,4.2),0), ((8.3,4.2),0), a_stop,
                         ((3.0,2.0),0), ((1.0,1.2),0)]
        return Tour(locations)
    def spawn_visitor(self):
        if len(self.env.visitors) >= self.max_visitors:
            return None
        vid = f"V{self.next_id}"
        self.next_id += 1
        self.env.add_visitor(vid, (1.0,1.2))
        self.tours[vid] = self.make_tour()
        self.total_entered += 1
        self.events.append((self.env.tick, f"{vid} entered the museum"))
        return vid
    def move_visitors(self):
        for vid, tour in list(self.tours.items()):
            if tour.pause > 0:
                tour.pause -= 1
                continue
            if tour.waypoint_index >= len(tour.waypoints):
                self.env.remove_visitor(vid)
                del self.tours[vid]
                self.total_exited += 1
                self.events.append((self.env.tick, f"{vid} exited the museum"))
                continue
            visitor = self.env.visitors[vid]
            target, pause = tour.waypoints[tour.waypoint_index]
            d = dist(visitor.position, target)
            speed = .85
            if d <= speed:
                self.env.move_visitor(vid, target)
                tour.waypoint_index += 1
                tour.pause = pause
            else:
                alpha = speed / d
                new_pos = tuple(visitor.position[i] + alpha*(target[i]-visitor.position[i]) for i in (0,1))
                self.env.move_visitor(vid, new_pos)
    def step(self):
        self.env.advance()
        if self.spawn_every and self.env.tick % self.spawn_every == 0:
            self.spawn_visitor()
        self.move_visitors()
        new = self.visitor_agent.step(self.env) + self.artifact_agent.step(self.env)
        self.messages.extend(new)
        return new


# ============================================================================
# Cell 4 — Live museum map renderer (Student 1)
# ============================================================================

# ---------------- LIVE RENDERER (model state, not agent's camera view) ----------------
def museum_figure(sim):
    env = sim.env
    navy, teal = "#16334E", "#0F988D"
    fig, ax = plt.subplots(figsize=(12.6, 6.3))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#F4F7FB")
    for name,(xmin,xmax,ymin,ymax) in env.HALLS.items():
        ax.add_patch(FancyBboxPatch((xmin,ymin),xmax-xmin,ymax-ymin,
                     boxstyle="round,pad=0.02,rounding_size=0.13",
                     facecolor="#FFFCF7",edgecolor="#536A82",linewidth=2,zorder=1))
        # Colored camera overlay is based on actual active cameras.
        if any(c.active and c.hall == name for c in env.cameras.values()):
            ax.add_patch(Rectangle((xmin+.08,ymin+.08),xmax-xmin-.16,ymax-ymin-.16,
                                   facecolor="#B5E5E5",alpha=.32,zorder=2))
        ax.text((xmin+xmax)/2,8.45,
                "HERITAGE GALLERY" if name=="Hall A" else "MANUSCRIPT GALLERY",
                color=navy,fontsize=10.3,weight="bold",ha="center",zorder=8)
    ax.add_patch(Rectangle((9,3.35),1,1.75,facecolor="#E1EBF2",edgecolor="#536A82",zorder=2))
    ax.text(9.5,4.18,"PASSAGE",ha="center",va="center",fontsize=6.3,rotation=90,color=navy,zorder=7)
    for name,(bounds,_) in env.RESTRICTED.items():
        x1,x2,y1,y2=bounds
        ax.add_patch(Rectangle((x1,y1),x2-x1,y2-y1,facecolor="#F8D7D7",
                               edgecolor="#C24C4C",hatch="///",zorder=4))
        ax.text((x1+x2)/2,8,"STAFF\nONLY",ha="center",va="center",fontsize=6.8,color="#9B2929",zorder=7)
    for a in env.artifacts.values():
        x,y=a.home_position
        ax.add_patch(Circle((x,y),env.PROTECTION_RADIUS,color="#F6C96F",alpha=.25,zorder=3))
        ax.add_patch(Circle((x,y),env.PROTECTION_RADIUS,fill=False,
                            edgecolor="#C89230",linestyle="--",linewidth=1.3,zorder=4))
        ax.add_patch(FancyBboxPatch((x-.38,y-.32),.76,.64,
                          boxstyle="round,pad=.025,rounding_size=.07",
                          facecolor="#F5EEE4",edgecolor="#AA8970",zorder=5))
        status = env.read_artifact_sensor(a.artifact_id)["status"]
        ax.scatter(*zip(a.position),s=140,marker="D" if a.artifact_id=="A1" else "s",
                   color="#C43B49" if status!="IN_PLACE" else "#8A5F47",zorder=8)
        ax.text(x,y-.84,f"{a.name}  [{status}]",fontsize=8,ha="center",weight="bold",color=navy,zorder=8)
    # Decorative exhibits are visual-only, not additional tracked artifacts.
    for x in (2,6.5,12,16.5):
        ax.add_patch(Rectangle((x-.38,6.6),.76,.55,facecolor="#E7D8C8",edgecolor="#AD9177",zorder=4))
        ax.text(x,6.3,"DISPLAY",fontsize=6.6,color="#8E7150",ha="center",zorder=7)
    for vid,v in env.visitors.items():
        ax.scatter(v.position[0],v.position[1],s=108,c="#286BC6",edgecolor="white",linewidth=1.2,zorder=10)
        ax.text(v.position[0]+.16,v.position[1]+.24,vid,fontsize=8.5,color=navy,weight="bold",zorder=10)
    cam_pos={"CAM_A":(.9,7.9),"CAM_B":(10.9,7.9),"CAM_BACKUP":(6.6,1.3)}
    for cid,c in env.cameras.items():
        x,y=cam_pos[cid]
        color=teal if c.active else "#C43B49"
        ax.scatter(x,y,marker="s",s=85,c=color,zorder=11)
        ax.text(x+.23,y,f"{cid} {'ON' if c.active else 'OFF'}",fontsize=7.2,color=color,weight="bold",va="center",zorder=11)
    ax.text(1.0,.45,"ENTRANCE / EXIT",fontsize=8,color=navy,weight="bold",zorder=9)
    ax.set_title(f"IRTH  |  LIVE MUSEUM SIMULATION   •   TICK {env.tick}",fontsize=15.5,
                 pad=13,color=navy,weight="bold")
    ax.set_xlim(-.7,19.8)
    ax.set_ylim(-.6,9.6)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    return fig


# ============================================================================
# Cell 5 — Interactive dashboard: base controls (Student 3)
# ============================================================================

import ipywidgets as widgets
from IPython.display import display, clear_output
import matplotlib.pyplot as plt

class MuseumLiveDashboard:
    SCENARIO_STEPS = 6

    def __init__(self, seed=42):
        self.seed = seed
        self.sim = LiveMuseum(seed=seed)
        self.mode = "LIVE"
        self.running = False
        self.task = None
        self._run_generation = 0
        self.visitor_agent_failed = False

        self.scenario = widgets.Dropdown(
            options=[
                ("Live", "LIVE"),
                ("S1 - Normal Visit", "S1"),
                ("S2 - Artifact Tampering", "S2"),
                ("S3 - Camera and Agent Failure", "S3")
            ],
            value="LIVE",
            description="Scenario"
        )

        self.load_button = widgets.Button(description="Load")
        self.play = widgets.Button(description="Start", button_style="success")
        self.pause = widgets.Button(description="Pause")
        self.single = widgets.Button(description="Next Step")
        self.reset = widgets.Button(description="Reset")
        self.tamper = widgets.Button(description="Tamper A1", button_style="danger")

        self.cam_a = widgets.Checkbox(value=True, description="Camera A")
        self.backup = widgets.Checkbox(value=False, description="Backup Camera")

        self.spawn = widgets.IntSlider(
            value=9, min=0, max=20, description="Spawn"
        )
        self.capacity = widgets.IntSlider(
            value=7, min=2, max=20, description="Visitors"
        )
        self.dwell = widgets.IntSlider(
            value=3, min=1, max=10, description="Dwell"
        )
        self.delay = widgets.FloatSlider(
            value=1, min=0.2, max=3, step=0.2, description="Speed"
        )

        self.output = widgets.Output()

        self.load_button.on_click(lambda _: self.load_mode())
        self.play.on_click(self.on_play)
        self.pause.on_click(self.on_pause)
        self.single.on_click(lambda _: self.next_step())
        self.reset.on_click(lambda _: self.load_mode())
        self.tamper.on_click(lambda _: self.tamper_artifact())

        self.cam_a.observe(self.update_cameras, names="value")
        self.backup.observe(self.update_cameras, names="value")

    @staticmethod
    def apply_scenario_event(context):
        env = context.sim.env
        tick = env.tick

        if context.mode in ("S1", "S2") and tick < 3:
            if "V1" in env.visitors:
                env.move_visitor("V1", (4.1, 5.05))

        if context.mode == "S2" and tick == 2:
            env.tamper_case("A1", True)

        if context.mode == "S3":
            if tick == 0:
                env.set_camera("CAM_A", False)
                context.visitor_agent_failed = True
                context.sim.visitor_agent.step = lambda env: []

            if tick == 2:
                env.tamper_case("A1", True)

    def stop(self):
        self.running = False
        self._run_generation += 1

        if self.task is not None and not self.task.done():
            self.task.cancel()

        self.task = None

    def load_mode(self):
        self.stop()
        self.mode = self.scenario.value

        self.sim = LiveMuseum(
            seed=self.seed,
            spawn_every=self.spawn.value if self.mode == "LIVE" else 0,
            max_visitors=self.capacity.value,
            dwell_threshold=self.dwell.value
        )

        self.visitor_agent_failed = False

        if self.mode != "LIVE":
            self.sim.tours.clear()

            for vid in list(self.sim.env.visitors):
                if vid != "V1":
                    self.sim.env.remove_visitor(vid)

        self.sim.env.set_camera("CAM_A", self.cam_a.value)
        self.sim.env.set_camera("CAM_BACKUP", self.backup.value)

        self.render()

    def update_cameras(self, change):
        self.sim.env.set_camera("CAM_A", self.cam_a.value)
        self.sim.env.set_camera("CAM_BACKUP", self.backup.value)
        self.render()

    def tamper_artifact(self):
        self.sim.env.tamper_case("A1", True)
        self.render()

    def step_once(self):
        if self.mode != "LIVE":
            if self.sim.env.tick >= self.SCENARIO_STEPS:
                return False

            self.apply_scenario_event(self)

        self.sim.step()
        return True

    def next_step(self):
        self.step_once()
        self.render()

    def on_play(self, button):
        self.next_step()

    def on_pause(self, button):
        self.stop()

    def render(self):
        with self.output:
            clear_output(wait=True)

            fig = museum_figure(self.sim)
            display(fig)
            plt.close(fig)

            env = self.sim.env

            print("Mode:", self.mode)
            print("Tick:", env.tick)
            print("Visitors:", len(env.visitors))

            print("\nCAMERA STATUS:")
            for name, camera in env.cameras.items():
                status = "ONLINE" if camera.active else "OFFLINE"
                print(name, status)

            print("\nARTIFACT STATUS:")
            for name in env.artifacts:
                status = env.read_artifact_sensor(name)["status"]
                print(name, status)

            print("\nAGENT STATUS:")
            status = "OFFLINE" if self.visitor_agent_failed else "ONLINE"
            print("Visitor Monitoring:", status)
            print("Artifact Monitoring: ONLINE")

            print("\nRECENT ACL MESSAGES:")
            for message in list(self.sim.messages)[-8:]:
                print(
                    message.sender,
                    "->",
                    message.receiver,
                    "|",
                    message.performative,
                    "|",
                    message.content
                )

    def show(self):
        display(widgets.VBox([
            widgets.HBox([
                self.scenario,
                self.load_button
            ]),
            widgets.HBox([
                self.play,
                self.pause,
                self.single,
                self.reset,
                self.tamper
            ]),
            widgets.HBox([
                self.cam_a,
                self.backup
            ]),
            self.spawn,
            self.capacity,
            self.dwell,
            self.delay,
            self.output
        ]))

        self.render()


# ============================================================================
# Cell 6 — Dashboard: automatic simulation clock (Student 3)
# ============================================================================

_OriginalMuseumLiveDashboard = MuseumLiveDashboard


class MuseumLiveDashboard(_OriginalMuseumLiveDashboard):

    def __init__(self, seed=42):

        self.clock = None
        self._clock_last = 0
        self._clock_syncing = False

        super().__init__(seed=seed)

        # Browser-based simulation clock
        self.clock = widgets.Play(
            value=0,
            min=0,
            max=100000,
            step=1,
            interval=int(self.delay.value * 1000),
            description="Auto clock"
        )

        self.clock.observe(
            self._on_clock_tick,
            names="value"
        )

        self.clock.observe(
            self._on_clock_playing,
            names="playing"
        )

        self.delay.observe(
            self._on_delay_change,
            names="value"
        )

        self.clock_status = widgets.HTML(
            value="<b>Status:</b> Paused"
        )

    # ------------------------------------
    # Stop automatic playback
    # ------------------------------------

    def stop(self):

        self.running = False
        self._run_generation += 1

        if self.clock is not None:
            self.clock.playing = False

        if self.task is not None and not self.task.done():
            self.task.cancel()

        self.task = None

    # ------------------------------------
    # Reset clock when loading a mode
    # ------------------------------------

    def load_mode(self):

        self.stop()

        if self.clock is not None:

            self._clock_syncing = True

            self.clock.playing = False
            self.clock.value = 0
            self._clock_last = 0

            self._clock_syncing = False

        super().load_mode()

        if hasattr(self, "clock_status"):
            self.clock_status.value = (
                "<b>Status:</b> Ready"
            )

    # ------------------------------------
    # Simulation speed
    # ------------------------------------

    def _on_delay_change(self, change):

        self.clock.interval = int(
            self.delay.value * 1000
        )

    def _on_clock_playing(self, change):

        self.running = bool(change["new"])

    # ------------------------------------
    # START BUTTON
    # ------------------------------------

    def on_play(self, _):

        if self.mode != self.scenario.value:
            self.load_mode()

        if (
            self.mode != "LIVE"
            and self.sim.env.tick >= self.SCENARIO_STEPS
        ):

            self.clock_status.value = (
                "<b>Status:</b> Finished - Reset to replay"
            )
            return

        self.clock.interval = int(
            self.delay.value * 1000
        )

        self.running = True
        self.clock.playing = True

        self.clock_status.value = (
            "<b>Status:</b> Running"
        )

    # ------------------------------------
    # PAUSE BUTTON
    # ------------------------------------

    def on_pause(self, _):

        self.stop()

        self.clock_status.value = (
            "<b>Status:</b> Paused"
        )

        self.render()

    # ------------------------------------
    # AUTOMATIC TICK HANDLER
    # ------------------------------------

    def _on_clock_tick(self, change):

        if self._clock_syncing or not self.running:
            return

        new_value = int(change["new"])

        if new_value <= self._clock_last:
            self._clock_last = new_value
            return

        # Process all elapsed simulation steps
        delta = new_value - self._clock_last

        self._clock_last = new_value

        try:

            for _ in range(delta):

                progressed = self.step_once()

                if not progressed:

                    self.stop()

                    self.clock_status.value = (
                        "<b>Status:</b> Scenario complete"
                    )

                    break

                # Stop at the end of a fixed scenario
                if (
                    self.mode != "LIVE"
                    and self.sim.env.tick
                    >= self.SCENARIO_STEPS
                ):

                    self.stop()

                    self.clock_status.value = (
                        "<b>Status:</b> Scenario complete"
                    )

                    break

            self.render()

        except Exception as error:

            self.stop()

            self.clock_status.value = (
                "<b style='color:red'>Playback Error:</b> "
                + str(error)
            )

            raise

    # ------------------------------------
    # DISPLAY DASHBOARD
    # ------------------------------------

    def show(self):

        try:
            from google.colab import output as colab_output
            colab_output.enable_custom_widget_manager()

        except ImportError:
            pass

        display(
            widgets.VBox([

                widgets.HBox([
                    self.scenario,
                    self.load_button
                ]),

                widgets.HBox([
                    self.play,
                    self.pause,
                    self.single,
                    self.reset,
                    self.tamper
                ]),

                widgets.HBox([
                    self.cam_a,
                    self.backup
                ]),

                self.spawn,
                self.capacity,
                self.dwell,
                self.delay,

                widgets.HBox([
                    self.clock,
                    self.clock_status
                ]),

                self.output
            ])
        )

        self.render()


# ============================================================================
# Cell 8 — Access Control Agent (Student 3)
# ============================================================================

class AccessControlAgent:
    name = "access_control_agent"
    agent_type = "Reactive"

    def __init__(self):
        self.reported_entries = set()

    def check_permission(self, env, visitor_id, zone):
        visitor = env.visitors.get(visitor_id)

        if visitor is None:
            return False

        if zone not in env.RESTRICTED:
            return False

        allowed_roles = env.RESTRICTED[zone][1]
        return visitor.role in allowed_roles

    def step(self, env):
        messages = []
        current_entries = set()

        for visitor in env.visitors.values():
            zone = env.restricted_zone_for(visitor.position)

            if zone is None:
                continue

            key = (visitor.visitor_id, zone)
            current_entries.add(key)

            if self.check_permission(env, visitor.visitor_id, zone):
                continue

            if key not in self.reported_entries:
                messages.append(
                    ACLMessage(
                        self.name,
                        "security_coordination_agent",
                        "INFORM",
                        "access_control",
                        {
                            "event": "UNAUTHORIZED_ENTRY",
                            "visitor_id": visitor.visitor_id,
                            "role": visitor.role,
                            "zone": zone,
                            "authorized": False
                        },
                        env.tick
                    )
                )

        self.reported_entries = current_entries
        return messages

    def handle_request(self, env, request):
        if request.performative != "REQUEST":
            raise ValueError("Invalid request")

        if request.ontology != "access_control":
            raise ValueError("Invalid ontology")

        visitor_id = request.content["visitor_id"]
        zone = request.content["zone"]

        authorized = self.check_permission(
            env,
            visitor_id,
            zone
        )

        return ACLMessage(
            self.name,
            request.sender,
            "INFORM",
            "access_control",
            {
                "event": "PERMISSION_REPLY",
                "visitor_id": visitor_id,
                "zone": zone,
                "authorized": authorized
            },
            env.tick
        )


_OriginalLiveMuseum = LiveMuseum


class LiveMuseum(_OriginalLiveMuseum):

    def __init__(
        self,
        seed=42,
        spawn_every=9,
        max_visitors=7,
        dwell_threshold=3
    ):
        super().__init__(
            seed=seed,
            spawn_every=spawn_every,
            max_visitors=max_visitors,
            dwell_threshold=dwell_threshold
        )

        self.access_agent = AccessControlAgent()

    def step(self):
        access_messages = self.access_agent.step(self.env)

        messages = super().step()

        self.messages.extend(access_messages)

        return access_messages + messages


# ============================================================================
# Cell 10 — Dashboard: agent status and message log panel (Student 3)
# ============================================================================

_PreviousMuseumLiveDashboard = MuseumLiveDashboard


class MuseumLiveDashboard(_PreviousMuseumLiveDashboard):

    def render(self):
        with self.output:
            clear_output(wait=True)

            fig = museum_figure(self.sim)
            display(fig)
            plt.close(fig)

            env = self.sim.env

            print(
                "Mode:", self.mode,
                "| Tick:", env.tick,
                "| Visitors:", len(env.visitors)
            )

            print(
                "Cameras:",
                ", ".join(
                    f"{name}: {'ON' if cam.active else 'OFF'}"
                    for name, cam in env.cameras.items()
                )
            )

            print(
                "Artifacts:",
                ", ".join(
                    f"{name}: {env.read_artifact_sensor(name)['status']}"
                    for name in env.artifacts
                )
            )

            print("\nAgent Status")
            print("------------")
            print(
                "Visitor Monitoring:",
                "OFFLINE" if self.visitor_agent_failed else "ONLINE"
            )
            print("Artifact Monitoring: ONLINE")
            print("Access Control: ONLINE")

            print("\nRecent ACL Messages")
            print("-------------------")

            for message in list(self.sim.messages)[-8:]:
                print(
                    message.sender,
                    "->",
                    message.receiver,
                    message.performative,
                    message.content
                )


# ============================================================================
# Cell 11 — Dashboard: scenario S4, unauthorized entry (Student 3)
# ============================================================================

_PreviousDashboardWithAccess = MuseumLiveDashboard


class MuseumLiveDashboard(_PreviousDashboardWithAccess):

    def __init__(self, seed=42):
        super().__init__(seed=seed)

        options = list(self.scenario.options)

        if not any(value == "S4" for _, value in options):
            options.append(
                ("S4 - Unauthorized Entry", "S4")
            )

        self.scenario.options = options

    def load_mode(self):
        if self.scenario.value != "S4":
            return super().load_mode()

        self.stop()

        self.mode = "S4"
        self.sim = LiveMuseum(seed=self.seed, spawn_every=0)
        self.visitor_agent_failed = False

        self.sim.env.move_visitor("V1", (8.5, 8.0))

        self.sim.step()

        self.render()


# ============================================================================
# Cell 12 — Dashboard: suspicion indicator (Student 3)
# ============================================================================

_PreviousDashboardWithSuspicion = MuseumLiveDashboard


class MuseumLiveDashboard(_PreviousDashboardWithSuspicion):

    def __init__(self, seed=42):
        super().__init__(seed=seed)

        self.suspicion = widgets.IntSlider(
            value=2,
            min=1,
            max=5,
            step=1,
            description="Suspicion"
        )

        self.suspicion_status = "NORMAL"

    def calculate_suspicion(self):
        score = 0

        for message in list(self.sim.messages):
            event = message.content.get("event")

            if event == "ENTERED_PROTECTION_ZONE":
                score += 1

            elif event == "LINGERING":
                score += 2

            elif event == "UNAUTHORIZED_ENTRY":
                score += 2

        if score >= self.suspicion.value:
            self.suspicion_status = "SUSPICIOUS"
        else:
            self.suspicion_status = "NORMAL"

        return score

    def render(self):
        self.calculate_suspicion()

        super().render()

        with self.output:
            print("\nSuspicion Monitoring")
            print("--------------------")
            print("Threshold:", self.suspicion.value)
            print("Status:", self.suspicion_status)

    def show(self):
        try:
            from google.colab import output as colab_output
            colab_output.enable_custom_widget_manager()
        except ImportError:
            pass

        display(
            widgets.VBox([

                widgets.HBox([
                    self.scenario,
                    self.load_button
                ]),

                widgets.HBox([
                    self.play,
                    self.pause,
                    self.single,
                    self.reset,
                    self.tamper
                ]),

                widgets.HBox([
                    self.cam_a,
                    self.backup
                ]),

                self.spawn,
                self.capacity,
                self.dwell,
                self.suspicion,
                self.delay,

                widgets.HBox([
                    self.clock,
                    self.clock_status
                ]),

                self.output
            ])
        )

        self.render()


# ============================================================================
# Cell 13 — Unified ACL-like message format and shared Message Bus (Student 4)
# ============================================================================

# Cell 13 — Unified ACL-like message format + shared Message Bus
# Every message between agents uses ONE format:
#   sender | receiver | performative (message type) | ontology | content | tick
#   + conversation_id / msg_id / in_reply_to so each reply can be traced back to its request.
import itertools
import json
from dataclasses import dataclass, field

PERFORMATIVES = {
    "INFORM":  "The sender tells the receiver a fact it believes is true",
    "REQUEST": "The sender asks the receiver for information or for an action",
    "ACCEPT":  "The receiver agrees to perform the requested action",
    "REFUSE":  "The receiver cannot or will not perform the request (reason in content)",
}

ONTOLOGIES = {
    "visitor_behavior":  "Visitor positions, approaching and lingering near artifacts",
    "artifact_status":   "Artifact sensor state: IN_PLACE / MOVED / TAMPERED",
    "access_control":    "Roles, zone permissions and artifact-handling permits",
    "coverage":          "Camera health and monitored / unmonitored halls",
    "security_response": "Coordinator decisions, alerts and guard dispatch",
}

# Keep the team's original ACLMessage fields and only ADD optional ones,
# so every agent written before this cell keeps working unchanged.
_BaseACLMessage = globals().get("_BaseACLMessage", ACLMessage)
_MSG_COUNTER = itertools.count(1)


@dataclass
class ACLMessage(_BaseACLMessage):
    conversation_id: str = None
    in_reply_to: str = None
    msg_id: str = field(default_factory=lambda: f"M{next(_MSG_COUNTER):05d}")

    def to_acl(self):
        """FIPA-ACL-like textual form of the message."""
        return (
            f"({self.performative}\n"
            f"   :sender          {self.sender}\n"
            f"   :receiver        {self.receiver}\n"
            f"   :ontology        {self.ontology}\n"
            f"   :conversation-id {self.conversation_id}\n"
            f"   :reply-with      {self.msg_id}\n"
            f"   :in-reply-to     {self.in_reply_to}\n"
            f"   :tick            {self.tick}\n"
            f"   :content         {json.dumps(self.content, ensure_ascii=False, default=str)})"
        )

    def short(self):
        return (f"[T{self.tick}] {self.msg_id} {self.sender} -> {self.receiver} | "
                f"{self.performative} | {self.ontology} | {self.content.get('event')}")


def _upgrade(msg):
    """Convert a message created with the old ACLMessage class to the unified format."""
    if hasattr(msg, "msg_id"):
        return msg
    return ACLMessage(msg.sender, msg.receiver, msg.performative,
                      msg.ontology, msg.content, msg.tick)


def validate_acl(msg):
    """Reject any message that does not follow the shared format."""
    errors = []
    for name in ("sender", "receiver"):
        value = getattr(msg, name, None)
        if not isinstance(value, str) or not value:
            errors.append(f"{name} must be a non-empty string")
    if msg.performative not in PERFORMATIVES:
        errors.append(f"unknown performative {msg.performative!r}")
    if msg.ontology not in ONTOLOGIES:
        errors.append(f"unknown ontology {msg.ontology!r}")
    if not isinstance(msg.content, dict) or "event" not in msg.content:
        errors.append("content must be a dict with an 'event' key")
    if not isinstance(msg.tick, int):
        errors.append("tick must be an int")
    if errors:
        raise ValueError("Invalid ACL message: " + "; ".join(errors))
    return msg


class MessageBus:
    """Shared messaging mechanism: validates, logs and delivers every message.

    post(msg)    -> one-way INFORM (delivered to receiver.receive if it has one)
    request(msg) -> synchronous REQUEST, returns the reply (INFORM / ACCEPT / REFUSE)
    """
    BUS_NAME = "message_bus"

    def __init__(self, env):
        self.env = env
        self.agents = {}
        self.log = []
        self._conversations = itertools.count(1)

    def register(self, *agents):
        for agent in agents:
            self.agents[agent.name] = agent

    def new_conversation(self):
        return f"C{next(self._conversations):04d}"

    def is_available(self, name):
        agent = self.agents.get(name)
        if agent is None or not getattr(agent, "online", True):
            return False
        # Scenario S3 simulates an agent crash by overriding step() on the instance.
        return "step" not in vars(agent)

    def post(self, msg, deliver=True):
        msg = validate_acl(_upgrade(msg))
        if msg.conversation_id is None:
            msg.conversation_id = self.new_conversation()
        self.log.append(msg)
        receiver = self.agents.get(msg.receiver)
        if deliver and receiver is not None and hasattr(receiver, "receive") \
                and self.is_available(msg.receiver):
            receiver.receive(self.env, msg)
        return msg

    def request(self, msg):
        if msg.performative != "REQUEST":
            raise ValueError("request() only sends REQUEST messages")
        msg = self.post(msg, deliver=False)
        receiver = self.agents.get(msg.receiver)
        tick = self.env.tick

        if not self.is_available(msg.receiver):
            # The receiver is down: the bus answers honestly instead of inventing data.
            reply = ACLMessage(self.BUS_NAME, msg.sender, "REFUSE", msg.ontology,
                               {"event": "RECEIVER_UNAVAILABLE",
                                "request_event": msg.content.get("event"),
                                "reason": f"{msg.receiver} is offline or not registered"},
                               tick)
        elif not hasattr(receiver, "handle_request"):
            reply = ACLMessage(msg.receiver, msg.sender, "REFUSE", msg.ontology,
                               {"event": "REQUEST_NOT_SUPPORTED",
                                "request_event": msg.content.get("event")}, tick)
        else:
            try:
                reply = receiver.handle_request(self.env, msg)
            except (ValueError, KeyError, TypeError) as error:
                reply = ACLMessage(msg.receiver, msg.sender, "REFUSE", msg.ontology,
                                   {"event": "REQUEST_REFUSED",
                                    "request_event": msg.content.get("event"),
                                    "reason": str(error)}, tick)

        reply = _upgrade(reply)
        reply.conversation_id = msg.conversation_id
        reply.in_reply_to = msg.msg_id
        return self.post(reply, deliver=False)

    def conversation(self, conversation_id):
        return [m for m in self.log if m.conversation_id == conversation_id]


# ============================================================================
# Cell 14 — Queryable agents, security staff and management endpoints (Student 4)
# ============================================================================

# Cell 14 — Agents the coordinator can query (REQUEST -> INFORM / ACCEPT / REFUSE)
# These subclasses only ADD request handlers; the team's original step() logic is unchanged.

class QueryableVisitorMonitoringAgent(VisitorMonitoringAgent):
    """Visitor agent + answers 'who is near artifact X?' using cameras only."""
    online = True

    def handle_request(self, env, request):
        if (request.ontology != "visitor_behavior"
                or request.content.get("event") != "VISITORS_NEAR_QUERY"):
            raise ValueError("Unsupported visitor query")
        artifact_id = request.content["artifact_id"]
        artifact = env.artifacts[artifact_id]
        hall = env.hall_for(artifact.home_position)
        covered = any(c.active and c.hall == hall for c in env.cameras.values())
        near = [
            {"visitor_id": obs["visitor_id"],
             "position": [round(v, 2) for v in obs["position"]],
             "camera_id": obs["camera_id"]}
            for obs in env.observed_visitors()
            if obs["hall"] == hall and min(
                dist(obs["position"], artifact.home_position),
                dist(obs["position"], artifact.position)) <= env.PROTECTION_RADIUS
        ]
        return ACLMessage(self.name, request.sender, "INFORM", "visitor_behavior",
                          {"event": "VISITORS_NEAR_REPLY", "artifact_id": artifact_id,
                           "hall": hall, "camera_coverage": covered, "visitors": near},
                          env.tick)


class PermitAwareAccessControlAgent(AccessControlAgent):
    """Access agent + artifact-handling permits + public-area answers."""
    online = True
    ARTIFACT_HANDLER_ROLES = {"staff"}

    def __init__(self):
        super().__init__()
        self.artifact_permits = set()          # {(person_id, artifact_id)}

    def grant_artifact_permit(self, person_id, artifact_id):
        self.artifact_permits.add((person_id, artifact_id))

    def revoke_artifact_permit(self, person_id, artifact_id):
        self.artifact_permits.discard((person_id, artifact_id))

    def can_move_artifact(self, env, person_id, artifact_id):
        person = env.visitors.get(person_id)
        return (person is not None
                and person.role in self.ARTIFACT_HANDLER_ROLES
                and (person_id, artifact_id) in self.artifact_permits)

    def _refuse(self, env, request, reason, **extra):
        return ACLMessage(self.name, request.sender, "REFUSE", "access_control",
                          {"event": "PERMISSION_REFUSED", "reason": reason, **extra},
                          env.tick)

    def handle_request(self, env, request):
        if request.performative != "REQUEST" or request.ontology != "access_control":
            raise ValueError("Invalid access request")
        content = request.content
        person_id = content.get("visitor_id")
        if person_id not in env.visitors:
            return self._refuse(env, request, "unknown_person", visitor_id=person_id)
        person = env.visitors[person_id]

        if content.get("action") == "MOVE_ARTIFACT":
            artifact_id = content.get("artifact_id")
            if artifact_id not in env.artifacts:
                return self._refuse(env, request, "unknown_artifact", artifact_id=artifact_id)
            return ACLMessage(self.name, request.sender, "INFORM", "access_control",
                              {"event": "PERMISSION_REPLY", "action": "MOVE_ARTIFACT",
                               "visitor_id": person_id, "role": person.role,
                               "artifact_id": artifact_id,
                               "permit_on_file": (person_id, artifact_id) in self.artifact_permits,
                               "authorized": self.can_move_artifact(env, person_id, artifact_id)},
                              env.tick)

        zone = content.get("zone")
        if zone in env.RESTRICTED:
            return super().handle_request(env, request)      # original team logic
        if zone in env.HALLS or zone == "Passage":
            return ACLMessage(self.name, request.sender, "INFORM", "access_control",
                              {"event": "PERMISSION_REPLY", "action": "ENTER_ZONE",
                               "visitor_id": person_id, "role": person.role, "zone": zone,
                               "public_area": True, "authorized": True}, env.tick)
        return self._refuse(env, request, "unknown_zone", zone=zone)


class SecurityStaffAgent:
    """Simulated security team: receives alerts and ACCEPTs / REFUSEs guard dispatch."""
    name = "security_staff"
    agent_type = "Human endpoint (simulated)"
    online = True

    def __init__(self, guards=2):
        self.available_guards = guards
        self.assignments = {}      # incident_id -> guard_id
        self.alerts = []
        self._guard_ids = itertools.count(1)

    def receive(self, env, msg):
        event = msg.content.get("event")
        if event == "SECURITY_ALERT":
            self.alerts.append(msg)
        elif event == "INCIDENT_CLOSED" and msg.content.get("incident_id") in self.assignments:
            self.assignments.pop(msg.content["incident_id"])
            self.available_guards += 1

    def handle_request(self, env, request):
        if request.content.get("event") != "DISPATCH_GUARD":
            raise ValueError("Unsupported staff request")
        incident_id = request.content["incident_id"]
        if self.available_guards <= 0:
            return ACLMessage(self.name, request.sender, "REFUSE", "security_response",
                              {"event": "DISPATCH_REFUSED", "incident_id": incident_id,
                               "reason": "no_guard_available"}, env.tick)
        self.available_guards -= 1
        guard_id = f"G{next(self._guard_ids)}"
        self.assignments[incident_id] = guard_id
        return ACLMessage(self.name, request.sender, "ACCEPT", "security_response",
                          {"event": "DISPATCH_ACCEPTED", "incident_id": incident_id,
                           "guard_id": guard_id, "target": request.content.get("target")},
                          env.tick)


class NotificationEndpoint:
    """Passive receiver (e.g. museum management) that just stores INFORM messages."""
    online = True

    def __init__(self, name):
        self.name = name
        self.inbox = []

    def receive(self, env, msg):
        self.inbox.append(msg)


# ============================================================================
# Cell 15 — Security Coordination Agent: decision rules R1–R10 (Student 4)
# ============================================================================

# Cell 15 — Security Coordination Agent (the decision-maker)
# Explicit decision rules. Every decision stores the rule applied and the IDs
# of the messages that support it (objective O5: explain every decision).
DECISION_RULES = {
    "R1":  "Visitor approached an artifact + artifact IN_PLACE + public area -> LOG (approach alone is NOT an alarm)",
    "R2":  "Visitor lingering near an artifact + artifact IN_PLACE -> MONITOR (still no alarm)",
    "R3":  "Artifact MOVED and nobody nearby holds a verified permit -> ESCALATE",
    "R4":  "Artifact MOVED by a person holding a verified permit -> LOG (authorized relocation)",
    "R5":  "Display case TAMPERED -> ESCALATE (tampering is never authorized)",
    "R6":  "Unauthorized entry to a restricted zone confirmed by Access Control -> ALERT_STAFF",
    "R7":  "Confirmed unauthorized entry + an anomalous artifact in the same hall -> ESCALATE",
    "R8":  "Artifact reported back IN_PLACE -> LOG and close its open incident",
    "R9":  "Coverage gap reported -> MONITOR; decisions in that hall rely on sensors + access control",
    "R10": "Required evidence missing or contradictory -> MONITOR (never alarm on one unverified report)",
}
RESPONSE_LEVELS = ("LOG", "MONITOR", "ALERT_STAFF", "ESCALATE")


@dataclass
class Decision:
    decision_id: str
    tick: int
    rule: str
    level: str
    subject: str
    summary: str
    evidence: list                       # msg_ids supporting the decision
    conversation_id: str = None
    missing_evidence: list = field(default_factory=list)
    suspects: list = field(default_factory=list)
    response: str = ""


class SecurityCoordinationAgent:
    name = "security_coordination_agent"
    agent_type = "Deliberative (rule-based)"
    online = True

    VISITOR = "visitor_monitoring_agent"
    ARTIFACT = "artifact_monitoring_agent"
    ACCESS = "access_control_agent"
    STAFF = "security_staff"
    MANAGEMENT = "museum_management"
    # Strongest evidence first, so a tampering report is handled before a lingering report.
    PRIORITY = {"artifact_status": 0, "access_control": 1, "coverage": 2, "visitor_behavior": 3}

    def __init__(self, bus):
        self.bus = bus
        self.inbox = []
        self.decisions = []
        self.open_incidents = {}         # (artifact_id, status) -> Decision
        self.unmonitored_halls = set()
        self._ids = itertools.count(1)

    # ---------------- messaging helpers ----------------
    def receive(self, env, msg):
        self.inbox.append(msg)

    def _ask(self, env, receiver, ontology, content, conversation_id):
        return self.bus.request(ACLMessage(self.name, receiver, "REQUEST", ontology,
                                           content, env.tick, conversation_id))

    def _tell(self, env, receiver, ontology, content, conversation_id):
        return self.bus.post(ACLMessage(self.name, receiver, "INFORM", ontology,
                                        content, env.tick, conversation_id))

    # ---------------- main loop ----------------
    def step(self, env):
        start = len(self.bus.log)
        inbox = sorted(self.inbox, key=lambda m: self.PRIORITY.get(m.ontology, 9))
        self.inbox = []
        handlers = {
            ("INFORM", "artifact_status"): self._on_artifact_report,
            ("INFORM", "visitor_behavior"): self._on_visitor_report,
            ("INFORM", "access_control"): self._on_access_report,
            ("INFORM", "coverage"): self._on_coverage_report,
        }
        for msg in inbox:
            handler = handlers.get((msg.performative, msg.ontology))
            if handler:
                handler(env, msg)
        return self.bus.log[start:]          # every message this agent caused this tick

    # ---------------- decisions ----------------
    def _decide(self, env, rule, level, subject, summary, evidence, conversation_id,
                missing=(), suspects=()):
        decision = Decision(f"D{next(self._ids):04d}", env.tick, rule, level, subject, summary,
                            [m.msg_id for m in evidence], conversation_id,
                            list(missing), list(suspects))
        self.decisions.append(decision)
        if level in ("ALERT_STAFF", "ESCALATE"):
            self._respond(env, decision)
        return decision

    def _respond(self, env, d):
        alert = self._tell(env, self.STAFF, "security_response",
                           {"event": "SECURITY_ALERT", "incident_id": d.decision_id,
                            "level": d.level, "rule": d.rule, "subject": d.subject,
                            "summary": d.summary, "suspects": d.suspects,
                            "missing_evidence": d.missing_evidence}, d.conversation_id)
        d.evidence.append(alert.msg_id)
        d.response = "staff alerted"
        if d.level != "ESCALATE":
            return
        reply = self._ask(env, self.STAFF, "security_response",
                          {"event": "DISPATCH_GUARD", "incident_id": d.decision_id,
                           "target": d.subject}, d.conversation_id)
        d.evidence.append(reply.msg_id)
        if reply.performative == "ACCEPT":
            d.response = f"staff alerted; guard {reply.content['guard_id']} dispatched"
        else:
            note = self._tell(env, self.MANAGEMENT, "security_response",
                              {"event": "ESCALATION_NO_GUARD", "incident_id": d.decision_id,
                               "subject": d.subject, "reason": reply.content.get("reason")},
                              d.conversation_id)
            d.evidence.append(note.msg_id)
            d.response = "staff alerted; dispatch REFUSED -> management informed"

    # ---------------- rule application ----------------
    def _on_visitor_report(self, env, msg):
        event = msg.content["event"]
        if event not in ("ENTERED_PROTECTION_ZONE", "LINGERING"):
            return
        visitor_id, artifact_id = msg.content["visitor_id"], msg.content["artifact_id"]
        conv = msg.conversation_id
        # A visitor report alone is not enough -> request the missing evidence.
        status = self._ask(env, self.ARTIFACT, "artifact_status",
                           {"event": "ARTIFACT_STATUS_QUERY", "artifact_id": artifact_id}, conv)
        permission = self._ask(env, self.ACCESS, "access_control",
                               {"event": "PERMISSION_QUERY", "action": "ENTER_ZONE",
                                "visitor_id": visitor_id, "zone": msg.content["hall"]}, conv)
        evidence = [msg, status, permission]

        if status.performative != "INFORM":
            self._decide(env, "R10", "MONITOR", artifact_id,
                         f"{visitor_id} near {artifact_id}, but artifact state could not be verified",
                         evidence, conv, missing=["artifact_status"], suspects=[visitor_id])
            return
        if status.content["status"] != "IN_PLACE":
            self._artifact_anomaly(env, status, evidence, suspects=[visitor_id])
            return
        if permission.performative != "INFORM" or not permission.content.get("authorized"):
            self._decide(env, "R10", "MONITOR", visitor_id,
                         f"{visitor_id} near {artifact_id}; area permission not confirmed",
                         evidence, conv, missing=["access_permission"], suspects=[visitor_id])
            return
        if event == "LINGERING":
            self._decide(env, "R2", "MONITOR", artifact_id,
                         f"{visitor_id} lingering {msg.content['dwell_ticks']} ticks near "
                         f"{artifact_id}; artifact IN_PLACE, public area -> watch, no alarm",
                         evidence, conv, suspects=[visitor_id])
        else:
            self._decide(env, "R1", "LOG", artifact_id,
                         f"{visitor_id} approached {artifact_id}; artifact IN_PLACE, "
                         f"public area -> logged, no alarm", evidence, conv)

    def _on_artifact_report(self, env, msg):
        artifact_id, status = msg.content["artifact_id"], msg.content["status"]
        if status == "IN_PLACE":
            closed = [key for key in self.open_incidents if key[0] == artifact_id]
            evidence = [msg]
            for key in closed:
                incident = self.open_incidents.pop(key)
                evidence.append(self._tell(env, self.STAFF, "security_response",
                                           {"event": "INCIDENT_CLOSED",
                                            "incident_id": incident.decision_id},
                                           msg.conversation_id))
            self._decide(env, "R8", "LOG", artifact_id,
                         f"{artifact_id} back IN_PLACE; closed {len(closed)} incident(s)",
                         evidence, msg.conversation_id)
            return
        self._artifact_anomaly(env, msg, [msg])

    def _artifact_anomaly(self, env, status_msg, evidence, suspects=()):
        artifact_id = status_msg.content["artifact_id"]
        status = status_msg.content["status"]
        hall = status_msg.content.get("hall")
        key = (artifact_id, status)
        if key in self.open_incidents:                   # already handled: just add evidence
            incident = self.open_incidents[key]
            incident.evidence += [m.msg_id for m in evidence if m.msg_id not in incident.evidence]
            incident.suspects += [s for s in suspects if s not in incident.suspects]
            return incident

        conv = status_msg.conversation_id
        evidence = list(evidence)
        missing = []
        # Request more information: who was near the artifact?
        seen = self._ask(env, self.VISITOR, "visitor_behavior",
                         {"event": "VISITORS_NEAR_QUERY", "artifact_id": artifact_id}, conv)
        evidence.append(seen)
        nearby = []
        if seen.performative != "INFORM":
            missing.append("visual evidence: visitor monitoring unavailable")
        elif not seen.content["camera_coverage"]:
            missing.append(f"visual evidence: no active camera in {hall}")
        else:
            nearby = [v["visitor_id"] for v in seen.content["visitors"]]
        if hall in self.unmonitored_halls:
            missing.append(f"coverage gap reported for {hall}")
        candidates = list(dict.fromkeys(list(suspects) + nearby))

        if status == "TAMPERED":
            decision = self._decide(env, "R5", "ESCALATE", artifact_id,
                                    f"{artifact_id} display case TAMPERED", evidence, conv,
                                    missing, candidates)
        else:  # MOVED -> is there a permit?
            authorized_by = None
            for person_id in candidates:
                reply = self._ask(env, self.ACCESS, "access_control",
                                  {"event": "PERMISSION_QUERY", "action": "MOVE_ARTIFACT",
                                   "visitor_id": person_id, "artifact_id": artifact_id}, conv)
                evidence.append(reply)
                if reply.performative == "INFORM" and reply.content.get("authorized"):
                    authorized_by = person_id
                    break
            if authorized_by:
                decision = self._decide(env, "R4", "LOG", artifact_id,
                                        f"{artifact_id} MOVED by {authorized_by} who holds a "
                                        f"valid permit -> authorized relocation",
                                        evidence, conv, missing, [])
            else:
                who = ", ".join(candidates) if candidates else (
                    "nobody observed" if not missing else "person unknown")
                decision = self._decide(env, "R3", "ESCALATE", artifact_id,
                                        f"{artifact_id} MOVED without a verified permit ({who})",
                                        evidence, conv, missing, candidates)
        self.open_incidents[key] = decision
        return decision

    def _on_access_report(self, env, msg):
        if msg.content.get("event") != "UNAUTHORIZED_ENTRY":
            return
        visitor_id, zone = msg.content["visitor_id"], msg.content["zone"]
        conv = msg.conversation_id
        # Verify the report before acting on it.
        confirm = self._ask(env, self.ACCESS, "access_control",
                            {"event": "PERMISSION_QUERY", "action": "ENTER_ZONE",
                             "visitor_id": visitor_id, "zone": zone}, conv)
        evidence = [msg, confirm]
        (x1, x2, y1, y2), _ = env.RESTRICTED[zone]             # static museum map
        hall = env.hall_for(((x1 + x2) / 2, (y1 + y2) / 2))
        anomalous = []
        for artifact_id, artifact in env.artifacts.items():
            if env.hall_for(artifact.home_position) != hall:
                continue
            state = self._ask(env, self.ARTIFACT, "artifact_status",
                              {"event": "ARTIFACT_STATUS_QUERY", "artifact_id": artifact_id}, conv)
            evidence.append(state)
            if state.performative == "INFORM" and state.content["status"] != "IN_PLACE":
                anomalous.append(f"{artifact_id}:{state.content['status']}")

        if confirm.performative != "INFORM" or confirm.content.get("authorized"):
            self._decide(env, "R10", "MONITOR", visitor_id,
                         f"Entry report for {visitor_id} in {zone} not confirmed by verification",
                         evidence, conv, missing=["confirmed permission"], suspects=[visitor_id])
        elif anomalous:
            self._decide(env, "R7", "ESCALATE", zone,
                         f"{visitor_id} ({confirm.content.get('role') or msg.content.get('role')}) entered {zone} without "
                         f"permission while {', '.join(anomalous)} in {hall}",
                         evidence, conv, suspects=[visitor_id])
        else:
            self._decide(env, "R6", "ALERT_STAFF", zone,
                         f"{visitor_id} ({confirm.content.get('role') or msg.content.get('role')}) entered {zone} "
                         f"without permission", evidence, conv, suspects=[visitor_id])

    def _on_coverage_report(self, env, msg):
        hall = msg.content.get("hall")
        if msg.content.get("event") == "ZONE_UNMONITORED":
            self.unmonitored_halls.add(hall)
            self._decide(env, "R9", "MONITOR", hall,
                         f"{hall} unmonitored -> relying on artifact sensors and access control",
                         [msg], msg.conversation_id, missing=[f"camera coverage in {hall}"])
        elif msg.content.get("event") == "COVERAGE_RESTORED":
            self.unmonitored_halls.discard(hall)
            self._decide(env, "R9", "LOG", hall, f"Coverage restored in {hall}",
                         [msg], msg.conversation_id)

    # ---------------- requests addressed TO the coordinator ----------------
    def handle_request(self, env, request):
        """E.g. the Coverage Management Agent asks the coordinator to rely on sensors."""
        content = request.content
        if request.ontology == "coverage" and content.get("event") == "RELY_ON_SENSORS":
            hall = content.get("hall")
            if hall not in env.HALLS:
                return ACLMessage(self.name, request.sender, "REFUSE", "coverage",
                                  {"event": "RELY_ON_SENSORS_REFUSED", "hall": hall,
                                   "reason": "unknown_hall"}, env.tick)
            self.unmonitored_halls.add(hall)
            self._decide(env, "R9", "MONITOR", hall,
                         f"Coverage agent asked to rely on sensors in {hall}",
                         [request], request.conversation_id,
                         missing=[f"camera coverage in {hall}"])
            return ACLMessage(self.name, request.sender, "ACCEPT", "coverage",
                              {"event": "RELY_ON_SENSORS_ACCEPTED", "hall": hall,
                               "fallback": ["artifact_sensors", "access_control"]}, env.tick)
        return ACLMessage(self.name, request.sender, "REFUSE", request.ontology,
                          {"event": "REQUEST_NOT_SUPPORTED",
                           "request_event": content.get("event")}, env.tick)


# ============================================================================
# Cell 16 — Coordinator in the simulation + scenarios S5–S7 (Student 4)
# ============================================================================

# Cell 16 — Plug the coordinator into the simulation and the dashboard

_PreCoordinatorLiveMuseum = globals().get("_PreCoordinatorLiveMuseum", LiveMuseum)


class LiveMuseum(_PreCoordinatorLiveMuseum):

    def __init__(self, seed=42, spawn_every=9, max_visitors=7, dwell_threshold=3, guards=2):
        super().__init__(seed=seed, spawn_every=spawn_every,
                         max_visitors=max_visitors, dwell_threshold=dwell_threshold)
        # Same agents, extended with request handlers (state is still empty here).
        self.visitor_agent = QueryableVisitorMonitoringAgent(dwell_threshold)
        self.access_agent = PermitAwareAccessControlAgent()

        self.bus = MessageBus(self.env)
        self.staff = SecurityStaffAgent(guards)
        self.management = NotificationEndpoint("museum_management")
        self.coordinator = SecurityCoordinationAgent(self.bus)
        self.bus.register(self.visitor_agent, self.artifact_agent, self.access_agent,
                          self.coordinator, self.staff, self.management)

    @property
    def decisions(self):
        return self.coordinator.decisions

    def step(self):
        reports = super().step()              # visitor + artifact + access reports
        for message in reports:
            self.bus.post(message)            # validated, logged, delivered to the coordinator
        coordination = self.coordinator.step(self.env)
        self.messages.extend(coordination)
        return reports + coordination


_PreCoordinatorDashboard = globals().get("_PreCoordinatorDashboard", MuseumLiveDashboard)


class MuseumLiveDashboard(_PreCoordinatorDashboard):

    def __init__(self, seed=42):
        super().__init__(seed=seed)
        options = list(self.scenario.options)
        for label, value in [("S5 - Artifact Moved Without Permit", "S5"),
                             ("S6 - Authorized Staff Relocation", "S6"),
                             ("S7 - Artifact Moved, Camera Down", "S7")]:
            if not any(v == value for _, v in options):
                options.append((label, value))
        self.scenario.options = options

    @staticmethod
    def apply_scenario_event(context):
        _PreCoordinatorDashboard.apply_scenario_event(context)
        sim, env = context.sim, context.sim.env
        tick, mode = env.tick, context.mode

        if mode == "S3" and tick == 0:
            sim.visitor_agent.online = False
        if mode in ("S5", "S6", "S7") and tick < 3 and "V1" in env.visitors:
            env.move_visitor("V1", (4.1, 5.05))
        if mode == "S6" and tick == 0:
            env.visitors["V1"].role = "staff"
            sim.access_agent.grant_artifact_permit("V1", "A1")
        if mode == "S7" and tick == 0:
            env.set_camera("CAM_A", False)
            env.set_camera("CAM_BACKUP", False)
        if mode in ("S5", "S6", "S7") and tick == 2:
            env.move_artifact("A1", (4.7, 4.6))

    def render(self):
        super().render()
        coordinator = self.sim.coordinator
        with self.output:
            alarms = [d for d in coordinator.decisions if d.level in ("ALERT_STAFF", "ESCALATE")]
            print("\nSecurity Coordination Agent: ONLINE")
            print("-----------------------------------")
            print(f"Decisions: {len(coordinator.decisions)} | Alerts/Escalations: {len(alarms)}"
                  f" | Guards available: {self.sim.staff.available_guards}"
                  f" | Unmonitored halls: {sorted(coordinator.unmonitored_halls) or '-'}")
            for d in coordinator.decisions[-5:]:
                line = f"T{d.tick} {d.decision_id} [{d.level}] {d.rule}: {d.summary}"
                if d.missing_evidence:
                    line += f" | missing: {', '.join(d.missing_evidence)}"
                if d.response:
                    line += f" | {d.response}"
                print(line)


# ============================================================================
# Cell 17 — Coverage Management Agent (Student 5)
# ============================================================================

# Cell 17 — Coverage Management Agent (Student 5)
# Monitors the health of every camera and monitoring agent through periodic
# HEARTBEAT signals. A unit that misses `heartbeat_timeout` heartbeats is declared
# FAILED, the hall it covered becomes a blind zone, and a standby camera is asked
# to take over (REQUEST -> ACCEPT / REFUSE). If nobody can cover the hall, the
# Security Coordination Agent is asked to rely on artifact sensors and access
# control (REQUEST RELY_ON_SENSORS, rule R9). Recovery is reported with INFORM.
# All messages go through the team's MessageBus with ontology "coverage".

ACTIVE, STANDBY, COVERING, FAILED = "ACTIVE", "STANDBY", "COVERING", "FAILED"
OPERATING = (ACTIVE, COVERING)


def _contains(outer, inner):
    """True if rectangle `outer` (xmin, xmax, ymin, ymax) fully covers `inner`."""
    return (outer[0] <= inner[0] and outer[1] >= inner[1]
            and outer[2] <= inner[2] and outer[3] >= inner[3])


class CameraUnitAgent:
    """One camera as an agent: sends heartbeats and answers coverage requests.

    Primary cameras stream all the time. Standby cameras stay idle until the
    Coverage Agent asks them to take over. A failed primary camera is silent.
    """
    online = True

    def __init__(self, camera_id, role="primary", available=True):
        self.camera_id = camera_id
        self.name = f"camera_unit_{camera_id.lower()}"
        self.role = role                 # "primary" or "standby"
        self.available = available       # False = under maintenance
        self.assigned_hall = None        # hall covered after a takeover

    def heartbeat(self, env):
        """INFORM heartbeat, or None when the camera is down (silent failure)."""
        camera = env.cameras[self.camera_id]
        if camera.active:
            status = COVERING if self.assigned_hall else ACTIVE
        elif self.role == "standby":
            status = STANDBY             # powered and idle, can still be asked
        else:
            return None
        return ACLMessage(self.name, CoverageManagementAgent.name, "INFORM", "coverage",
                          {"event": "HEARTBEAT", "unit_id": self.camera_id,
                           "status": status, "available": self.available}, env.tick)

    def handle_request(self, env, request):
        action = request.content.get("event")
        hall = request.content.get("hall")
        camera = env.cameras[self.camera_id]

        def reply(performative, event, **extra):
            return ACLMessage(self.name, request.sender, performative, "coverage",
                              {"event": event, "unit_id": self.camera_id,
                               "hall": hall, **extra}, env.tick)

        if action == "RELEASE_REQUEST":
            self.assigned_hall = None
            env.set_camera(self.camera_id, False)
            return reply("INFORM", "COVERAGE_RELEASED")
        if action != "TAKEOVER_REQUEST":
            return reply("REFUSE", "TAKEOVER_REFUSED", reason="unknown_action")
        if not self.available:
            return reply("REFUSE", "TAKEOVER_REFUSED", reason="unit_under_maintenance")
        if not _contains(camera.bounds, env.HALLS[hall]):
            return reply("REFUSE", "TAKEOVER_REFUSED", reason="hall_out_of_range")
        if camera.active or self.assigned_hall:
            return reply("REFUSE", "TAKEOVER_REFUSED", reason="already_assigned")
        self.assigned_hall = hall
        env.set_camera(self.camera_id, True)
        return reply("ACCEPT", "TAKEOVER_ACCEPTED")


class CoverageManagementAgent:
    """Hybrid agent: reactive failure detection + deliberative recovery planning."""
    name = "coverage_management_agent"
    agent_type = "Hybrid (reactive detection + deliberative recovery)"
    online = True
    COORDINATOR = "security_coordination_agent"
    MANAGEMENT = "museum_management"
    MONITORED_AGENTS = ("visitor_monitoring_agent", "artifact_monitoring_agent",
                        "access_control_agent", "security_coordination_agent")

    def __init__(self, bus, camera_units, heartbeat_timeout=2, retry_interval=5):
        self.bus = bus
        self.camera_units = camera_units
        self.heartbeat_timeout = heartbeat_timeout
        self.retry_interval = retry_interval
        env = bus.env
        # Belief base: what the agent believes about every unit.
        self.units = {}
        for cid, unit in camera_units.items():
            self.units[cid] = {"type": "camera", "role": unit.role,
                               "state": ACTIVE if env.cameras[cid].active else STANDBY,
                               "last_seen": env.tick, "failed_at": None, "reported": None}
        for agent_name in self.MONITORED_AGENTS:
            self.units[agent_name] = {"type": "agent", "role": "agent", "state": ACTIVE,
                                      "last_seen": env.tick, "failed_at": None,
                                      "reported": ACTIVE}
        self.blind_since = {}            # hall -> tick coverage was lost
        self.next_retry = {}             # hall -> tick of next takeover attempt
        self.reported_unmonitored = set()
        self.heartbeats_received = 0

    # ---------- perception ----------
    def collect_heartbeats(self, env):
        beats = [hb for unit in self.camera_units.values()
                 if (hb := unit.heartbeat(env)) is not None]
        for agent_name in self.MONITORED_AGENTS:
            if self.bus.is_available(agent_name):
                beats.append(ACLMessage(agent_name, self.name, "INFORM", "coverage",
                                        {"event": "HEARTBEAT", "unit_id": agent_name,
                                         "status": ACTIVE, "available": True}, env.tick))
        return beats

    def receive_heartbeats(self, beats):
        for hb in beats:
            unit = self.units.get(hb.content["unit_id"])
            if unit is not None:
                unit["last_seen"] = hb.tick
                unit["reported"] = hb.content["status"]
                self.heartbeats_received += 1

    def missed(self, unit_id, tick):
        return tick - self.units[unit_id]["last_seen"]

    # ---------- world model ----------
    def halls_of(self, env, camera_id):
        bounds = env.cameras[camera_id].bounds
        return [h for h, hb in env.HALLS.items() if _contains(bounds, hb)]

    def blind_halls(self, env):
        covered = set()
        for uid, u in self.units.items():
            if u["type"] == "camera" and u["state"] in OPERATING:
                covered.update(self.halls_of(env, uid))
        return [h for h in env.HALLS if h not in covered]

    def artifacts_in(self, env, hall):
        return [a.artifact_id for a in env.artifacts.values()
                if env.hall_for(a.home_position) == hall]

    def coverage_ratio(self, env):
        return 1 - len(self.blind_halls(env)) / len(env.HALLS)

    # ---------- messaging ----------
    def _inform(self, env, receiver, content):
        return self.bus.post(ACLMessage(self.name, receiver, "INFORM", "coverage",
                                        content, env.tick))

    def _request(self, env, receiver, content, conversation_id=None):
        return self.bus.request(ACLMessage(self.name, receiver, "REQUEST", "coverage",
                                           content, env.tick, conversation_id))

    # ---------- behaviour 1: failure detection (reactive) ----------
    def detect_failures(self, env):
        for uid, u in self.units.items():
            missed = self.missed(uid, env.tick)
            if u["state"] in OPERATING and missed >= self.heartbeat_timeout:
                halls = self.halls_of(env, uid) if u["type"] == "camera" else []
                u["state"], u["failed_at"] = FAILED, env.tick
                if u["type"] == "camera" and self.camera_units[uid].assigned_hall:
                    self.camera_units[uid].assigned_hall = None
                event = ("CAMERA_FAILURE_DETECTED" if u["type"] == "camera"
                         else "AGENT_FAILURE_DETECTED")
                self._inform(env, self.COORDINATOR,
                             {"event": event, "unit_id": uid, "missed_heartbeats": missed,
                              "affected_halls": halls})
            elif u["state"] == FAILED and missed == 0:
                downtime = env.tick - u["failed_at"]
                u["state"] = STANDBY if u["reported"] == STANDBY else ACTIVE
                u["failed_at"] = None
                event = ("CAMERA_RECOVERED" if u["type"] == "camera" else "AGENT_RECOVERED")
                self._inform(env, self.COORDINATOR,
                             {"event": event, "unit_id": uid, "downtime_ticks": downtime})
            elif missed == 0 and u["type"] == "camera":
                # Keep beliefs in line with what the unit itself reports
                # (e.g. an operator switched the backup on or off by hand).
                if u["state"] == STANDBY and u["reported"] == ACTIVE:
                    u["state"] = ACTIVE
                elif u["state"] in OPERATING and u["reported"] == STANDBY:
                    u["state"] = STANDBY
                    self.camera_units[uid].assigned_hall = None

    # ---------- behaviour 2: coverage recovery (deliberative) ----------
    def candidates(self, env, hall):
        """Healthy idle standby units, those that can reach the hall first."""
        units = [uid for uid, u in self.units.items()
                 if u["type"] == "camera" and u["role"] == "standby"
                 and u["state"] == STANDBY and self.missed(uid, env.tick) == 0]
        return sorted(units, key=lambda uid: not _contains(env.cameras[uid].bounds,
                                                           env.HALLS[hall]))

    def recover_coverage(self, env):
        for hall in self.blind_halls(env):
            self.blind_since.setdefault(hall, env.tick)
            if self.next_retry.get(hall, env.tick) > env.tick:
                continue
            failed = next((uid for uid, u in self.units.items() if u["state"] == FAILED
                           and u["type"] == "camera" and hall in self.halls_of(env, uid)), None)
            conversation = self.bus.new_conversation()
            accepted, refusals = None, []
            for uid in self.candidates(env, hall):
                reply = self._request(env, self.camera_units[uid].name,
                                      {"event": "TAKEOVER_REQUEST", "hall": hall,
                                       "failed_unit": failed}, conversation)
                if reply.performative == "ACCEPT":
                    accepted = uid
                    self.units[uid]["state"] = COVERING
                    break
                refusals.append(f"{uid}: {reply.content.get('reason')}")

            if accepted:
                self.next_retry.pop(hall, None)
                self._inform(env, self.COORDINATOR,
                             {"event": "COVERAGE_TRANSFERRED", "hall": hall,
                              "failed_unit": failed, "covered_by": accepted,
                              "blind_ticks": env.tick - self.blind_since.pop(hall)})
                if hall in self.reported_unmonitored:
                    self.reported_unmonitored.discard(hall)
                    self._inform(env, self.COORDINATOR,
                                 {"event": "COVERAGE_RESTORED", "hall": hall,
                                  "restored_by": accepted})
                continue

            self.next_retry[hall] = env.tick + self.retry_interval
            if hall in self.reported_unmonitored:
                continue
            # Coverage cannot be restored: never assume every failure is recoverable.
            self.reported_unmonitored.add(hall)
            reply = self._request(env, self.COORDINATOR,
                                  {"event": "RELY_ON_SENSORS", "hall": hall,
                                   "failed_unit": failed,
                                   "artifacts_at_risk": self.artifacts_in(env, hall),
                                   "refusals": refusals}, conversation)
            if reply.performative != "ACCEPT":
                self._inform(env, self.MANAGEMENT,
                             {"event": "ZONE_UNMONITORED", "hall": hall,
                              "reason": "coordinator unavailable",
                              "artifacts_at_risk": self.artifacts_in(env, hall)})

    # ---------- behaviour 3: release backups / report restored halls ----------
    def release_and_restore(self, env):
        for uid, u in self.units.items():
            hall = self.camera_units[uid].assigned_hall if uid in self.camera_units else None
            if u["state"] != COVERING or hall is None:
                continue
            primary_back = any(o["type"] == "camera" and o["state"] == ACTIVE and oid != uid
                               and hall in self.halls_of(env, oid)
                               for oid, o in self.units.items())
            if primary_back:
                self._request(env, self.camera_units[uid].name,
                              {"event": "RELEASE_REQUEST", "hall": hall})
                u["state"] = STANDBY
        blind = set(self.blind_halls(env))
        for hall in list(self.reported_unmonitored):
            if hall not in blind:
                self.reported_unmonitored.discard(hall)
                self.blind_since.pop(hall, None)
                self.next_retry.pop(hall, None)
                self._inform(env, self.COORDINATOR,
                             {"event": "COVERAGE_RESTORED", "hall": hall,
                              "restored_by": "camera recovery"})
        for hall in list(self.blind_since):
            if hall not in blind:
                self.blind_since.pop(hall)

    # ---------- perceive -> decide -> act ----------
    def step(self, env):
        start = len(self.bus.log)
        self.receive_heartbeats(self.collect_heartbeats(env))
        self.detect_failures(env)
        self.recover_coverage(env)
        self.release_and_restore(env)
        return self.bus.log[start:]

    # ---------- answers status queries ----------
    def handle_request(self, env, request):
        if request.content.get("event") != "COVERAGE_STATUS_QUERY":
            raise ValueError("Unsupported coverage request")
        return ACLMessage(self.name, request.sender, "INFORM", "coverage",
                          {"event": "COVERAGE_STATUS_REPLY", **self.report(env)}, env.tick)

    def report(self, env):
        blind = self.blind_halls(env)
        return {"coverage_ratio": round(self.coverage_ratio(env), 2),
                "blind_halls": blind,
                "artifacts_unmonitored": [a for h in blind for a in self.artifacts_in(env, h)],
                "units": {uid: {"state": u["state"], "missed": self.missed(uid, env.tick)}
                          for uid, u in self.units.items()}}


# ---------- plug the agent into the simulation ----------
_PreCoverageLiveMuseum = globals().get("_PreCoverageLiveMuseum", LiveMuseum)


class LiveMuseum(_PreCoverageLiveMuseum):

    def __init__(self, seed=42, spawn_every=9, max_visitors=7, dwell_threshold=3,
                 guards=2, heartbeat_timeout=2):
        super().__init__(seed=seed, spawn_every=spawn_every, max_visitors=max_visitors,
                         dwell_threshold=dwell_threshold, guards=guards)
        self.camera_units = {cid: CameraUnitAgent(cid, "standby" if cid == "CAM_BACKUP"
                                                  else "primary")
                             for cid in self.env.cameras}
        self.coverage_agent = CoverageManagementAgent(self.bus, self.camera_units,
                                                      heartbeat_timeout=heartbeat_timeout)
        self.bus.register(self.coverage_agent, *self.camera_units.values())

    def step(self):
        reports = super().step()             # monitoring agents + coordinator
        coverage = self.coverage_agent.step(self.env)
        self.messages.extend(coverage)
        return reports + coverage


# ============================================================================
# Cell 18 — Coverage Management in the dashboard: scenarios S8–S9 (Student 5)
# ============================================================================

# Cell 18 — Coverage Management in the dashboard (scenarios S8, S9)
# Adds: CAM_B switch, coverage panel, blind-zone overlay on the map and two
# scenarios. S3 and S7 now state explicitly that the backup is under maintenance,
# so the Coverage Agent's takeover is REFUSEd there (their original story).

_PreCoverageMuseumFigure = globals().get("_PreCoverageMuseumFigure", museum_figure)


def museum_figure(sim):
    """Team map + the Coverage Agent's beliefs (blind halls, failed / covering cameras)."""
    fig = _PreCoverageMuseumFigure(sim)
    agent = getattr(sim, "coverage_agent", None)
    if agent is None:
        return fig
    ax, env = fig.axes[0], sim.env
    for hall in agent.blind_halls(env):
        xmin, xmax, ymin, ymax = env.HALLS[hall]
        ax.add_patch(Rectangle((xmin + .08, ymin + .08), xmax - xmin - .16, ymax - ymin - .16,
                               facecolor="#C43B49", alpha=.10, edgecolor="#C43B49",
                               hatch="xx", zorder=2.5))
        ax.text((xmin + xmax) / 2, 1.0, "BLIND ZONE - coverage lost", ha="center",
                fontsize=9, weight="bold", color="#9B2929", zorder=12)
    label_pos = {"CAM_A": (.9, 7.9), "CAM_B": (10.9, 7.9), "CAM_BACKUP": (6.6, 1.3)}
    for uid, (x, y) in label_pos.items():
        unit = agent.units[uid]
        note = {FAILED: ("FAILED (heartbeat timeout)", "#9B2929"),
                COVERING: (f"COVERING {sim.camera_units[uid].assigned_hall}", "#0F988D"),
                STANDBY: ("STANDBY" if sim.camera_units[uid].available
                          else "STANDBY (maintenance)", "#536A82")}.get(unit["state"])
        if note:
            ax.text(x + .23, y - .38, note[0], fontsize=6.8, weight="bold",
                    color=note[1], zorder=12)
    return fig


_PreCoverageDashboard = globals().get("_PreCoverageDashboard", MuseumLiveDashboard)


class MuseumLiveDashboard(_PreCoverageDashboard):

    def __init__(self, seed=42):
        self.cam_b = widgets.Checkbox(value=True, description="Camera B")
        super().__init__(seed=seed)
        options = list(self.scenario.options)
        for label, value in [("S8 - Camera Failure, Backup Takes Over", "S8"),
                             ("S9 - Camera Failure, No Backup Possible", "S9")]:
            if not any(v == value for _, v in options):
                options.append((label, value))
        self.scenario.options = options
        self.cam_b.observe(self.update_cameras, names="value")

    @staticmethod
    def apply_scenario_event(context):
        _PreCoverageDashboard.apply_scenario_event(context)
        sim, env = context.sim, context.sim.env
        tick, mode = env.tick, context.mode
        if mode in ("S3", "S7") and tick == 0:
            sim.camera_units["CAM_BACKUP"].available = False      # under maintenance
        if mode == "S8":
            if tick < 3 and "V1" in env.visitors:
                env.move_visitor("V1", (4.1, 5.05))
            if tick == 0:
                env.set_camera("CAM_A", False)                     # silent failure
            if tick == 3:
                env.set_camera("CAM_A", True)                      # repaired
        if mode == "S9":
            if tick < 3 and "V1" in env.visitors:
                env.move_visitor("V1", (14, 5))
            if tick == 0:
                env.set_camera("CAM_B", False)                     # backup cannot reach Hall B
            if tick == 2:
                env.move_artifact("A2", (15, 4))                   # moved while Hall B is blind

    # ---- keep the switches in line with the real camera state ----
    def _sync_switches(self):
        for box in (self.cam_a, self.cam_b, self.backup):
            box.unobserve(self.update_cameras, names="value")
        cams = self.sim.env.cameras
        self.cam_a.value = cams["CAM_A"].active
        self.cam_b.value = cams["CAM_B"].active
        self.backup.value = cams["CAM_BACKUP"].active
        for box in (self.cam_a, self.cam_b, self.backup):
            box.observe(self.update_cameras, names="value")

    def update_cameras(self, change):
        self.sim.env.set_camera("CAM_B", self.cam_b.value)
        super().update_cameras(change)

    def load_mode(self):
        # Every mode starts from the default hardware state, so a camera left
        # off by the previous scenario never leaks into the next one.
        for box in (self.cam_a, self.cam_b, self.backup):
            box.unobserve(self.update_cameras, names="value")
        self.cam_a.value, self.cam_b.value, self.backup.value = True, True, False
        for box in (self.cam_a, self.cam_b, self.backup):
            box.observe(self.update_cameras, names="value")
        super().load_mode()
        self.sim.env.set_camera("CAM_B", self.cam_b.value)

    def step_once(self):
        progressed = super().step_once()
        self._sync_switches()
        return progressed

    def render(self):
        super().render()
        agent = getattr(self.sim, "coverage_agent", None)
        if agent is None:
            return
        report = agent.report(self.sim.env)
        with self.output:
            print("\nCoverage Management Agent: ONLINE")
            print("---------------------------------")
            print(f"Coverage: {report['coverage_ratio']:.0%} of halls"
                  f" | Blind halls: {', '.join(report['blind_halls']) or '-'}"
                  f" | Unmonitored artifacts: "
                  f"{', '.join(report['artifacts_unmonitored']) or '-'}")
            for uid, unit in report["units"].items():
                print(f"  {uid}: {unit['state']} (missed heartbeats: {unit['missed']})")

    def show(self):
        try:
            from google.colab import output as colab_output
            colab_output.enable_custom_widget_manager()
        except ImportError:
            pass
        display(widgets.VBox([
            widgets.HBox([self.scenario, self.load_button]),
            widgets.HBox([self.play, self.pause, self.single, self.reset, self.tamper]),
            widgets.HBox([self.cam_a, self.cam_b, self.backup]),
            self.spawn, self.capacity, self.dwell, self.suspicion, self.delay,
            widgets.HBox([self.clock, self.clock_status]),
            self.output,
        ]))
        self.render()
