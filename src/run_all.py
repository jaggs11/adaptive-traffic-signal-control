import os
import shutil
import yaml
import pandas as pd

from src.sim.traci_runner import run_simulation


CONFIG_PATH = "config/settings.yaml"
PROCESSED_DIR = "data/processed"


def load_cfg():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_cfg(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


def run_mode(mode: str):
    cfg = load_cfg()
    cfg["controller"]["mode"] = mode
    save_cfg(cfg)

    print(f"\n=== Running mode: {mode} ===")
    run_simulation(cfg)

    # Copy outputs to mode-specific files
    step_src = cfg["output"]["step_csv"]
    run_src = cfg["output"]["metrics_csv"]

    step_dst = os.path.join(PROCESSED_DIR, f"step_log_{mode}.csv")
    run_dst = os.path.join(PROCESSED_DIR, f"run_metrics_{mode}.csv")

    shutil.copyfile(step_src, step_dst)
    shutil.copyfile(run_src, run_dst)

    print(f"Saved: {step_dst}")
    print(f"Saved: {run_dst}")


def build_comparison():
    rows = []
    for mode in ["fixed", "fuzzy", "anfis"]:
        path = os.path.join(PROCESSED_DIR, f"run_metrics_{mode}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        if df.empty:
            continue
        r = df.iloc[0].to_dict()
        r["mode"] = mode
        rows.append(r)

    if rows:
        cmp_df = pd.DataFrame(rows)[["mode", "avg_total_wait", "avg_total_queue", "throughput"]]
        cmp_path = os.path.join(PROCESSED_DIR, "comparison.csv")
        cmp_df.to_csv(cmp_path, index=False)
        print(f"Saved: {cmp_path}")
        print("\nComparison:\n", cmp_df)
    else:
        print("No run metrics found to build comparison.csv")


if __name__ == "__main__":
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    original_cfg = load_cfg()
    original_mode = original_cfg["controller"]["mode"]

    try:
        for m in ["fixed", "fuzzy", "anfis"]:
            run_mode(m)
        build_comparison()
    finally:
        # restore user's original mode
        cfg = load_cfg()
        cfg["controller"]["mode"] = original_mode
        save_cfg(cfg)
        print(f"\nRestored controller.mode to: {original_mode}")