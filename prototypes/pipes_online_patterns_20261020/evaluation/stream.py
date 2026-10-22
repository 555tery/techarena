"""Causal event bookkeeping reused from the frozen prior input generator."""
import collections
import heapq

class Stream:
    def __init__(self, rng):
        self.rng = rng
        self.commands, self.ids = [], []
        self.live, self.positions = {}, {}
        self.order = collections.deque()
        self.stack, self.deadlines = [], []
        self.next_pid = 1
        self.volume = self.peak = self.peak_count = 0
        self.anchors = set()
        self.run_size = rng.randint(7, 34)
        self.run_period = rng.randint(259, 521)
        self.batch_remaining = 0

    def emit(self, command, life=1000000):
        if command > 0:
            assert command <= 40
            pid = self.next_pid
            self.next_pid += 1
            self.live[pid] = command
            self.positions[pid] = len(self.ids)
            self.ids.append(pid)
            self.order.append(pid)
            self.stack.append(pid)
            heapq.heappush(self.deadlines, (len(self.commands) + life, pid))
            self.volume += command
        else:
            assert command < 0 and -command in self.live
            pid = -command
            self.volume -= self.live.pop(pid)
            idx = self.positions.pop(pid)
            last = self.ids.pop()
            if idx < len(self.ids):
                self.ids[idx] = last
                self.positions[last] = idx
        self.commands.append(command)
        self.peak = max(self.peak, self.volume)
        self.peak_count = max(self.peak_count, len(self.live))

    def choose(self, policy="random", protect=False):
        if len(self.live) <= 1:
            return None
        if policy in ("oldest", "newest") and not protect:
            seq = self.order if policy == "oldest" else self.stack
            while seq and (seq[0] if policy == "oldest" else seq[-1]) not in self.live:
                seq.popleft() if policy == "oldest" else seq.pop()
            return seq[0] if policy == "oldest" else seq[-1]
        candidates = [self.ids[self.rng.randrange(len(self.ids))] for _ in range(24)]
        if protect:
            candidates = [p for p in candidates if p not in self.anchors]
            if not candidates:
                return None
        if policy == "young": return max(candidates)
        if policy == "old": return min(candidates)
        return candidates[0]

    def due(self):
        while self.deadlines and self.deadlines[0][1] not in self.live:
            heapq.heappop(self.deadlines)
        if len(self.live) > 1 and self.deadlines and self.deadlines[0][0] <= len(self.commands):
            return self.deadlines[0][1]
        return None

