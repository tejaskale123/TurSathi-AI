/**
 * GoogleIcon — Pure React Native multicolor Google "G" logo.
 * No external icon library or SVG package required.
 * Renders the official Google G color segments (blue, red, yellow, green)
 * using clipped arc views inside a fixed container.
 */
import { View, StyleSheet } from 'react-native';

// Official Google brand colors
const G_BLUE   = '#4285F4';
const G_RED    = '#EA4335';
const G_YELLOW = '#FBBC05';
const G_GREEN  = '#34A853';

interface GoogleIconProps {
  size?: number;
}

export default function GoogleIcon({ size = 20 }: GoogleIconProps) {
  const half = size / 2;
  const thickness = size * 0.22; // ring thickness
  const outerR = half;
  const innerR = outerR - thickness;

  // Each quadrant is a square clipped to show one arc segment.
  // We overlay 4 colored squares (each half×half), each positioned in one
  // quadrant, then mask them by placing an inner white circle on top to
  // create the ring shape.
  return (
    <View style={[styles.container, { width: size, height: size }]}>
      {/* Top-right: Blue */}
      <View
        style={[
          styles.quadrant,
          { width: half, height: half, top: 0, right: 0, backgroundColor: G_BLUE },
        ]}
      />
      {/* Bottom-right: Green */}
      <View
        style={[
          styles.quadrant,
          { width: half, height: half, bottom: 0, right: 0, backgroundColor: G_GREEN },
        ]}
      />
      {/* Bottom-left: Yellow */}
      <View
        style={[
          styles.quadrant,
          { width: half, height: half, bottom: 0, left: 0, backgroundColor: G_YELLOW },
        ]}
      />
      {/* Top-left: Red */}
      <View
        style={[
          styles.quadrant,
          { width: half, height: half, top: 0, left: 0, backgroundColor: G_RED },
        ]}
      />

      {/* Inner white circle — creates the ring/donut shape */}
      <View
        style={[
          styles.innerMask,
          {
            width: innerR * 2,
            height: innerR * 2,
            borderRadius: innerR,
            top: half - innerR,
            left: half - innerR,
          },
        ]}
      />

      {/* Blue "G" bar that extends right from center — the distinctive Google G notch */}
      <View
        style={[
          styles.gBar,
          {
            width: half + thickness * 0.4,
            height: thickness,
            top: half - thickness / 2,
            left: half - thickness * 0.15,
            backgroundColor: G_BLUE,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    borderRadius: 9999,
    overflow: 'hidden',
    backgroundColor: 'transparent',
  },
  quadrant: {
    position: 'absolute',
  },
  innerMask: {
    position: 'absolute',
    backgroundColor: '#FFFFFF',
  },
  gBar: {
    position: 'absolute',
    borderRadius: 1,
  },
});
