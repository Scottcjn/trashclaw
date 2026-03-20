# Token-per-second Display - #64 (10 RTC)

class TokenStats:
    def __init__(self):
        self.tokens = 0
        self.start_time = 0
    
    def start(self):
        import time
        self.start_time = time.time()
    
    def update(self, tokens):
        self.tokens = tokens
    
    def get_tps(self):
        import time
        elapsed = time.time() - self.start_time
        tps = self.tokens / max(1, elapsed)
        return {'tokens': self.tokens, 'tps': tps}

if __name__ == '__main__':
    stats = TokenStats()
    stats.start()
    stats.update(100)
    print(stats.get_tps())
