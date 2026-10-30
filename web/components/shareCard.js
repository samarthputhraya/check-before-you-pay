const CARD_WIDTH = 1080;
const CARD_HEIGHT = 1350;
export const FONT_STACK = 'system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Noto Sans Devanagari, Noto Sans Tamil, Noto Sans Telugu, Noto Sans Kannada, Noto Sans Bengali, sans-serif';

function escapeXml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;',
  })[char]);
}

let measureContext = null;

/** Text width in px for a CSS font, measured the way the browser will draw the card. */
function measure(text, font) {
  if (!measureContext) measureContext = document.createElement('canvas').getContext('2d');
  if (!measureContext) return String(text).length * 30; // no canvas: a rough upper bound
  measureContext.font = font;
  return measureContext.measureText(text).width;
}

/** Wrap by measured width, not by character count, so Tamil or Kannada words never run off the card. A word wider
 *  than a line is split by characters; text that still doesn't fit ends with an ellipsis. */
export function wrapToWidth(value, font, maxWidth, maxLines) {
  const words = String(value || '').trim().split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  let dropped = false;
  const push = (text) => { if (lines.length < maxLines) lines.push(text); else dropped = true; };
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (measure(candidate, font) <= maxWidth) { line = candidate; continue; }
    if (line) { push(line); line = ''; }
    if (measure(word, font) <= maxWidth) { line = word; continue; }
    let piece = '';
    for (const ch of Array.from(word)) {
      if (measure(piece + ch, font) > maxWidth && piece) { push(piece); piece = ''; }
      piece += ch;
    }
    line = piece;
  }
  if (line) push(line);
  if (dropped && lines.length) {
    let last = lines[lines.length - 1].replace(/[.…]+$/, '');
    while (last && measure(`${last}…`, font) > maxWidth) last = Array.from(last).slice(0, -1).join('');
    lines[lines.length - 1] = `${last}…`;
  }
  return lines;
}

function lineMarkup(lines, x, y, lineHeight, className) {
  return lines.map((line, index) =>
    `<text class="${className}" x="${x}" y="${y + index * lineHeight}">${escapeXml(line)}</text>`,
  ).join('');
}

const TEXT_WIDTH = 988 - 92;

function cardSvg(result, bandLabel, labels) {
  const colors = {
    high_risk: { ink: '#9d1c14', pale: '#fdecea', accent: '#b42318' },
    caution: { ink: '#854000', pale: '#fff3e0', accent: '#a64b00' },
    no_known_signals: { ink: '#344054', pale: '#f0f2f1', accent: '#667085' },
  }[result.band] || { ink: '#344054', pale: '#f0f2f1', accent: '#667085' };
  // Shrink a long headline before cutting it: 54 px for up to 4 lines, else 44 px for up to 5.
  let headSize = 54;
  let headlineLines = wrapToWidth(result.headline, `700 54px ${FONT_STACK}`, TEXT_WIDTH, 5);
  if (headlineLines.length > 4) {
    headSize = 44;
    headlineLines = wrapToWidth(result.headline, `700 44px ${FONT_STACK}`, TEXT_WIDTH, 5);
  }
  const headlineMarkup = lineMarkup(headlineLines, 92, 642, Math.round(headSize * 1.42), 'headline');
  // The pill grows with its label (up to the card's width) and the label shrinks if it still doesn't fit.
  let bandSize = 30;
  while (bandSize > 20 && measure(bandLabel, `700 ${bandSize}px ${FONT_STACK}`) > TEXT_WIDTH - 110) bandSize -= 2;
  const pillWidth = Math.min(TEXT_WIDTH, Math.max(260, Math.ceil(measure(bandLabel, `700 ${bandSize}px ${FONT_STACK}`)) + 110));
  const score = Math.max(0, Math.min(100, Number(result.score) || 0));

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD_WIDTH}" height="${CARD_HEIGHT}" viewBox="0 0 ${CARD_WIDTH} ${CARD_HEIGHT}" xml:lang="${escapeXml(result.lang === 'hinglish' ? 'hi-Latn' : result.lang || 'en')}">
    <rect width="1080" height="1350" fill="#f6f7f5"/>
    <rect x="48" y="48" width="984" height="1254" rx="32" fill="#ffffff" stroke="#d9dfda" stroke-width="3"/>
    <rect x="48" y="48" width="984" height="20" rx="10" fill="${colors.accent}"/>
    <text x="92" y="154" class="brand">Check Before You Pay</text>
    <rect x="92" y="205" width="${pillWidth}" height="68" rx="34" fill="${colors.pale}"/>
    <circle cx="130" cy="239" r="11" fill="${colors.accent}"/>
    <text x="158" y="250" class="band" font-size="${bandSize}" fill="${colors.ink}">${escapeXml(bandLabel)}</text>
    <text x="92" y="480" class="score" fill="${colors.ink}">${score}<tspan class="outof"> / 100</tspan></text>
    <text x="92" y="554" class="caption">${escapeXml(labels.riskScore)}</text>
    ${headlineMarkup}
    <line x1="92" y1="1110" x2="988" y2="1110" stroke="#d9dfda" stroke-width="3"/>
    ${lineMarkup(wrapToWidth(labels.footer, `30px ${FONT_STACK}`, TEXT_WIDTH, 1), 92, 1172, 40, 'footer')}
    <text x="92" y="1234" class="url">${escapeXml(location.host)}</text>
    <style>
      text { font-family: ${FONT_STACK}; }
      .brand { font-size: 38px; font-weight: 700; fill: #16201b; }
      .band { font-weight: 700; }
      .score { font-size: 170px; font-weight: 800; }
      .outof { font-size: 52px; font-weight: 600; fill: #5b675f; }
      .caption { font-size: 28px; fill: #5b675f; }
      .headline { font-size: ${headSize}px; font-weight: 700; fill: #16201b; }
      .footer { font-size: 30px; fill: #344054; }
      .url { font-size: 26px; fill: #5b675f; }
    </style>
  </svg>`;
}

function toPng(svg) {
  return new Promise((resolve, reject) => {
    const svgUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(svgUrl);
      const canvas = document.createElement('canvas');
      canvas.width = CARD_WIDTH;
      canvas.height = CARD_HEIGHT;
      const context = canvas.getContext('2d');
      if (!context) return reject(new Error('Canvas is unavailable.'));
      context.drawImage(image, 0, 0, CARD_WIDTH, CARD_HEIGHT);
      canvas.toBlob((blob) => {
        if (blob) resolve(new File([blob], 'check-before-you-pay.png', { type: 'image/png' }));
        else reject(new Error('Could not render the share card.'));
      }, 'image/png');
    };
    image.onerror = () => {
      URL.revokeObjectURL(svgUrl);
      reject(new Error('Could not render the share card.'));
    };
    image.src = svgUrl;
  });
}

// The no-signals headline already says it doesn't prove the message is genuine (backend/language.py), so the card
// adds no second disclaimer.
export async function createShareCard(result, bandLabel, labels = { riskScore: 'Risk score', footer: 'Check evidence before you pay.' }) {
  return toPng(cardSvg(result, bandLabel, labels));
}
