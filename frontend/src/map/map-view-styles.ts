import Feature from "ol/Feature";
import type Geometry from "ol/geom/Geometry";
import Fill from "ol/style/Fill";
import Stroke from "ol/style/Stroke";
import Style from "ol/style/Style";

const selectionPulsePeriodMs = 1400;
const selectionPulseMinWidth = 4;
const selectionPulseMaxWidth = 8;
const selectionPulseMinAlpha = 0.2;
const selectionPulseMaxAlpha = 0.7;

export function createMapViewStyles(isReducedMotion: () => boolean) {
  const defaultFeatureStyle = new Style({
    stroke: new Stroke({ color: "#ff3333", width: 3 }),
    fill: new Fill({ color: "rgba(255, 51, 51, 0.2)" })
  });

  const selectedHaloStyle = new Style({
    stroke: new Stroke({ color: "rgba(255, 255, 255, 0.95)", width: 8 }),
    fill: new Fill({ color: "rgba(0, 0, 0, 0)" })
  });

  const selectedInnerStyle = new Style({
    stroke: new Stroke({ color: "#ffd400", width: 4 }),
    fill: new Fill({ color: "rgba(0, 0, 0, 0)" })
  });

  const selectedPulseStroke = new Stroke({
    color: `rgba(255, 212, 0, ${selectionPulseMinAlpha})`,
    width: selectionPulseMinWidth
  });

  const selectedPulseStyle = new Style({
    stroke: selectedPulseStroke,
    fill: new Fill({ color: "rgba(0, 0, 0, 0)" })
  });

  const defaultStyleSelector = (_feature: Feature<Geometry>): Style => defaultFeatureStyle;

  const selectedStyleSelector = (_feature: Feature<Geometry>): Style[] => {
    const progress = ((Date.now() % selectionPulsePeriodMs) / selectionPulsePeriodMs) * Math.PI * 2;
    const eased = (Math.sin(progress) + 1) / 2;
    const pulseAlpha =
      selectionPulseMinAlpha + (selectionPulseMaxAlpha - selectionPulseMinAlpha) * eased;
    const pulseWidth =
      selectionPulseMinWidth + (selectionPulseMaxWidth - selectionPulseMinWidth) * eased;

    selectedPulseStroke.setColor(`rgba(255, 212, 0, ${pulseAlpha})`);
    selectedPulseStroke.setWidth(pulseWidth);

    if (isReducedMotion()) {
      return [selectedHaloStyle, selectedInnerStyle];
    }
    return [selectedHaloStyle, selectedInnerStyle, selectedPulseStyle];
  };

  return { defaultStyleSelector, selectedStyleSelector };
}
