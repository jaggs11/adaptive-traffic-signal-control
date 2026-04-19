import os
import csv
import traci
from sumolib import checkBinary

from src.controller.fixed_time import FixedTimeController
from src.controller.fuzzy_controller import FuzzyTrafficController
from src.controller.anfis_controller import ANFISTrafficController
from src.sim.metrics import summarize


def build_controller(cfg):
    mode = cfg["controller"]["mode"]
    sim_cfg = cfg["simulation"]

    if mode == "fixed":
        return FixedTimeController(green_time=30)
    if mode == "fuzzy":
        return FuzzyTrafficController(sim_cfg["green_min"], sim_cfg["green_max"])
    if mode == "anfis":
        return ANFISTrafficController(
            "models/anfis_model.pkl",
            sim_cfg["green_min"],
            sim_cfg["green_max"],
        )
    raise ValueError(f"Unknown controller mode: {mode}")


def get_edge_stats(edges):
    q = 0
    waits = []
    edge_ids = set(traci.edge.getIDList())

    for e in edges:
        if e not in edge_ids:
            continue
        q += traci.edge.getLastStepHaltingNumber(e)
        vids = traci.edge.getLastStepVehicleIDs(e)
        for v in vids:
            waits.append(traci.vehicle.getWaitingTime(v))

    avg_wait = (sum(waits) / len(waits)) if waits else 0.0
    return q, avg_wait


def phase_has_green_for_linkstate(link_state: str, link_index: int) -> bool:
    """Check if a TLS phase state gives green to a link index."""
    if link_index < 0 or link_index >= len(link_state):
        return False
    return link_state[link_index] in ("g", "G")


def detect_ns_ew_green_phases(tls_id, ns_edges, ew_edges):
    """
    Try to auto-detect which phase index is NS-green and EW-green.
    Uses controlled links and phase state strings from current TLS program.
    Fallback to (0, 2) if detection fails.
    """
    logic = traci.trafficlight.getAllProgramLogics(tls_id)[0]
    phases = logic.phases
    controlled_links = traci.trafficlight.getControlledLinks(tls_id)
    # controlled_links: tuple where each index corresponds to state char in phase.state
    # each item -> list of tuples (inLane, outLane, viaLane)
    ns_link_indices = set()
    ew_link_indices = set()

    def lane_to_edge(lane_id):
        # lane like "A1B1_0" => edge "A1B1"
        return lane_id.rsplit("_", 1)[0]

    for idx, link_group in enumerate(controlled_links):
        for link in link_group:
            in_lane = link[0]
            in_edge = lane_to_edge(in_lane)
            if in_edge in ns_edges:
                ns_link_indices.add(idx)
            if in_edge in ew_edges:
                ew_link_indices.add(idx)

    best_ns = None
    best_ew = None
    best_ns_score = -1
    best_ew_score = -1

    for i, ph in enumerate(phases):
        s = ph.state
        ns_score = sum(1 for li in ns_link_indices if phase_has_green_for_linkstate(s, li))
        ew_score = sum(1 for li in ew_link_indices if phase_has_green_for_linkstate(s, li))

        if ns_score > best_ns_score:
            best_ns_score = ns_score
            best_ns = i
        if ew_score > best_ew_score:
            best_ew_score = ew_score
            best_ew = i

    if best_ns is None or best_ew is None or best_ns == best_ew:
        return 0, 2  # fallback for common 4-phase layouts
    return best_ns, best_ew


def run_simulation(cfg):
    sim_cfg = cfg["simulation"]
    steps = sim_cfg["steps"]
    warmup_steps = sim_cfg.get("warmup_steps", 0)
    decision_interval = sim_cfg["decision_interval"]
    yellow_time = sim_cfg.get("yellow_time", 3)
    all_red_time = sim_cfg.get("all_red_time", 1)

    sumo_binary = checkBinary("sumo")
    sumo_cfg = "sumo/sim.sumocfg"
    traci.start([sumo_binary, "-c", sumo_cfg])

    controller = build_controller(cfg)

    tls_ids = list(traci.trafficlight.getIDList())
    print("Detected TLS IDs:", tls_ids)
    if not tls_ids:
        traci.close()
        raise RuntimeError(
            "No traffic lights found in current SUMO network. "
            "Regenerate net with TLS and ensure routes go through that junction."
        )

    cfg_tls = cfg["junction"]["tls_id"]
    tls_id = tls_ids[0] if cfg_tls == "AUTO" else cfg_tls
    if tls_id not in tls_ids:
        traci.close()
        raise RuntimeError(f"Configured tls_id '{tls_id}' not in detected IDs: {tls_ids}")

    print("Using TLS:", tls_id)

    # Approaches for center junction B1 in your grid
    ns_edges = ["A1B1", "C1B1"]  # north-south incoming to B1
    ew_edges = ["B0B1", "B2B1"]  # west-east incoming to B1

    ns_green_phase, ew_green_phase = detect_ns_ew_green_phases(tls_id, ns_edges, ew_edges)
    print(f"Detected phase mapping: NS={ns_green_phase}, EW={ew_green_phase}")

    # Start with NS
    current_dir = "NS"
    traci.trafficlight.setPhase(tls_id, ns_green_phase)

    next_decision_step = warmup_steps
    hold_until_step = warmup_steps
    arrived = 0
    records = []
    current_green_dur = 0

    for step in range(steps):
        traci.simulationStep()
        arrived += traci.simulation.getArrivedNumber()

        q_ns, w_ns = get_edge_stats(ns_edges)
        q_ew, w_ew = get_edge_stats(ew_edges)

        # Decide only after warmup and when current hold ends
        if step >= next_decision_step and step >= hold_until_step and (step % decision_interval == 0):
            state = {
                "queue_ns": q_ns,
                "queue_ew": q_ew,
                "wait_ns": w_ns,
                "wait_ew": w_ew,
                "current_phase_dir": current_dir,
            }

            green_dur = int(controller.next_green_duration(state))
            green_dur = max(sim_cfg["green_min"], min(sim_cfg["green_max"], green_dur))
            current_green_dur = green_dur

            # Switch direction
            target_dir = "EW" if current_dir == "NS" else "NS"
            target_phase = ew_green_phase if target_dir == "EW" else ns_green_phase

            # Transition safety timing (approx): keep current phase for yellow+all_red budget
            transition_budget = yellow_time + all_red_time
            if transition_budget > 0:
                # Let SUMO internal phase logic progress for transition budget steps
                # (simple approximation if custom phase indices are not explicit yellow/all-red)
                for _ in range(transition_budget):
                    if step + 1 >= steps:
                        break
                    traci.simulationStep()

            traci.trafficlight.setPhase(tls_id, target_phase)
            current_dir = target_dir

            hold_until_step = step + transition_budget + green_dur
            next_decision_step = step + decision_interval

        records.append(
            {
                "step": step,
                "queue_ns": q_ns,
                "queue_ew": q_ew,
                "wait_ns": w_ns,
                "wait_ew": w_ew,
                "total_queue": q_ns + q_ew,
                "total_wait": w_ns + w_ew,
                "arrived": arrived,
                "active_dir": current_dir,
                "green_dur_last": current_green_dur,
            }
        )

    traci.close()

    os.makedirs("data/processed", exist_ok=True)

    if records:
        with open(cfg["output"]["step_csv"], "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)

        summary = summarize(records)
        with open(cfg["output"]["metrics_csv"], "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=summary.keys())
            writer.writeheader()
            writer.writerow(summary)

        print("Run Summary:", summary)
    else:
        print("No simulation records generated.")