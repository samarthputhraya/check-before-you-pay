const CARD_WIDTH = 1080;
const CARD_HEIGHT = 1350;
const FONT_STACK = 'system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Noto Sans Devanagari, Noto Sans Tamil, Noto Sans Telugu, Noto Sans Kannada, Noto Sans Bengali, sans-serif';

function escapeXml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;',
  })[char]);
}

function wrapWords(value, maxChars = 25, maxLines = 4) {
  const words = String(value || '').trim().split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length > maxChars && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
    if (lines.length === maxLines) break;
  }
  if (line && lines.length < maxLines) lines.push(line);
  if (words.join(' ').length > lines.join(' ').length && lines.length) {
    lines[lines.length - 1] = `${lines[lines.length - 1].replace(/[.…]+$/, '')}…`;
  }
  return lines;
}

function lineMarkup(lines, x, y, lineHeight, className) {
  return lines.map((line, index) =>
    `<text class="${className}" x="${x}" y="${y + index * lineHeight}">${escapeXml(line)}</text>`,
  ).join('');
}

function cardSvg(result, bandLabel, noProof) {
  const colors = {
    high_risk: { ink: '#9d1c14', pale: '#fdecea', accent: '#b42318' },
    caution: { ink: '#854000', pale: '#fff3e0', accent: '#a64b00' },
    no_known_signals: { ink: '#344054', pale: '#f0f2f1', accent: '#667085' },
  }[result.band] || { ink: '#344054', pale: '#f0f2f1', accent: '#667085' };
  const headlineLines = wrapWords(result.headline, 25, 4);
  const headlineMarkup = lineMarkup(headlineLines, 92, 620, 78, 'headline');
  const disclaimerLines = result.band === 'no_known_signals' ? wrapWords(noProof, 48, 2) : [];
  const disclaimerMarkup = lineMarkup(disclaimerLines, 92, 994, 42, 'disclaimer');
  const score = Math.max(0, Math.min(100, Number(result.score) || 0));

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD_WIDTH}" height="${CARD_HEIGHT}" viewBox="0 0 ${CARD_WIDTH} ${CARD_HEIGHT}" xml:lang="${escapeXml(result.lang || 'en')}">
    <rect width="1080" height="1350" fill="#f6f7f5"/>
    <rect x="48" y="48" width="984" height="1254" rx="32" fill="#ffffff" stroke="#d9dfda" stroke-width="3"/>
    <rect x="48" y="48" width="984" height="20" rx="10" fill="${colors.accent}"/>
    <text x="92" y="154" class="brand">Check Before You Pay</text>
    <rect x="92" y="205" width="420" height="68" rx="34" fill="${colors.pale}"/>
    <circle cx="130" cy="239" r="11" fill="${colors.accent}"/>
    <text x="158" y="252" class="band" fill="${colors.ink}">${escapeXml(bandLabel)}</text>
    <text x="92" y="480" class="score" fill="${colors.ink}">${score}<tspan class="outof"> / 100</tspan></text>
    <text x="92" y="554" class="caption">Risk score</text>
    ${headlineMarkup}
    ${disclaimerMarkup}
    <line x1="92" y1="1110" x2="988" y2="1110" stroke="#d9dfda" stroke-width="3"/>
    <text x="92" y="1172" class="footer">Check evidence before you pay.</text>
    <text x="92" y="1234" class="url">${escapeXml(location.host)}</text>
    <style>
      text { font-family: ${FONT_STACK}; }
      .brand { font-size: 38px; font-weight: 700; fill: #16201b; }
      .band { font-size: 30px; font-weight: 700; }
      .score { font-size: 170px; font-weight: 800; }
      .outof { font-size: 52px; font-weight: 600; fill: #5b675f; }
      .caption { font-size: 28px; fill: #5b675f; }
      .headline { font-size: 54px; font-weight: 700; fill: #16201b; }
      .disclaimer { font-size: 27px; fill: #344054; }
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

export async function createShareCard(result, bandLabel, noProof) {
  return toPng(cardSvg(result, bandLabel, noProof));
}
