import yaml
from src.sim.traci_runner import run_simulation

def load_config(path="config/settings.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    cfg = load_config()
    run_simulation(cfg)