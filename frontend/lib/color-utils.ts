/**
 * Determines if a hex color is light or dark based on luminance.
 * Useful for choosing contrasting text colors.
 *
 * @param hex - Hex color string (e.g., "#FFFFFF" or "FFFFFF")
 * @returns true if the color is light (should use dark text), false if dark (should use light text)
 */
export function isLightColor(hex: string): boolean {
  const color = hex.replace("#", "");
  const r = parseInt(color.substring(0, 2), 16);
  const g = parseInt(color.substring(2, 4), 16);
  const b = parseInt(color.substring(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5;
}

/**
 * Returns appropriate text color class based on background color luminance.
 */
export function getContrastTextClass(hex: string): string {
  return isLightColor(hex) ? "text-slate-900" : "text-white";
}
