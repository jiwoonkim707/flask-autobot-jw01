import time

class Monitor:
    def __init__(self, client, engine):
        self.client = client
        self.engine = engine
        self.exit_flag = False

    def start(self):
        while not self.exit_flag:
            try:
                self.engine.monitor_positions()
            except Exception as e:
                print(f"[Monitor 오류] {e}")
            time.sleep(5)
