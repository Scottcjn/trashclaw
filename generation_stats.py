# Token/Second Display - Bounty #64
# Add generation stats display

import time

class GenerationStats:
    def __init__(self):
        self.start_time = None
        self.tokens = 0
    
    def start(self):
        self.start_time = time.time()
        self.tokens = 0
    
    def update(self, tokens):
        self.tokens = tokens
    
    def get_stats(self):
        elapsed = time.time() - self.start_time if self.start_time else 0
        tps = self.tokens / elapsed if elapsed > 0 else 0
        return {"tokens": self.tokens, "elapsed": f"{elapsed:.2f}s", "tokens_per_second": f"{tps:.1f}"}

if __name__ == "__main__":
    stats = GenerationStats()
    stats.start()
    stats.update(100)
    print(stats.get_stats())
