"""Tests for cross-episode intro/outro segment detection (pure fingerprint math).

_find_shared_segments finds every contiguous run of the target's fingerprint that
also appears in at least min_matches sibling fingerprints. Real intros/outros play
once per episode but recur across episodes, which is exactly this.
"""
import numpy as np

from audio_fingerprinter import _find_shared_segments


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
    segs = _find_shared_segments(target, [sib1, sib2, sib3], win=WIN,
                                 similarity=0.73, min_matches=2, min_len=24, max_len=400)
    assert len(segs) == 1
    start, end, count = segs[0]
    assert count >= 2
    assert abs(start - seg_start) <= WIN
    assert (end - start) >= 60  # most of the 80-int segment recovered


def test_finds_multiple_segments_ordered():
    # Two distinct shared runs; both surface, left to right.
    rng = np.random.default_rng(5)
    seg_a = _rand(40, rng)
    seg_b = _rand(40, rng)
    target = np.concatenate([_rand(5, rng), seg_a, _rand(30, rng), seg_b, _rand(5, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg_a, _rand(10, rng), seg_b, _rand(10, rng)])
    sib2 = np.concatenate([_rand(3, rng), seg_a, _rand(20, rng), seg_b, _rand(3, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=WIN, similarity=0.73,
                                 min_matches=2, min_len=24, max_len=400)
    assert len(segs) == 2
    assert segs[0][0] < segs[1][0]  # ordered by start


def test_empty_when_only_one_sibling_matches():
    rng = np.random.default_rng(1)
    seg = _rand(80, rng)
    target = np.concatenate([_rand(20, rng), seg, _rand(20, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])   # only this one
    sib2 = _rand(120, rng)
    sib3 = _rand(120, rng)
    segs = _find_shared_segments(target, [sib1, sib2, sib3], win=WIN,
                                 similarity=0.73, min_matches=2, min_len=24, max_len=400)
    assert segs == []


def test_empty_when_shared_run_too_short():
    rng = np.random.default_rng(2)
    seg = _rand(20, rng)  # ~2.5s, below min_len
    target = np.concatenate([_rand(20, rng), seg, _rand(20, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])
    sib2 = np.concatenate([_rand(30, rng), seg, _rand(5, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=WIN,
                                 similarity=0.73, min_matches=2, min_len=40, max_len=400)
    assert segs == []


def test_caps_run_at_max_len_without_fragmenting():
    # A single shared segment longer than max_len yields ONE capped candidate,
    # not a stack of overlapping fragments (the cap must not defeat skip-past).
    rng = np.random.default_rng(3)
    seg = _rand(200, rng)  # long shared run, well over max_len
    target = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])
    sib1 = np.concatenate([_rand(5, rng), seg, _rand(5, rng)])
    sib2 = np.concatenate([_rand(15, rng), seg, _rand(5, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=WIN,
                                 similarity=0.73, min_matches=2, min_len=24, max_len=120)
    assert len(segs) == 1
    start, end, _ = segs[0]
    assert (end - start) <= 120


def test_does_not_overextend_past_shared_boundary():
    # A shared prefix followed by content that DIFFERS per episode must not be
    # absorbed into the run (the cumulative-average bug grew it ~2x too long).
    rng = np.random.default_rng(4)
    seg = _rand(40, rng)  # ~5s shared
    target = np.concatenate([_rand(8, rng), seg, _rand(60, rng)])
    sib1 = np.concatenate([_rand(12, rng), seg, _rand(60, rng)])
    sib2 = np.concatenate([_rand(4, rng), seg, _rand(60, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=WIN, similarity=0.73,
                                 min_matches=2, min_len=24, max_len=400)
    assert len(segs) >= 1
    start, end, _ = segs[0]
    assert (end - start) <= 40 + 2 * (WIN // 2)  # ~shared length, not doubled


def test_backward_walk_recovers_onset():
    # The probe can land mid-segment; the run must extend back to the true start.
    rng = np.random.default_rng(6)
    seg = _rand(80, rng)
    target = np.concatenate([_rand(24, rng), seg, _rand(24, rng)])
    sib1 = np.concatenate([_rand(40, rng), seg, _rand(8, rng)])
    sib2 = np.concatenate([_rand(8, rng), seg, _rand(40, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=WIN, similarity=0.73,
                                 min_matches=2, min_len=24, max_len=400)
    assert len(segs) == 1
    assert abs(segs[0][0] - 24) <= WIN // 2  # onset recovered, not the mid probe


def test_fine_edge_recovery_sub_step():
    # After coarse grow, a 1-subfp refinement step must recover the true edge
    # when the segment boundary falls mid-coarse-step.
    # The seg is planted at offset 35 (not a multiple of step=8), so the true
    # lo boundary (35) and hi boundary (35+40=75) both fall off the coarse grid,
    # forcing the fine refinement path to exercise both edges.
    rng = np.random.default_rng(7)
    step = 8
    win = 16
    seg = _rand(40, rng)  # shared segment of 40 subfps
    # Plant seg in target at position 35 (off the step=8 coarse grid).
    target = np.concatenate([_rand(35, rng), seg, _rand(35, rng)])
    sib1 = np.concatenate([_rand(10, rng), seg, _rand(10, rng)])
    sib2 = np.concatenate([_rand(20, rng), seg, _rand(20, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=win,
                                 step=step, similarity=0.73,
                                 min_matches=2, min_len=win, max_len=400)
    assert len(segs) == 1
    # Both edges must be recovered within 4 subfps (half a step) of true boundaries.
    assert abs(segs[0][0] - 35) <= 4       # lo-edge fine refinement
    assert abs(segs[0][1] - (35 + 40)) <= 4  # hi-edge fine refinement


def test_max_len_per_zone_bound():
    # max_len caps the returned segment length; passing max_len=32 on a
    # 80-subfp segment should yield a result with (end-start) <= 32.
    rng = np.random.default_rng(8)
    seg = _rand(80, rng)
    target = np.concatenate([_rand(16, rng), seg, _rand(16, rng)])
    sib1 = np.concatenate([_rand(8, rng), seg, _rand(8, rng)])
    sib2 = np.concatenate([_rand(24, rng), seg, _rand(24, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=16,
                                 step=8, similarity=0.73,
                                 min_matches=2, min_len=16, max_len=32)
    assert len(segs) == 1
    assert (segs[0][1] - segs[0][0]) <= 32


def test_claimed_run_does_not_cross_into_prior():
    # A new candidate that starts inside a previously claimed run must not be
    # emitted (no overlapping duplicates).
    rng = np.random.default_rng(9)
    seg = _rand(48, rng)
    target = np.concatenate([_rand(8, rng), seg, _rand(100, rng)])
    sib1 = np.concatenate([_rand(4, rng), seg, _rand(50, rng)])
    sib2 = np.concatenate([_rand(16, rng), seg, _rand(50, rng)])
    segs = _find_shared_segments(target, [sib1, sib2], win=16,
                                 step=8, similarity=0.73,
                                 min_matches=2, min_len=16, max_len=400)
    assert len(segs) == 1  # only one result, no overlapping duplicate
    assert segs[0][0] >= 0 and segs[0][1] <= 8 + 48 + 8  # within plausible range
