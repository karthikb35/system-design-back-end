#!/usr/bin/env python3
"""
enhance_interview_questions.py
Appends scenario-based code questions with solutions to every
interview_questions.ipynb notebook.
Run: python enhance_interview_questions.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).parent


def uid():
    return uuid.uuid4().hex[:12]


def mk_md(text):
    return {"cell_type": "markdown", "id": uid(), "metadata": {}, "source": [text]}


def mk_py(text):
    return {"cell_type": "code", "id": uid(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": [text]}


def append_cells(rel_path, cells):
    path = ROOT / rel_path
    if not path.exists():
        print(f"  SKIP: {rel_path}")
        return
    nb = json.loads(path.read_text(encoding="utf-8"))
    nb["cells"].extend([dict(c, id=uid()) for c in cells])
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  + {path.parent.name}/{path.name}  ({len(nb['cells'])} cells, {path.stat().st_size//1024}KB)")


# ─── Python Foundations ──────────────────────────────────────────────────────

PY = [
    mk_md("---\n## Scenario-Based Code Questions -- Python Foundations"),

    mk_md(
        "### Scenario 1 -- Retry Decorator with Exponential Backoff + Jitter\n\n"
        "**Context:** BuildFast's GitHub API client gets 429 rate-limit errors.\n"
        "Implement `@retry(times, exceptions, base_delay, cap)` with exponential "
        "backoff + random jitter to prevent thundering-herd.\n\n"
        "**Requirements:**\n"
        "- Delay = `min(base * 2^attempt + random(0, 0.5), cap)` seconds\n"
        "- Raises the LAST exception if all retries fail\n"
        "- Preserves `__name__` / `__doc__` via `functools.wraps`\n\n"
        "**Try it, then scroll to the solution.**"
    ),

    mk_py(
        "# -- ATTEMPT (scaffold) --\n"
        "import functools, time, random\n\n"
        "def retry(times=3, exceptions=(Exception,), base_delay=1.0, cap=60.0):\n"
        "    # YOUR CODE HERE\n"
        "    pass\n\n"
        "# Quick test\n"
        "call_count = 0\n\n"
        "@retry(times=3, exceptions=(ValueError,), base_delay=0.001)\n"
        "def flaky():\n"
        "    global call_count; call_count += 1\n"
        "    if call_count < 3: raise ValueError('transient')\n"
        "    return 'ok'\n\n"
        "print(flaky(), call_count)  # should print: ok  3"
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import functools, time, random\n\n"
        "def retry(times=3, exceptions=(Exception,), base_delay=1.0, cap=60.0):\n"
        "    def decorator(fn):\n"
        "        @functools.wraps(fn)\n"
        "        def wrapper(*args, **kwargs):\n"
        "            last = None\n"
        "            for attempt in range(times):\n"
        "                try:\n"
        "                    return fn(*args, **kwargs)\n"
        "                except exceptions as e:\n"
        "                    last = e\n"
        "                    if attempt < times - 1:\n"
        "                        delay = min(base_delay * (2**attempt) + random.uniform(0, 0.5), cap)\n"
        "                        time.sleep(delay)\n"
        "            raise last\n"
        "        return wrapper\n"
        "    return decorator\n\n"
        "# -- Verify --\n"
        "call_count = 0\n\n"
        "@retry(times=3, exceptions=(ValueError,), base_delay=0.001)\n"
        "def flaky():\n"
        "    global call_count; call_count += 1\n"
        "    if call_count < 3: raise ValueError('transient')\n"
        "    return 'ok'\n\n"
        "assert flaky() == 'ok' and call_count == 3\n"
        "assert flaky.__name__ == 'flaky'\n"
        "print(f'Result: ok after {call_count} attempts, __name__ preserved: {flaky.__name__!r}')"
    ),

    mk_md(
        "**Analysis:** 3-level nesting (factory -> decorator -> wrapper). "
        "`min(..., cap)` prevents unbounded waits. Jitter desynchronises concurrent callers. "
        "`functools.wraps` preserves identity for FastAPI/Pydantic route introspection."
    ),

    mk_md(
        "### Scenario 2 -- Lazy CSV Pipeline (Generator Chain)\n\n"
        "**Context:** BuildFast exports 10M+ build records. Loading into a list "
        "exhausts 16GB RAM. Stream one row at a time using generators.\n\n"
        "**Requirements:** `read_csv` -> `filter_rows` -> `transform` -> `to_csv_lines` "
        "-- each step is lazy. Peak memory = O(1)."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import csv, io, sys\n\n"
        "def read_csv(fileobj):\n"
        "    for row in csv.DictReader(fileobj): yield dict(row)\n\n"
        "def filter_rows(rows, key, value):\n"
        "    for row in rows:\n"
        "        if row.get(key) == value: yield row\n\n"
        "def transform(rows, fn):\n"
        "    for row in rows: yield fn(row)\n\n"
        "def to_csv_lines(rows):\n"
        "    for row in rows: yield ','.join(str(v) for v in row.values())\n\n"
        "# -- Test --\n"
        "data = 'id,status,dur_ms\\n1,failed,8900\\n2,success,1200\\n3,failed,12000'\n"
        "pipeline = to_csv_lines(\n"
        "    transform(\n"
        "        filter_rows(read_csv(io.StringIO(data)), 'status', 'failed'),\n"
        "        lambda r: {**r, 'dur_s': float(r['dur_ms'])/1000}\n"
        "    )\n"
        ")\n"
        "for line in pipeline: print(line)\n"
        "gen = to_csv_lines(filter_rows(read_csv(io.StringIO(data)), 'status', 'failed'))\n"
        "print(f'Generator size: {sys.getsizeof(gen)} bytes -- constant regardless of file size')"
    ),

    mk_md(
        "### Scenario 3 -- Descriptor-Based Field Validator\n\n"
        "**Context:** BuildFast pipeline config fields need type + range validation "
        "on EVERY assignment (not just `__init__`). Build a reusable descriptor.\n\n"
        "```python\n"
        "class PipelineConfig:\n"
        "    max_parallel = TypedField(int, min_val=1, max_val=50)\n"
        "    name         = TypedField(str)\n"
        "cfg.max_parallel = -1  # ValueError!\n"
        "```"
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "class TypedField:\n"
        "    def __init__(self, ftype, min_val=None, max_val=None):\n"
        "        self.ftype, self.min_val, self.max_val = ftype, min_val, max_val\n\n"
        "    def __set_name__(self, owner, name): self._attr = f'_{name}'\n\n"
        "    def __get__(self, obj, t=None): return self if obj is None else getattr(obj, self._attr, None)\n\n"
        "    def __set__(self, obj, value):\n"
        "        if not isinstance(value, self.ftype):\n"
        "            raise TypeError(f'{self._attr[1:]}: expected {self.ftype.__name__}, got {type(value).__name__}')\n"
        "        if self.min_val is not None and value < self.min_val:\n"
        "            raise ValueError(f'{self._attr[1:]} >= {self.min_val} required, got {value}')\n"
        "        if self.max_val is not None and value > self.max_val:\n"
        "            raise ValueError(f'{self._attr[1:]} <= {self.max_val} required, got {value}')\n"
        "        setattr(obj, self._attr, value)\n\n"
        "class PipelineConfig:\n"
        "    max_parallel    = TypedField(int, min_val=1, max_val=50)\n"
        "    timeout_minutes = TypedField(int, min_val=1, max_val=1440)\n"
        "    name            = TypedField(str)\n\n"
        "cfg = PipelineConfig()\n"
        "cfg.name = 'frontend-ci'; cfg.max_parallel = 4\n"
        "for bad, exc in [(-1, ValueError), (51, ValueError), ('5', TypeError)]:\n"
        "    try: cfg.max_parallel = bad\n"
        "    except (ValueError, TypeError) as e: print(f'  Rejected {bad!r}: {e}')\n"
        "print('Descriptor validates on every assignment (not just __init__) |/')"
    ),

    mk_md(
        "### Scenario 4 -- Plugin Registry via __init_subclass__\n\n"
        "**Context:** BuildFast report exporters self-register by subclassing `Exporter`. "
        "No manual registry call needed.\n\n"
        "```python\n"
        "class JsonExporter(Exporter, fmt='json'):\n"
        "    def export(self, data): return json.dumps(data)\n"
        "Exporter.create('json').export({'a': 1})  # works immediately\n"
        "```"
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import json as _json\n"
        "from typing import ClassVar\n\n"
        "class Exporter:\n"
        "    _registry: ClassVar[dict] = {}\n\n"
        "    def __init_subclass__(cls, fmt: str = '', **kwargs):\n"
        "        super().__init_subclass__(**kwargs)\n"
        "        Exporter._registry[fmt or cls.__name__.lower()] = cls\n\n"
        "    @classmethod\n"
        "    def create(cls, fmt: str):\n"
        "        if fmt not in cls._registry:\n"
        "            raise KeyError(f'Unknown format {fmt!r}. Available: {list(cls._registry)}')\n"
        "        return cls._registry[fmt]()\n\n"
        "    def export(self, data) -> str: raise NotImplementedError\n\n"
        "class JsonExporter(Exporter, fmt='json'):\n"
        "    def export(self, data) -> str: return _json.dumps(data)\n\n"
        "class CsvExporter(Exporter, fmt='csv'):\n"
        "    def export(self, data) -> str: return ','.join(str(v) for v in data)\n\n"
        "print('Registry:', list(Exporter._registry))\n"
        "print(Exporter.create('json').export({'build': 'success'}))\n"
        "print(Exporter.create('csv').export([1, 2, 3]))\n"
        "try: Exporter.create('xml')\n"
        "except KeyError as e: print(f'Unknown: {e}')"
    ),
]

# ─── DSA ─────────────────────────────────────────────────────────────────────

DSA = [
    mk_md("---\n## Scenario-Based Code Questions -- DSA"),

    mk_md(
        "### Scenario 1 -- LRU Cache (O(1) get and put)\n\n"
        "**Context:** ShopFlow caches rendered product HTML. On capacity, evict "
        "least-recently-used. Implement with O(1) for both operations using a "
        "doubly-linked list + hash map. **Do NOT use OrderedDict.**\n\n"
        "```\n"
        "cache = LRUCache(2)\n"
        "cache.put(1, 'a'); cache.put(2, 'b')\n"
        "cache.get(1)        # 'a' -- now MRU\n"
        "cache.put(3, 'c')   # evicts key 2\n"
        "cache.get(2)        # -1 (evicted)\n"
        "```"
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "class LRUCache:\n"
        "    class Node:\n"
        "        __slots__ = ('key', 'val', 'prev', 'next')\n"
        "        def __init__(self, key=0, val=0):\n"
        "            self.key, self.val, self.prev, self.next = key, val, None, None\n\n"
        "    def __init__(self, capacity):\n"
        "        self.cap, self.map = capacity, {}\n"
        "        self.head, self.tail = self.Node(), self.Node()\n"
        "        self.head.next, self.tail.prev = self.tail, self.head\n\n"
        "    def _remove(self, n): n.prev.next, n.next.prev = n.next, n.prev\n\n"
        "    def _push_front(self, n):\n"
        "        n.prev, n.next = self.head, self.head.next\n"
        "        self.head.next.prev = n; self.head.next = n\n\n"
        "    def get(self, key):\n"
        "        if key not in self.map: return -1\n"
        "        n = self.map[key]; self._remove(n); self._push_front(n)\n"
        "        return n.val\n\n"
        "    def put(self, key, val):\n"
        "        if key in self.map: self._remove(self.map[key])\n"
        "        n = self.Node(key, val); self.map[key] = n; self._push_front(n)\n"
        "        if len(self.map) > self.cap:\n"
        "            lru = self.tail.prev; self._remove(lru); del self.map[lru.key]\n\n"
        "cache = LRUCache(2)\n"
        "cache.put(1, 'product_a'); cache.put(2, 'product_b')\n"
        "assert cache.get(1) == 'product_a'\n"
        "cache.put(3, 'product_c')\n"
        "assert cache.get(2) == -1\n"
        "assert cache.get(3) == 'product_c'\n"
        "print('LRU Cache: all assertions passed |/')"
    ),

    mk_md(
        "### Scenario 2 -- Sliding Window Rate Limiter\n\n"
        "**Context:** BuildFast limits each user to N requests per T-second sliding window. "
        "Unlike fixed windows, a sliding window counts requests in the ACTUAL last T seconds.\n\n"
        "```\n"
        "rl = SlidingWindowRateLimiter(3, 60)\n"
        "rl.allow('u1', 0)   # True\n"
        "rl.allow('u1', 65)  # True (t=0 expired)\n"
        "```"
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "from collections import defaultdict, deque\n\n"
        "class SlidingWindowRateLimiter:\n"
        "    def __init__(self, max_requests, window_seconds):\n"
        "        self.max, self.window = max_requests, window_seconds\n"
        "        self._log: dict = defaultdict(deque)\n\n"
        "    def allow(self, user_id: str, timestamp: float) -> bool:\n"
        "        dq = self._log[user_id]\n"
        "        cutoff = timestamp - self.window\n"
        "        while dq and dq[0] <= cutoff: dq.popleft()\n"
        "        if len(dq) < self.max:\n"
        "            dq.append(timestamp); return True\n"
        "        return False\n\n"
        "rl = SlidingWindowRateLimiter(3, 60)\n"
        "results = [rl.allow('u1', t) for t in [0, 20, 40, 50, 65]]\n"
        "print('allow() results:', results)\n"
        "assert results == [True, True, True, False, True]\n"
        "print('Sliding window rate limiter correct |/')"
    ),

    mk_md(
        "### Scenario 3 -- Pipeline Topological Sort + Cycle Detection\n\n"
        "**Context:** BuildFast CI/CD jobs have dependencies. Detect circular "
        "dependencies and return valid execution order. Use Kahn's BFS (O(V+E))."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "from collections import defaultdict, deque\n\n"
        "def validate_pipeline(jobs: dict):\n"
        "    in_deg = {j: 0 for j in jobs}\n"
        "    for job, deps in jobs.items():\n"
        "        for dep in deps:\n"
        "            in_deg[job] += 1\n"
        "            if dep not in in_deg: in_deg[dep] = 0\n"
        "    queue = deque(j for j, d in in_deg.items() if d == 0)\n"
        "    order = []\n"
        "    while queue:\n"
        "        job = queue.popleft(); order.append(job)\n"
        "        for nj, deps in jobs.items():\n"
        "            if job in deps:\n"
        "                in_deg[nj] -= 1\n"
        "                if in_deg[nj] == 0: queue.append(nj)\n"
        "    return order if len(order) == len(in_deg) else None\n\n"
        "jobs = {'checkout':[],'install':['checkout'],'test':['install'],'build':['test'],'deploy':['build']}\n"
        "print('Valid order:', validate_pipeline(jobs))\n"
        "cyclic = {'a':['c'],'b':['a'],'c':['b']}\n"
        "print('Cyclic pipeline:', validate_pipeline(cyclic))  # None"
    ),

    mk_md(
        "### Scenario 4 -- Consistent Hashing Ring\n\n"
        "**Context:** ShopFlow distributes product cache across 3 nodes. When a node "
        "is removed, only ~1/3 of keys should be remapped (not all)."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import hashlib, bisect\n\n"
        "class ConsistentHashRing:\n"
        "    def __init__(self, replicas=100):\n"
        "        self.replicas, self._ring, self._nodes = replicas, [], {}\n\n"
        "    def _hash(self, key): return int(hashlib.md5(key.encode()).hexdigest(), 16)\n\n"
        "    def add_node(self, node):\n"
        "        for i in range(self.replicas):\n"
        "            h = self._hash(f'{node}#{i}')\n"
        "            self._nodes[h] = node; bisect.insort(self._ring, h)\n\n"
        "    def remove_node(self, node):\n"
        "        for i in range(self.replicas):\n"
        "            h = self._hash(f'{node}#{i}')\n"
        "            del self._nodes[h]; self._ring.pop(bisect.bisect_left(self._ring, h))\n\n"
        "    def get_node(self, key):\n"
        "        if not self._ring: return None\n"
        "        idx = bisect.bisect_right(self._ring, self._hash(key)) % len(self._ring)\n"
        "        return self._nodes[self._ring[idx]]\n\n"
        "ring = ConsistentHashRing(50)\n"
        "for n in ['cache-1','cache-2','cache-3']: ring.add_node(n)\n"
        "keys = [f'user:{i}' for i in range(1000)]\n"
        "before = {k: ring.get_node(k) for k in keys}\n"
        "ring.remove_node('cache-2')\n"
        "after = {k: ring.get_node(k) for k in keys}\n"
        "remapped = sum(1 for k in keys if before[k] != after[k])\n"
        "print(f'Remapped: {remapped}/1000 ({remapped/10:.1f}%) -- expect ~33%')"
    ),
]

# ─── System Design ─────────────────────────────────────────────────────────

SD = [
    mk_md("---\n## Scenario-Based Code Questions -- System Design"),

    mk_md(
        "### Scenario 1 -- Token Bucket Rate Limiter\n\n"
        "**Context:** ShopFlow's API gateway rate-limits to `max_tokens` requests/sec "
        "using token bucket (allows short bursts).\n\n"
        "**Critical:** Use `time.monotonic()` NOT `time.time()` -- immune to NTP jumps!"
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import time, threading\n"
        "from collections import defaultdict\n\n"
        "class TokenBucket:\n"
        "    def __init__(self, max_tokens: float, refill_rate: float):\n"
        "        self.max, self.rate = max_tokens, refill_rate\n"
        "        self._tokens: dict = defaultdict(lambda: max_tokens)\n"
        "        self._last:   dict = defaultdict(time.monotonic)\n"
        "        self._lock   = threading.Lock()\n\n"
        "    def consume(self, user_id: str, n: float = 1, now: float | None = None) -> bool:\n"
        "        now = now or time.monotonic()\n"
        "        with self._lock:\n"
        "            elapsed = now - self._last[user_id]\n"
        "            self._tokens[user_id] = min(self.max, self._tokens[user_id] + elapsed * self.rate)\n"
        "            self._last[user_id]   = now\n"
        "            if self._tokens[user_id] >= n:\n"
        "                self._tokens[user_id] -= n; return True\n"
        "            return False\n\n"
        "tb = TokenBucket(max_tokens=10, refill_rate=5)\n"
        "assert tb.consume('u1', 5, now=0.0)\n"
        "assert not tb.consume('u1', 6, now=0.0)  # only 5 left\n"
        "assert tb.consume('u1', 10, now=1.0)      # +5 refilled\n"
        "print('Token bucket assertions passed |/')"
    ),

    mk_md(
        "### Scenario 2 -- Bloom Filter\n\n"
        "**Context:** BuildFast deduplicates build events before querying the DB. "
        "False positives OK (will re-check DB), false negatives NOT OK."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import math, hashlib\n\n"
        "class BloomFilter:\n"
        "    def __init__(self, capacity: int, error_rate: float = 0.01):\n"
        "        self.size   = int(-capacity * math.log(error_rate) / (math.log(2)**2))\n"
        "        self.hashes = int(self.size / capacity * math.log(2))\n"
        "        self._bits  = bytearray(self.size)\n\n"
        "    def _pos(self, item):\n"
        "        return [int(hashlib.sha256(f'{i}:{item}'.encode()).hexdigest(), 16) % self.size\n"
        "                for i in range(self.hashes)]\n\n"
        "    def add(self, item: str):\n"
        "        for p in self._pos(item): self._bits[p] = 1\n\n"
        "    def might_contain(self, item: str) -> bool:\n"
        "        return all(self._bits[p] for p in self._pos(item))\n\n"
        "bf = BloomFilter(capacity=10_000, error_rate=0.01)\n"
        "for i in range(1000): bf.add(f'event_{i}')\n"
        "assert bf.might_contain('event_0') and bf.might_contain('event_999')\n"
        "assert not bf.might_contain('event_99999')\n"
        "fps = sum(1 for i in range(10000, 20000) if bf.might_contain(f'event_{i}'))\n"
        "print(f'False positive rate: {fps/10000:.2%} (target: ~1%)')"
    ),
]

# ─── FastAPI ─────────────────────────────────────────────────────────────────

FA = [
    mk_md("---\n## Scenario-Based Code Questions -- FastAPI Advanced"),

    mk_md(
        "### Scenario 1 -- ASGI Request ID Middleware\n\n"
        "**Context:** Every BuildFast request needs `X-Request-ID` injected "
        "(or reuse the caller's ID) and returned in the response.\n\n"
        "**Requirements:** Pure ASGI middleware -- no FastAPI import needed."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import uuid\n"
        "from fastapi import FastAPI, Request\n"
        "from fastapi.testclient import TestClient\n"
        "from starlette.datastructures import MutableHeaders\n\n"
        "class RequestIDMiddleware:\n"
        "    def __init__(self, app): self.app = app\n\n"
        "    async def __call__(self, scope, receive, send):\n"
        "        if scope['type'] not in ('http', 'websocket'):\n"
        "            await self.app(scope, receive, send); return\n"
        "        headers = dict(scope.get('headers', []))\n"
        "        req_id  = (headers.get(b'x-request-id') or str(uuid.uuid4()).encode()).decode()\n"
        "        scope.setdefault('state', {})['request_id'] = req_id\n\n"
        "        async def inject(message):\n"
        "            if message['type'] == 'http.response.start':\n"
        "                MutableHeaders(scope=message).append('x-request-id', req_id)\n"
        "            await send(message)\n\n"
        "        await self.app(scope, receive, inject)\n\n"
        "app = FastAPI()\n"
        "app.add_middleware(RequestIDMiddleware)\n\n"
        "@app.get('/ping')\n"
        "def ping(request: Request): return {'request_id': request.state.request_id}\n\n"
        "client = TestClient(app)\n"
        "r = client.get('/ping')\n"
        "assert 'x-request-id' in r.headers\n"
        "assert r.json()['request_id'] == r.headers['x-request-id']\n"
        "print('Auto-generated ID:', r.headers['x-request-id'])\n\n"
        "r2 = client.get('/ping', headers={'X-Request-ID': 'my-trace-123'})\n"
        "assert r2.headers['x-request-id'] == 'my-trace-123'\n"
        "print('Caller-provided ID preserved:', r2.headers['x-request-id'])"
    ),
]

# ─── Concurrency ─────────────────────────────────────────────────────────────

CONC = [
    mk_md("---\n## Scenario-Based Code Questions -- Concurrency"),

    mk_md(
        "### Scenario 1 -- Async Connection Pool\n\n"
        "**Context:** BuildFast async workers need to reuse N HTTP connections "
        "to GitHub instead of creating a new TLS connection per request (~200ms overhead).\n\n"
        "**Key:** Use `asyncio.Queue` (not `threading.Queue`) -- it suspends coroutines, "
        "not threads."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import asyncio\n"
        "from contextlib import asynccontextmanager\n\n"
        "class FakeConn:\n"
        "    _n = 0\n"
        "    def __init__(self): FakeConn._n += 1; self.id = FakeConn._n\n"
        "    async def get(self, url): await asyncio.sleep(0.001); return {'url': url, 'conn': self.id}\n\n"
        "class AsyncConnectionPool:\n"
        "    def __init__(self, size: int):\n"
        "        self._size, self._q = size, None\n\n"
        "    async def setup(self):\n"
        "        self._q = asyncio.Queue(maxsize=self._size)\n"
        "        for _ in range(self._size): await self._q.put(FakeConn())\n\n"
        "    @asynccontextmanager\n"
        "    async def acquire(self):\n"
        "        conn = await self._q.get()\n"
        "        try:   yield conn\n"
        "        finally: await self._q.put(conn)\n\n"
        "async def demo():\n"
        "    pool = AsyncConnectionPool(3)\n"
        "    await pool.setup()\n"
        "    async def fetch(i):\n"
        "        async with pool.acquire() as conn: return await conn.get(f'https://api/{i}')\n"
        "    results = await asyncio.gather(*[fetch(i) for i in range(10)])\n"
        "    ids = {r['conn'] for r in results}\n"
        "    print(f'10 requests via {len(ids)} pooled connections: {sorted(ids)}')\n"
        "    assert len(ids) <= 3\n\n"
        "asyncio.run(demo())"
    ),

    mk_md(
        "### Scenario 2 -- Thread-Safe Bounded Worker Pool\n\n"
        "**Context:** BuildFast limits concurrent GitHub API calls to 3 at a time "
        "using a semaphore on top of ThreadPoolExecutor."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import threading, time\n"
        "from concurrent.futures import ThreadPoolExecutor\n\n"
        "class BoundedPool:\n"
        "    def __init__(self, max_workers: int):\n"
        "        self._sem  = threading.Semaphore(max_workers)\n"
        "        self._pool = ThreadPoolExecutor(max_workers=max_workers)\n\n"
        "    def submit(self, fn, *args, **kwargs):\n"
        "        self._sem.acquire()\n"
        "        def run():\n"
        "            try:   return fn(*args, **kwargs)\n"
        "            finally: self._sem.release()  # ALWAYS release\n"
        "        return self._pool.submit(run)\n\n"
        "    def shutdown(self, wait=True): self._pool.shutdown(wait=wait)\n\n"
        "peak = {'n': 0, 'max': 0}; lock = threading.Lock()\n\n"
        "def task(i):\n"
        "    with lock: peak['n'] += 1; peak['max'] = max(peak['max'], peak['n'])\n"
        "    time.sleep(0.05)\n"
        "    with lock: peak['n'] -= 1\n"
        "    return f'done_{i}'\n\n"
        "pool = BoundedPool(3)\n"
        "results = [f.result() for f in [pool.submit(task, i) for i in range(12)]]\n"
        "pool.shutdown()\n"
        "print(f'All {len(results)} done. Peak concurrency: {peak[\"max\"]} (limit: 3)')\n"
        "assert peak['max'] <= 3"
    ),
]

# ─── Event-Driven ─────────────────────────────────────────────────────────────

EVT = [
    mk_md("---\n## Scenario-Based Code Questions -- Event-Driven Systems"),

    mk_md(
        "### Scenario 1 -- Idempotent Event Consumer\n\n"
        "**Context:** Kafka delivers `order.placed` at-least-once. "
        "Processing an order twice = billing twice. Implement idempotent handling.\n\n"
        "**Key insight:** Register the event_id BEFORE processing. "
        "If we crash after registration but before processing, we skip on retry -- "
        "safer than double-processing."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import threading\n"
        "from collections import OrderedDict\n\n"
        "class IdempotentConsumer:\n"
        "    def __init__(self, process_fn, max_seen=100_000):\n"
        "        self._fn, self._max = process_fn, max_seen\n"
        "        self._seen = OrderedDict()  # LRU-bounded set\n"
        "        self._lock = threading.Lock()\n"
        "        self.processed = self.duplicates = 0\n\n"
        "    def handle(self, event_id: str, payload: dict) -> bool:\n"
        "        with self._lock:\n"
        "            if event_id in self._seen:\n"
        "                self.duplicates += 1; return False\n"
        "            self._seen[event_id] = True  # register BEFORE processing\n"
        "            if len(self._seen) > self._max: self._seen.popitem(last=False)\n"
        "        self._fn(payload)  # outside lock -- parallel processing\n"
        "        self.processed += 1\n"
        "        return True\n\n"
        "orders = []\n"
        "consumer = IdempotentConsumer(lambda p: orders.append(p['order_id']))\n"
        "events = [('e1',{'order_id':'O1'}),('e2',{'order_id':'O2'}),\n"
        "          ('e1',{'order_id':'O1'}),('e3',{'order_id':'O3'}),  # e1 duplicate\n"
        "          ('e2',{'order_id':'O2'})]                            # e2 duplicate\n"
        "for eid, p in events:\n"
        "    r = consumer.handle(eid, p)\n"
        "    print(f'  {eid}: {\"processed\" if r else \"SKIP\"}')\n"
        "assert orders.count('O1') == 1\n"
        "print(f'Processed: {consumer.processed}, Dupes skipped: {consumer.duplicates}')"
    ),
]

# ─── Security ─────────────────────────────────────────────────────────────────

SEC = [
    mk_md("---\n## Scenario-Based Code Questions -- Networking, Security & Testing"),

    mk_md(
        "### Scenario 1 -- JWT Sign & Verify from Scratch\n\n"
        "**Context:** BuildFast issues JWT tokens. Implement sign/verify using "
        "only stdlib to understand the security properties.\n\n"
        "**JWT structure:** `base64url(header).base64url(payload).HMAC-SHA256(h.p, secret)`\n\n"
        "**Critical:** Use `hmac.compare_digest()` not `==` -- prevents timing attacks."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import base64, hashlib, hmac, json, time\n\n"
        "def b64e(data): return base64.urlsafe_b64encode(data).rstrip(b'=').decode()\n"
        "def b64d(s):\n"
        "    s += '=' * ((4 - len(s) % 4) % 4)\n"
        "    return base64.urlsafe_b64decode(s)\n\n"
        "def jwt_sign(payload: dict, secret: str) -> str:\n"
        "    header = b64e(json.dumps({'alg':'HS256','typ':'JWT'}).encode())\n"
        "    body   = b64e(json.dumps(payload).encode())\n"
        "    msg    = f'{header}.{body}'.encode()\n"
        "    sig    = b64e(hmac.new(secret.encode(), msg, hashlib.sha256).digest())\n"
        "    return f'{header}.{body}.{sig}'\n\n"
        "def jwt_verify(token: str, secret: str) -> dict:\n"
        "    h, b, sig = token.split('.')\n"
        "    msg = f'{h}.{b}'.encode()\n"
        "    expected = b64e(hmac.new(secret.encode(), msg, hashlib.sha256).digest())\n"
        "    if not hmac.compare_digest(expected, sig):  # constant-time!\n"
        "        raise ValueError('invalid signature')\n"
        "    payload = json.loads(b64d(b))\n"
        "    if 'exp' in payload and payload['exp'] < time.time():\n"
        "        raise ValueError('token expired')\n"
        "    return payload\n\n"
        "SECRET = 'dev-secret'\n"
        "tok = jwt_sign({'user_id':'u1','role':'admin','exp': time.time()+3600}, SECRET)\n"
        "payload = jwt_verify(tok, SECRET)\n"
        "print('Verified:', payload['user_id'], payload['role'])\n"
        "h, b, s = tok.split('.')\n"
        "try: jwt_verify(f'{h}.{b}.BADSIG', SECRET)\n"
        "except ValueError as e: print('Tampered:', e)\n"
        "old = jwt_sign({'user_id':'u2','exp': time.time()-1}, SECRET)\n"
        "try: jwt_verify(old, SECRET)\n"
        "except ValueError as e: print('Expired:', e)"
    ),

    mk_md(
        "### Scenario 2 -- SQL Injection: Vulnerable vs Safe\n\n"
        "**Context:** BuildFast lets users search build logs by commit message. "
        "Show the VULNERABLE pattern and the SAFE parameterized fix."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import sqlite3\n\n"
        "db = sqlite3.connect(':memory:')\n"
        "db.execute('CREATE TABLE builds (id INT, commit_msg TEXT, status TEXT)')\n"
        "db.executemany('INSERT INTO builds VALUES (?,?,?)',\n"
        "               [(1,'fix: auth bug','success'),(2,'feat: new UI','failed')])\n"
        "db.commit()\n\n"
        "# VULNERABLE -- string interpolation\n"
        "def search_VULN(commit_msg: str):\n"
        "    sql = f\"SELECT * FROM builds WHERE commit_msg LIKE '%{commit_msg}%'\"\n"
        "    return db.execute(sql).fetchall()\n\n"
        "injection = \"' OR '1'='1\"\n"
        "rows = search_VULN(injection)\n"
        "print(f'[VULN] Injection returned {len(rows)} rows (ALL rows exposed!)')\n\n"
        "# SAFE -- parameterized query\n"
        "def search_SAFE(commit_msg: str):\n"
        "    return db.execute('SELECT * FROM builds WHERE commit_msg LIKE ?',\n"
        "                      (f'%{commit_msg}%',)).fetchall()\n\n"
        "safe_rows = search_SAFE(injection)\n"
        "print(f'[SAFE] Injection returned {len(safe_rows)} rows (0 = blocked |/)')\n"
        "real_rows = search_SAFE('fix:')\n"
        "print(f'[SAFE] Legitimate search: {real_rows}')"
    ),
]

# ─── ELK ─────────────────────────────────────────────────────────────────────

ELK = [
    mk_md("---\n## Scenario-Based Code Questions -- ELK & Observability"),

    mk_md(
        "### Scenario 1 -- Structured JSON Logger with Correlation ID\n\n"
        "**Context:** BuildFast needs every log line to be valid JSON parseable by "
        "Elasticsearch. Include `timestamp`, `level`, `service`, `request_id`, `message`."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import json, time, uuid\n\n"
        "class StructuredLogger:\n"
        "    def __init__(self, service: str):\n"
        "        self.service, self._request_id = service, None\n\n"
        "    def bind(self, request_id: str):\n"
        "        child = StructuredLogger(self.service)\n"
        "        child._request_id = request_id\n"
        "        return child\n\n"
        "    def _log(self, level, msg, **extra):\n"
        "        print(json.dumps({\n"
        "            'timestamp':  time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),\n"
        "            'level':      level, 'service': self.service,\n"
        "            'request_id': self._request_id or 'no-request',\n"
        "            'message':    msg, **extra\n"
        "        }))\n\n"
        "    def info(self, m, **k):  self._log('INFO', m, **k)\n"
        "    def warn(self, m, **k):  self._log('WARN', m, **k)\n"
        "    def error(self, m, **k): self._log('ERROR', m, **k)\n\n"
        "log = StructuredLogger('build-service')\n"
        "req = log.bind(request_id=str(uuid.uuid4())[:8])\n"
        "req.info('Pipeline started', pipeline='frontend-ci', user='alice@co.com')\n"
        "req.warn('Slow step', step='lint', duration_ms=8900)\n"
        "req.error('Step failed', step='test', exit_code=1)"
    ),
]

# ─── Database Scaling ──────────────────────────────────────────────────────────

DB = [
    mk_md("---\n## Scenario-Based Code Questions -- Database Scaling"),

    mk_md(
        "### Scenario 1 -- Read Replica Query Router\n\n"
        "**Context:** ShopFlow's product catalogue: 95% reads, 5% writes. "
        "Route SELECT queries to the replica, writes to primary. "
        "Detect operation type from SQL prefix."
    ),

    mk_py(
        "# -- SOLUTION --\n"
        "import re\n\n"
        "class QueryRouter:\n"
        "    WRITE_RE = re.compile(\n"
        "        r'^\\s*(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE)',\n"
        "        re.IGNORECASE\n"
        "    )\n\n"
        "    def __init__(self, primary: str, replica: str):\n"
        "        self.primary, self.replica = primary, replica\n\n"
        "    def route(self, sql: str) -> str:\n"
        "        return self.primary if self.WRITE_RE.match(sql) else self.replica\n\n"
        "router = QueryRouter('postgres://primary:5432/db', 'postgres://replica:5432/db')\n"
        "cases = [\n"
        "    ('SELECT * FROM products WHERE id = $1', 'replica'),\n"
        "    ('INSERT INTO orders VALUES ($1, $2)',    'primary'),\n"
        "    ('UPDATE inventory SET qty = $1',         'primary'),\n"
        "    ('SELECT COUNT(*) FROM builds',           'replica'),\n"
        "]\n"
        "for sql, expected in cases:\n"
        "    t = router.route(sql)\n"
        "    assert expected in t\n"
        "    print(f'  {\"WRITE\" if expected==\"primary\" else \"READ \":5s}: {sql[:50]}')\n"
        "print('All routing correct |/')"
    ),
]


def main():
    print("=" * 64)
    print("ENHANCING INTERVIEW QUESTION NOTEBOOKS")
    print("=" * 64)

    targets = {
        "00-python-foundations/interview_questions.ipynb":            PY,
        "01-dsa/examples/interview_questions.ipynb":                  DSA,
        "04-system-design/examples/interview_questions.ipynb":        SD,
        "05-fastapi-advanced/examples/interview_questions.ipynb":     FA,
        "09-concurrency/examples/interview_questions.ipynb":          CONC,
        "08-event-driven-systems/examples/interview_questions.ipynb": EVT,
        "10-networking-security-testing/examples/interview_questions.ipynb": SEC,
        "06-elk-monitoring/examples/interview_questions.ipynb":       ELK,
        "07-database-scaling/examples/interview_questions.ipynb":     DB,
    }

    all_extra = []
    for rel, cells in targets.items():
        append_cells(rel, cells)
        all_extra.extend(cells)

    # Master bank
    bank = ROOT / "interview_bank.ipynb"
    if bank.exists():
        header = [mk_md("---\n## Scenario-Based Code Questions -- All Modules")]
        append_cells("interview_bank.ipynb", header + all_extra)

    print("\n" + "=" * 64)
    print("DONE")


if __name__ == "__main__":
    main()
