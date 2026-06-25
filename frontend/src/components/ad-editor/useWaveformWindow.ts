import {
  useCallback,
  useDeferredValue,
  useMemo,
  useState,
  type MutableRefObject,
} from 'react';

export interface WaveformWindow {
  zoom: number;
  /** Visible time span [windowStart, windowEnd]; the rendered view IS the window. */
  windowStart: number;
  windowEnd: number;
  windowCenter: number;
  /** Pan the window so this time is centered (no zoom change). */
  setWindowCenter: (t: number) => void;
  /** Set absolute zoom, recentering on anchorTime (defaults to the live playhead). */
  setZoom: (z: number, anchorTime?: number) => void;
  /** Multiply zoom, recentering on anchorTime (defaults to the live playhead). */
  zoomBy: (factor: number, anchorTime?: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  /** Back to 1x, centered on `center`. */
  reset: (center: number) => void;
}

/**
 * Shared zoomable waveform window for the cue-marking and ad-edit modals
 * (issue #350). Zoom narrows the rendered time span around windowCenter rather
 * than widening a scrollable canvas -- wavesurfer caps its canvas at ~16000px
 * and leaves everything past that blank, so a giant-canvas zoom went blank at
 * the far end. Zooming recenters on the live playhead (Audacity-style) so the
 * cursor stays put in the view. Deferred so dragging the zoom slider stays
 * responsive while the windowed peaks re-slice.
 */
export function useWaveformWindow(
  totalDuration: number,
  initialCenter: number,
  playheadRef: MutableRefObject<number>,
  zoomMin = 1,
  zoomMax = 50,
): WaveformWindow {
  const [zoom, setZoomRaw] = useState(1);
  const [windowCenter, setWindowCenter] = useState(initialCenter);
  const deferredZoom = useDeferredValue(zoom);
  const deferredCenter = useDeferredValue(windowCenter);

  const { windowStart, windowEnd } = useMemo(() => {
    const winDur = Math.min(
      totalDuration,
      Math.max(0.5, totalDuration / Math.max(1, deferredZoom)),
    );
    let start = Math.max(0, Math.min(totalDuration - winDur, deferredCenter - winDur / 2));
    if (!Number.isFinite(start)) start = 0;
    return { windowStart: start, windowEnd: start + winDur };
  }, [deferredZoom, deferredCenter, totalDuration]);

  const clampZoom = useCallback(
    (z: number) => Math.max(zoomMin, Math.min(zoomMax, z)),
    [zoomMin, zoomMax],
  );

  const anchor = useCallback(
    (anchorTime?: number) => {
      const t = anchorTime ?? playheadRef.current;
      if (Number.isFinite(t)) setWindowCenter(t);
    },
    [playheadRef],
  );

  const setZoom = useCallback(
    (z: number, anchorTime?: number) => {
      anchor(anchorTime);
      setZoomRaw(clampZoom(z));
    },
    [anchor, clampZoom],
  );

  const zoomBy = useCallback(
    (factor: number, anchorTime?: number) => {
      anchor(anchorTime);
      setZoomRaw((z) => clampZoom(+(z * factor).toFixed(2)));
    },
    [anchor, clampZoom],
  );

  const zoomIn = useCallback(() => zoomBy(1.5), [zoomBy]);
  const zoomOut = useCallback(() => zoomBy(1 / 1.5), [zoomBy]);

  const reset = useCallback((center: number) => {
    setZoomRaw(1);
    setWindowCenter(center);
  }, []);

  return {
    zoom,
    windowStart,
    windowEnd,
    windowCenter,
    setWindowCenter,
    setZoom,
    zoomBy,
    zoomIn,
    zoomOut,
    reset,
  };
}
