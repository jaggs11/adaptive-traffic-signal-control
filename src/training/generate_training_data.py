import os
import numpy as np
import pandas as pd

def main():
    """
    Synthetic training data generator (starter).
    Later you can replace this with simulation-collected optimal targets.
    """
    np.random.seed(42)
    n = 3000

    queue_ns = np.random.randint(0, 60, n)
    queue_ew = np.random.randint(0, 60, n)
    wait_ns = np.random.uniform(0, 120, n)
    wait_ew = np.random.uniform(0, 120, n)
    phase_is_ns = np.random.randint(0, 2, n)

    # heuristic target duration
    imbalance_q = np.where(phase_is_ns == 1, queue_ns - queue_ew, queue_ew - queue_ns)
    imbalance_w = np.where(phase_is_ns == 1, wait_ns - wait_ew, wait_ew - wait_ns)
    target = 30 + 0.4 * imbalance_q + 0.15 * imbalance_w
    target = np.clip(target, 10, 60)

    df = pd.DataFrame({
        "queue_ns": queue_ns,
        "queue_ew": queue_ew,
        "wait_ns": wait_ns,
        "wait_ew": wait_ew,
        "phase_is_ns": phase_is_ns,
        "target_green_duration": target
    })

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/training_samples.csv", index=False)
    print("Saved data/processed/training_samples.csv")

if __name__ == "__main__":
    main()