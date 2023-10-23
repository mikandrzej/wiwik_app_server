class IrvineMeasure:
    def __init__(self, irvine_id: str, meas_type: str, value, timestamp):
        self.irvine_id = irvine_id
        self.meas_type = meas_type
        self.value = value
        self.timestamp = timestamp


class IrvineData:
    def __init__(self):
        self.measures = []

    def add_measure(self, measure: IrvineMeasure):
        self.measures.append(measure)
