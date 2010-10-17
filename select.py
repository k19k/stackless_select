import stackless

class _alt:
    def __init__(self, chan, op, value, cb):
        self.ch = chan
        self.task = stackless.getcurrent()
        self.dir = op
        self.val = value
        self.cb = cb
        self.next = None
        self.prev = None

    def add(self):
        assert self.task == stackless.getcurrent()

        self.ch._insert(self)
        self.task._ops.append(self)

    def __remove(self):
        self.ch._remove(self)

    def __removeall(self):
        for s in self.task._ops:
            s.__remove()
        self.task._ops = []

    def __copy(self, other):
        if self.dir == 1:
            other.val = self.val
        else:
            self.val = other.val

    def __signal(self):
        self.task._signal.preference = -self.dir * self.ch.preference
        self.task._signal.send(self)

    def action(self):
        assert self.task == stackless.getcurrent()

        # Pick a ready task.
        other = self.ch.queue

        assert other.task != self.task

        # Reset state of all involved channels and resume our task.
        self.__copy(other)
        other.__removeall()
        other.__signal()

    def ready(self):
        return self.ch.balance * self.dir < 0

    def result(self):
        assert self.task == stackless.getcurrent()

        if self.dir == 1:
            if self.cb:
                return self.cb(self.ch, 1)
            return (self.ch, 1)
        if self.cb:
            return self.cb(self.ch, -1, self.val)
        return (self.ch, -1, self.val)

__nrand_next = 1
def nrand(n):
    global __nrand_next
    __nrand_next = __nrand_next * 1103515245 + 12345
    return (__nrand_next / 65536) % n

class tasklet(stackless.tasklet):
    def __init__(self, callback):
        self._ops = []
        self._signal = stackless.channel()

    def select(self, ops):
        choice = None
        nready = 0
        for s in ops:
            if s.ready():
                nready += 1
                if nrand(nready) == 0:
                    choice = s
        if choice:
            choice.action()
            return choice.result()
        for s in ops:
            s.add()
        s = self._signal.receive()
        return s.result()

class channel():
    def __init__(self):
        self.queue = None
        self.balance = 0
        self.preference = -1
        self.__tail = None

    def send(self, value):
        select([self.sends(value)])

    def receive(self):
        return select([self.receives()])[2]

    def sends(self, value, cb=None):
        return _alt(self, 1, value, cb)

    def receives(self, cb=None):
        return _alt(self, -1, None, cb)

    def _insert(self, op):
        if self.queue:
            op.prev = self.__tail
            self.__tail.next = op
        else:
            op.prev = None
            self.queue = op
        op.next = None
        self.__tail = op
        self.balance += op.dir

    def _remove(self, op):
        if op.next:
            op.next.prev = op.prev
        if op.prev:
            op.prev.next = op.next
        if op == self.queue:
            self.queue = op.next
        if op == self.__tail:
            self.__tail = op.prev
        self.balance -= op.dir

def select(ops):
    return stackless.getcurrent().select(ops)
