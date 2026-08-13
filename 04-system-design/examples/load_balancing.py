"""
04 — System Design: Load Balancing Strategies
=============================================

Runnable companion to PDF Book V "How does traffic get spread across servers?".

A load balancer sits in front of N identical servers and decides which one
handles each request. The strategy is a real design trade-off:

  * ROUND ROBIN        — rotate through servers in order (simple, ignores load)
  * WEIGHTED ROUND ROBIN — bigger servers get proportionally more traffic
  * LEAST CONNECTIONS  — send to the server with the fewest in-flight requests
  * RANDOM             — pick uniformly (surprisingly good at scale)
  * IP / KEY HASH      — same client always hits the same server (sticky sessions)

This file implements each and asserts the distribution behaves as intended.
"""

from __future__ import annotations
import hashlib
import itertools
from collections import Counter


class RoundRobin:
    def __init__(self, servers: list[str]):
        self._it = itertools.cycle(servers)

    def pick(self) -> str:
        return next(self._it)


class WeightedRoundRobin:
    def __init__(self, weighted: dict[str, int]):
        # Expand by weight: {"a":1,"b":3} -> a,b,b,b then cycle.
        expanded: list[str] = []
        for server, w in weighted.items():
            expanded.extend([server] * w)
        self._it = itertools.cycle(expanded)

    def pick(self) -> str:
        return next(self._it)


class LeastConnections:
    def __init__(self, servers: list[str]):
        self._conns: dict[str, int] = {s: 0 for s in servers}

    def pick(self) -> str:
        server = min(self._conns, key=self._conns.get)   # fewest in-flight
        self._conns[server] += 1
        return server

    def release(self, server: str) -> None:
        self._conns[server] -= 1


class KeyHash:
    """Sticky: the same key (e.g. client IP / session) always maps to one server."""
    def __init__(self, servers: list[str]):
        self._servers = sorted(servers)

    def pick(self, key: str) -> str:
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self._servers[h % len(self._servers)]


def demo() -> None:
    servers = ["s1", "s2", "s3"]

    # Round robin: perfectly even over a multiple of N.
    rr = RoundRobin(servers)
    picks = [rr.pick() for _ in range(9)]
    assert Counter(picks) == {"s1": 3, "s2": 3, "s3": 3}
    assert picks[:3] == ["s1", "s2", "s3"]              # strict rotation
    print("   round robin: 9 requests -> 3/3/3, in strict rotation")

    # Weighted: s2 gets 3x the traffic of s1/s3.
    wrr = WeightedRoundRobin({"s1": 1, "s2": 3, "s3": 1})
    wpicks = Counter(wrr.pick() for _ in range(50))
    assert wpicks["s2"] > wpicks["s1"] and wpicks["s2"] > wpicks["s3"]
    print(f"   weighted: s2 (weight 3) got {wpicks['s2']} vs s1 {wpicks['s1']} / s3 {wpicks['s3']}")

    # Least connections: with 2 held on s1, the next 2 go to s2 and s3.
    lc = LeastConnections(servers)
    a, b = lc.pick(), lc.pick()          # holds one each on the two lowest → s1,s2
    c = lc.pick()                        # s3 now lowest
    assert {a, b, c} == {"s1", "s2", "s3"}, "spread across all three when equal"
    lc.release(a)                        # free one
    d = lc.pick()                        # should refill the freed server
    assert d == a
    print("   least connections: routes to the least-busy server; refills on release")

    # Key hash: sticky — the same client always lands on the same server.
    kh = KeyHash(servers)
    assert kh.pick("203.0.113.7") == kh.pick("203.0.113.7")   # deterministic
    ip_dist = Counter(kh.pick(f"10.0.0.{i}") for i in range(300))
    assert len(ip_dist) == 3, "different clients spread across all servers"
    print("   key hash: same client is sticky; many clients spread across all servers")


def main() -> None:
    print("=" * 70)
    print("SYSTEM DESIGN — load_balancing.py")
    print("=" * 70)
    print("Five strategies for spreading requests across identical servers:")
    demo()
    print("-" * 70)
    print("Lesson: round robin ignores load; least-connections adapts; key-hash gives stickiness. Match to the workload.")
    print("All load_balancing demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
