import numpy as np

def triangular(x, a, b, c):
    if x <= a or x >= c:
        return 0.0
    if a < x <= b:
        return (x - a) / (b - a + 1e-9)
    return (c - x) / (c - b + 1e-9)

class FuzzyTrafficController:
    """
    Inputs:
      - queue_ns, queue_ew (vehicles)
      - wait_ns, wait_ew (seconds, avg)
    Output:
      - extension time for current green (seconds)
    """
    def __init__(self, green_min=10, green_max=60):
        self.green_min = green_min
        self.green_max = green_max

    def fuzzify_queue(self, q):
        low = triangular(q, 0, 0, 10)
        med = triangular(q, 5, 15, 25)
        high = triangular(q, 20, 40, 60)
        return low, med, high

    def fuzzify_wait(self, w):
        low = triangular(w, 0, 0, 20)
        med = triangular(w, 10, 35, 60)
        high = triangular(w, 50, 90, 140)
        return low, med, high

    def infer_extension(self, queue_diff, wait_diff):
        # queue_diff = queue_current_green_dir - queue_other_dir
        # wait_diff  = wait_current_green_dir  - wait_other_dir

        q_low, q_med, q_high = self.fuzzify_queue(abs(queue_diff))
        w_low, w_med, w_high = self.fuzzify_wait(abs(wait_diff))

        # Rule strengths (simple but effective)
        # If current direction has much more queue/wait -> extend more
        if queue_diff >= 0 and wait_diff >= 0:
            strength_long = max(q_high, w_high)
            strength_med = max(q_med, w_med)
            strength_short = max(q_low, w_low) * 0.4
        else:
            strength_long = 0.2 * max(q_low, w_low)
            strength_med = 0.4 * max(q_med, w_med)
            strength_short = max(q_high, w_high)

        # Sugeno-style singleton consequents
        z_short, z_med, z_long = 0.2, 0.5, 0.9
        num = strength_short*z_short + strength_med*z_med + strength_long*z_long
        den = strength_short + strength_med + strength_long + 1e-9
        z = num / den

        duration = self.green_min + z * (self.green_max - self.green_min)
        return float(np.clip(duration, self.green_min, self.green_max))

    def next_green_duration(self, state):
        # state must include current_phase_dir in {"NS","EW"}
        q_ns, q_ew = state["queue_ns"], state["queue_ew"]
        w_ns, w_ew = state["wait_ns"], state["wait_ew"]

        if state["current_phase_dir"] == "NS":
            return self.infer_extension(q_ns - q_ew, w_ns - w_ew)
        return self.infer_extension(q_ew - q_ns, w_ew - w_ns)