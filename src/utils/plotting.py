import matplotlib.pyplot as plt
import pandas as pd

def plot_step_log(csv_path="data/processed/step_log.csv"):
    df = pd.read_csv(csv_path)

    plt.figure(figsize=(10,5))
    plt.plot(df["step"], df["total_wait"], label="Total Wait")
    plt.plot(df["step"], df["total_queue"], label="Total Queue")
    plt.xlabel("Step")
    plt.ylabel("Value")
    plt.title("Traffic Metrics Over Time")
    plt.legend()
    plt.tight_layout()
    plt.show()