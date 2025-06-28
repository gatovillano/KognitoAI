/**
 * Utility to handle base64 image data and prepare it for frontend display.
 */

/**
 * Converts a base64 string to a data URL for image display.
 * @param base64String The base64-encoded image string.
 * @returns A data URL that can be used as an image source.
 */
export function sentImage(base64String: string): string {
  // Check if the base64 string already contains the data URL prefix
  if (base64String.startsWith('data:image')) {
    return base64String;
  }
  // Assuming the image is in PNG format as per the mindmap generator tool
  return `data:image/png;base64,${base64String}`;
}

/**
 * Downloads the image from a base64 string.
 * @param base64String The base64-encoded image string.
 * @param fileName The name to give to the downloaded file.
 */
export function downloadImage(base64String: string, fileName: string = 'mindmap.png'): void {
  const dataUrl = sentImage(base64String);
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
