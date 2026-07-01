"""Unit tests for the cue threshold auto-suggest helper (#350)."""
from audio_analysis.cue_threshold_suggest import suggest_cue_threshold


def test_bimodal_scores_suggest_gap_midpoint():
    # Noise cluster ~0.45-0.52, signal cluster ~0.90-0.97: wide clean gap.
    scores = [0.45, 0.48, 0.50, 0.52, 0.90, 0.93, 0.95, 0.97]
    out = suggest_cue_threshold(scores)
    assert out['confidence'] == 'high'
    assert 0.52 < out['suggested'] < 0.90
    assert out['effectFloorWarning'] is None


def test_unimodal_scores_are_low_confidence():
    scores = [0.48, 0.49, 0.50, 0.51, 0.52, 0.53]
    out = suggest_cue_threshold(scores)
    assert out['confidence'] == 'low'
    assert 'suggested' not in out or out.get('suggested') is None


def test_thin_sample_is_low_confidence():
    out = suggest_cue_threshold([0.95])
    assert out['confidence'] == 'low'


def test_signal_below_effect_floor_warns():
    # Real cluster sits at 0.67-0.73, below the 0.80 effect floor.
    scores = [0.45, 0.48, 0.50, 0.67, 0.70, 0.73]
    out = suggest_cue_threshold(scores, effect_floor=0.80)
    assert out['effectFloorWarning'] == 'signal-below-floor'


def test_live_effect_floor_below_signal_is_clean():
    # Same cluster, but the feed lowered its snap floor to 0.60 -> no warning.
    scores = [0.45, 0.48, 0.50, 0.67, 0.70, 0.73]
    out = suggest_cue_threshold(scores, effect_floor=0.60)
    assert out['effectFloorWarning'] is None
