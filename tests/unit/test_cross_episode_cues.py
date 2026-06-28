"""Tests for cross-episode intro/outro segment detection (pure fingerprint math).

_find_shared_segment finds the longest contiguous run of the target's fingerprint
that also appears in at least min_matches sibling fingerprints. Real intros/outros
play once per episode but recur across episodes, which is exactly this.
"""
import numpy as np

from audio_fingerprinter import _find_shared_segment


def _rand(n, rng):
    """Random uint32 fingerprint ints (two random 32-bit values differ ~50% of
    bits, well below the 0.73 match threshold, so unrelated content never matches)."""
    return rng.integers(0, 2 ** 32, size=n, dtype=np.uint64).astype(np.uint32)


WIN = 16  # ~2s probe window at ~8 ints/sec


def test_finds_segment_shared_across_min_matches():
    rng = np.random.default_rng(0)
    seg = _rand(80, rng)  # shared "intro" ~10s
    target = np.concatenate([_rand(20, rng), seg, _rand(40, rng)])
    seg_start = 20
    sib1 = np.concatenate([_rand(35, rng), seg, _rand(10, rng)])   # has seg
    sib2 = np.concatenate([_rand(5, rng), seg, _rand(50, rng)])    # has seg
    sib3 = _rand(120, rng)                                         # no seg
    res = _find_shared_segment(target, [sib1, sib2, sib3], win=WIN,
                               similarity=0.73, min_matches=2, min_len=24, max_len=400)
    assert res is not None
    start, end, count = res
    assert count >= 2
    assert abs(start - seg_start) <= WIN
    assert (end - start) >= 60  # most of the 80-int segment recovered


def test_returns_none_when_only_one_sibling_matches():
    rng = np.random.default_rng(1)
    seg = _rand(80, rng)
    target = np.concatenate([_rand(20, rng), seg, _rand(20, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])   # only this one
    sib2 = _rand(120, rng)
    sib3 = _rand(120, rng)
    res = _find_shared_segment(target, [sib1, sib2, sib3], win=WIN,
                               similarity=0.73, min_matches=2, min_len=24, max_len=400)
    assert res is None


def test_returns_none_when_shared_run_too_short():
    rng = np.random.default_rng(2)
    seg = _rand(20, rng)  # ~2.5s, below min_len
    target = np.concatenate([_rand(20, rng), seg, _rand(20, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])
    sib2 = np.concatenate([_rand(30, rng), seg, _rand(5, rng)])
    res = _find_shared_segment(target, [sib1, sib2], win=WIN,
                               similarity=0.73, min_matches=2, min_len=40, max_len=400)
    assert res is None


def test_caps_run_at_max_len():
    rng = np.random.default_rng(3)
    seg = _rand(200, rng)  # long shared run
    target = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])
    sib1 = np.concatenate([_rand(5, rng), seg, _rand(5, rng)])
    sib2 = np.concatenate([_rand(15, rng), seg, _rand(5, rng)])
    res = _find_shared_segment(target, [sib1, sib2], win=WIN,
                               similarity=0.73, min_matches=2, min_len=24, max_len=120)
    assert res is not None
    start, end, _ = res
    assert (end - start) <= 120


def test_does_not_overextend_past_shared_boundary():
    # A shared prefix followed by content that DIFFERS per episode must not be
    # absorbed into the run (the cumulative-average bug grew it ~2x too long).
    rng = np.random.default_rng(4)
    seg = _rand(40, rng)  # ~5s shared
    target = np.concatenate([_rand(8, rng), seg, _rand(60, rng)])
    sib1 = np.concatenate([_rand(12, rng), seg, _rand(60, rng)])
    sib2 = np.concatenate([_rand(4, rng), seg, _rand(60, rng)])
    res = _find_shared_segment(target, [sib1, sib2], win=WIN, similarity=0.73,
                               min_matches=2, min_len=24, max_len=400)
    assert res is not None
    start, end, _ = res
    assert (end - start) <= 40 + 2 * (WIN // 2)  # ~shared length, not doubled


def test_backward_walk_recovers_onset():
    # The probe can land mid-segment; the run must extend back to the true start.
    rng = np.random.default_rng(6)
    seg = _rand(80, rng)
    target = np.concatenate([_rand(24, rng), seg, _rand(24, rng)])
    sib1 = np.concatenate([_rand(40, rng), seg, _rand(8, rng)])
    sib2 = np.concatenate([_rand(8, rng), seg, _rand(40, rng)])
    start, end, _ = _find_shared_segment(target, [sib1, sib2], win=WIN,
                                         similarity=0.73, min_matches=2,
                                         min_len=24, max_len=400)
    assert abs(start - 24) <= WIN // 2  # onset recovered, not the mid probe


def test_prefer_earliest_vs_latest():
    # Two shared runs in the target; intro wants the earliest, outro the latest.
    rng = np.random.default_rng(5)
    seg_a = _rand(40, rng)
    seg_b = _rand(40, rng)
    target = np.concatenate([_rand(5, rng), seg_a, _rand(30, rng), seg_b, _rand(5, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg_a, _rand(10, rng), seg_b, _rand(10, rng)])
    sib2 = np.concatenate([_rand(3, rng), seg_a, _rand(20, rng), seg_b, _rand(3, rng)])
    earliest = _find_shared_segment(target, [sib1, sib2], win=WIN, similarity=0.73,
                                    min_matches=2, min_len=24, max_len=400,
                                    prefer='earliest')
    latest = _find_shared_segment(target, [sib1, sib2], win=WIN, similarity=0.73,
                                  min_matches=2, min_len=24, max_len=400,
                                  prefer='latest')
    assert earliest is not None and latest is not None
    assert earliest[0] < latest[0]
