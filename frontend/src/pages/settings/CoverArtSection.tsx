import CollapsibleSection from '../../components/CollapsibleSection';
import ToggleSwitch from '../../components/ToggleSwitch';

interface CoverArtSectionProps {
  artworkWatermarkEnabled: boolean;
  onArtworkWatermarkEnabledChange: (enabled: boolean) => void;
}

function CoverArtSection({
  artworkWatermarkEnabled,
  onArtworkWatermarkEnabledChange,
}: CoverArtSectionProps) {
  return (
    <CollapsibleSection
      title="Cover Art"
      subtitle="Brand the served cover art so the filtered feed is easy to tell apart in a podcast app."
    >
      <div>
        <label className="flex items-center gap-3 cursor-pointer">
          <ToggleSwitch
            checked={artworkWatermarkEnabled}
            onChange={onArtworkWatermarkEnabledChange}
            ariaLabel="Overlay MinusPod badge on cover art"
          />
          <span className="text-sm font-medium text-foreground">
            Overlay MinusPod badge on cover art
          </span>
        </label>
        <p className="mt-2 text-sm text-muted-foreground">
          Adds a small MinusPod badge to the bottom-right corner of each served feed's cover art, so the filtered version is easy to tell apart from the original in your podcast app. Off by default.
        </p>
      </div>
    </CollapsibleSection>
  );
}

export default CoverArtSection;
