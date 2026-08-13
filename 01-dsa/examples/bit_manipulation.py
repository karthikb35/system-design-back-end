"""
01 — DSA Internals: Bit Manipulation Toolkit
============================================

Runnable companion to PDF Book II "Thinking in bits".

Integers are binary under the hood. Bit tricks turn certain O(n) or extra-space
problems into O(1) space / branch-free operations, and they show up constantly
in interviews (subsets, flags, low-level protocols, hashing).

Core operators:
    &  AND    |  OR    ^  XOR    ~  NOT    <<  left shift    >>  right shift

Key identities used below:
    x ^ x == 0,   x ^ 0 == x          -> XOR cancels pairs (find the loner)
    x & (x - 1)                       -> clears the lowest set bit
    x & -x                            -> isolates the lowest set bit
    x & (x - 1) == 0                  -> x is a power of two (for x > 0)
"""

from __future__ import annotations


def get_bit(x: int, i: int) -> int:
    """Return bit i (0 = least significant)."""
    return (x >> i) & 1


def set_bit(x: int, i: int) -> int:
    return x | (1 << i)


def clear_bit(x: int, i: int) -> int:
    return x & ~(1 << i)


def toggle_bit(x: int, i: int) -> int:
    return x ^ (1 << i)


def count_set_bits(x: int) -> int:
    """Brian Kernighan's algorithm: loops once per set bit, not per bit."""
    count = 0
    while x:
        x &= x - 1                          # drop the lowest set bit
        count += 1
    return count


def is_power_of_two(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0


def lowest_set_bit(x: int) -> int:
    """Isolate the lowest set bit, e.g. 0b10110 -> 0b00010."""
    return x & -x


def swap_without_temp(a: int, b: int) -> tuple[int, int]:
    a ^= b
    b ^= a
    a ^= b
    return a, b


def single_number(nums: list[int]) -> int:
    """Every element appears twice except one — XOR cancels the pairs. O(1) space."""
    result = 0
    for n in nums:
        result ^= n
    return result


def all_subsets(items: list) -> list[list]:
    """Enumerate the 2**n subsets: bit j of the counter = include items[j]."""
    n = len(items)
    out: list[list] = []
    for mask in range(1 << n):
        subset = [items[j] for j in range(n) if mask & (1 << j)]
        out.append(subset)
    return out


def demo() -> None:
    # Single-bit operations.
    assert get_bit(0b1010, 1) == 1 and get_bit(0b1010, 0) == 0
    assert set_bit(0b1000, 0) == 0b1001
    assert clear_bit(0b1011, 1) == 0b1001
    assert toggle_bit(0b1010, 2) == 0b1110
    print("   get/set/clear/toggle single bits verified")

    # Population count and power-of-two.
    assert count_set_bits(0b10110110) == 5
    assert count_set_bits(255) == 8
    assert [is_power_of_two(n) for n in (1, 2, 3, 4, 16, 17)] == [True, True, False, True, True, False]
    print("   count_set_bits(0b10110110) =", count_set_bits(0b10110110), " is_power_of_two ✔")

    # Isolate lowest set bit & XOR swap.
    assert lowest_set_bit(0b10110) == 0b00010
    assert swap_without_temp(7, 42) == (42, 7)
    print("   lowest_set_bit + XOR swap verified")

    # Classic interview: the number that appears once.
    assert single_number([4, 1, 2, 1, 2]) == 4
    assert single_number([7]) == 7
    print("   single_number([4,1,2,1,2]) =", single_number([4, 1, 2, 1, 2]), " (O(1) space via XOR)")

    # Subset enumeration via bitmask.
    subs = all_subsets(["a", "b", "c"])
    assert len(subs) == 8 and [] in subs and ["a", "b", "c"] in subs
    print("   all_subsets(['a','b','c']) ->", len(subs), "subsets (2**3)")


def main() -> None:
    print("=" * 70)
    print("DSA INTERNALS — bit_manipulation.py")
    print("=" * 70)
    print("Branch-free / O(1)-space tricks with & | ^ ~ << >>:")
    demo()
    print("-" * 70)
    print("Lesson: XOR cancels pairs; x&(x-1) clears the lowest bit; a bitmask enumerates all subsets.")
    print("All bit_manipulation demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
