# Irth | إرث — A Multi-Agent System for Museum Artifact Protection

CAI 461 – Agent-Based Systems · Princess Nourah bint Abdulrahman University
Supervised by Dr. Eman ALjabarti

Irth protects artifacts in a simulated two-hall museum. Five agents each observe
one part of the situation and share what they know through a unified ACL-like
message format (`INFORM`, `REQUEST`, `ACCEPT`, `REFUSE`) on a shared Message Bus.
A single observation never raises an alarm on its own: the Security Coordination
Agent combines evidence with explicit rules (R1–R10), and every decision records
the rule applied and the messages that support it.

## Agents

| Agent | Type | Role | Owner |
|---|---|---|---|
| Visitor Monitoring Agent | Reactive | Reports visitors approaching (`ENTERED_PROTECTION_ZONE`) or lingering (`LINGERING`) near an artifact; sees only what active cameras cover | Student 1 |
| Artifact Monitoring Agent | Reactive | Reads artifact sensors and reports `IN_PLACE`, `MOVED`, `TAMPERED` | Student 2 |
| Access Control Agent | Reactive | Distinguishes visitors from staff, reports `UNAUTHORIZED_ENTRY`, answers permission and artifact-permit requests | Student 3 |
| Security Coordination Agent | Deliberative (rule-based) | Combines reports, requests missing evidence, applies rules R1–R10, alerts staff and dispatches guards | Student 4 |
| Coverage Management Agent | Hybrid | Tracks heartbeats of cameras and agents, detects failures, negotiates backup coverage, asks the coordinator to rely on sensors when a hall stays blind | Student 5 |

Supporting endpoints: camera unit agents (one per camera), simulated security
staff (accept / refuse guard dispatch) and museum management (notifications).

## Repository layout

```
Irth/
├── Irth.ipynb               # main deliverable: all cells, tests, live dashboard (Colab)
├── main.py                  # headless entry point - no Jupyter needed
├── requirements.txt
├── irth/
│   ├── __init__.py
│   └── system.py            # system code exported from the notebook (auto-generated)
├── tools/
│   └── export_notebook.py   # regenerates irth/system.py from Irth.ipynb
├── tests/
│   └── test_system.py       # runs the notebook's test cells + system-level checks
└── outputs/                 # frames saved by main.py --save
```

`Irth.ipynb` is the single source of truth. `irth/system.py` is generated from it,
and a test fails if the two ever differ.

## Installation

Python 3.9 or newer.

```bash
pip install -r requirements.txt
```

## Running

**Interactive dashboard.** Open `Irth.ipynb` in Google Colab (or Jupyter) and
choose *Runtime → Run all*. The test cells print their results; the last cell
opens the dashboard. Choose a *Mode*, press **Load**, then **Start** (automatic
clock) or **Next Step**. Cameras can be switched off at any time — the Coverage
Management Agent reacts on its own and the switches follow the real camera state.

**Command line.**

```bash
python main.py                        # run scenarios S1-S9 with the message log
python main.py --scenario S8 -v       # one scenario, including message contents
python main.py --scenario S9 --save   # also save map frames to outputs/
python main.py --live 80              # free-roam museum with random visitors
pytest -q                             # all automated tests (18)
```

## Scenarios (all in the dashboard *Mode* menu)

| Mode | Situation | Expected outcome |
|---|---|---|
| S1 | Normal visit: V1 approaches A1 and lingers | R1 LOG, R2 MONITOR, no alarm |
| S2 | A1 display case tampered | R5 ESCALATE at T3, guard dispatched |
| S3 | CAM_A down, backup under maintenance, Visitor Agent crashes, A1 tampered | Backup REFUSEs → R9 MONITOR; tampering still escalated (R5) from the sensor |
| S4 | Visitor enters Storage A | R6 ALERT_STAFF |
| S5 | A1 moved by a visitor without a permit | R3 ESCALATE |
| S6 | A1 relocated by staff holding a permit | R4 LOG, no alarm |
| S7 | A1 moved while CAM_A and backup are down | R9 MONITOR, R3 ESCALATE with missing visual evidence |
| S8 | CAM_A fails, then is repaired | Failure detected at T2, backup ACCEPTs, visitor seen via backup, backup released after repair |
| S9 | CAM_B fails, backup cannot reach Hall B, A2 moved | Backup REFUSEs (out of range) → RELY_ON_SENSORS ACCEPTed → R3 ESCALATE from the sensor |

## Coverage Management protocol

```
units ─ INFORM(HEARTBEAT) every tick ─▶ Coverage Agent
missed heartbeats ≥ heartbeat_timeout ─▶ unit FAILED, hall becomes blind
Coverage ─ INFORM(CAMERA_FAILURE_DETECTED) ─▶ Coordinator
Coverage ─ REQUEST(TAKEOVER_REQUEST, hall) ─▶ standby camera
   ├─ ACCEPT  ─▶ INFORM(COVERAGE_TRANSFERRED) ─▶ Coordinator
   └─ REFUSE(reason) ─▶ REQUEST(RELY_ON_SENSORS) ─▶ Coordinator ─ ACCEPT (rule R9)
                         (coordinator unavailable ─▶ INFORM(ZONE_UNMONITORED) ─▶ Management)
camera heartbeats again ─▶ INFORM(CAMERA_RECOVERED) + REQUEST(RELEASE_REQUEST) to the backup
```

## Key parameters

| Parameter | Default | Owner |
|---|---|---|
| `PROTECTION_RADIUS` | 1.5 map units | Environment |
| `spawn_every` / `max_visitors` | 9 ticks / 7 visitors | Simulation |
| `dwell_threshold` | 3 ticks | Visitor Monitoring Agent |
| `suspicion` threshold (dashboard indicator) | 2 | Dashboard |
| `guards` | 2 | Security staff |
| `heartbeat_timeout` | 2 ticks | Coverage Management Agent |
| `retry_interval` | 5 ticks | Coverage Management Agent |

## Editing the code

Edit the notebook, then regenerate the package and run the tests:

```bash
python tools/export_notebook.py
pytest -q
```
