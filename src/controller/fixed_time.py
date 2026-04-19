class FixedTimeController:
    """
    Two-phase example:
    phase 0 -> NS green, EW red
    phase 2 -> EW green, NS red
    (SUMO TLS phase indices depend on your net; adjust accordingly)
    """
    def __init__(self, green_time=30):
        self.green_time = green_time

    def next_green_duration(self, state):
        return self.green_time