"""Merge cue-template candidates: within-episode recurrence + cross-episode intro/outro.

Pure -- no Flask/DB imports -- so the candidate-scan worker and unit tests use it
directly.
"""
from config import AUDIO_CUE_TYPE_SHOW_INTRO, AUDIO_CUE_TYPE_SHOW_OUTRO
from utils.time import ranges_overlap

_SUGGESTED_TYPE = {
    'intro': AUDIO_CUE_TYPE_SHOW_INTRO,
    'outro': AUDIO_CUE_TYPE_SHOW_OUTRO,
}


def merge_cue_candidates(recurring, cross_episode):
    """Combine within-episode recurrence hits with cross-episode intro/outro hits.

    ``recurring`` items are ``{start,end,count}`` (ad-break stings that repeat
    within the episode). ``cross_episode`` items are
    ``{start,end,kind:'intro'|'outro',episodeMatches}`` (segments that recur across
    sibling episodes). Returns typed candidates carrying a ``suggestedType`` so the
    capture tool preselects the cue type. Intro/outro rank first (high-value, typed),
    then recurring (already in descending recurrence order). A recurring hit that
    overlaps a cross-episode hit is the same sound surfaced twice, so it is dropped.
    """
    merged = [
        {
            'start': c['start'], 'end': c['end'], 'kind': c['kind'],
            'episodeMatches': c.get('episodeMatches'),
            'suggestedType': _SUGGESTED_TYPE.get(c['kind']),
        }
        for c in cross_episode
    ]
    merged.extend(
        {
            'start': c['start'], 'end': c['end'], 'kind': 'recurring',
            'count': c.get('count'), 'suggestedType': None,
        }
        for c in recurring
        if not any(ranges_overlap(c['start'], c['end'], x['start'], x['end'])
                   for x in cross_episode)
    )
    return merged
