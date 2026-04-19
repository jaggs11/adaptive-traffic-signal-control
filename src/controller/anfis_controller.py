import joblib
import numpy as np

class ANFISTrafficController:
    """
    Practical approximation:
    - Trained model maps features -> optimal green duration
    - Features: [queue_ns, queue_ew, wait_ns, wait_ew, phase_is_ns]
    """
    def __init__(self, model_path="models/anfis_model.pkl", green_min=10, green_max=60):
        self.model = joblib.load(model_path)
        self.green_min = green_min
        self.green_max = green_max

    def next_green_duration(self, state):
        x = np.array([[
            state["queue_ns"], state["queue_ew"],
            state["wait_ns"], state["wait_ew"],
            1 if state["current_phase_dir"] == "NS" else 0
        ]])
        y = float(self.model.predict(x)[0])
        return float(np.clip(y, self.green_min, self.green_max))