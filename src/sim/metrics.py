import numpy as np

def summarize(step_records):
    waits = [r["total_wait"] for r in step_records]
    queues = [r["total_queue"] for r in step_records]
    throughput = step_records[-1]["arrived"] if step_records else 0

    return {
        "avg_total_wait": float(np.mean(waits)) if waits else 0.0,
        "avg_total_queue": float(np.mean(queues)) if queues else 0.0,
        "throughput": int(throughput)
    }