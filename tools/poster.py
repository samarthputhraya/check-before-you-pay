"""Print poster (A4) with a QR code for the house, the demo stage and slides.

    python tools/poster.py            # -> docs/poster.pdf and docs/poster.png

The QR opens the live site with ?ref=u_qr_poster, so scans show up as ref_visit events. Needs qrcode and Playwright
with Chrome.
"""
import base64
import io
from pathlib import Path

import qrcode
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://34-45-129-243.sslip.io/?ref=u_qr_poster'

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=20, border=2)
qr.add_data(URL)
qr.make(fit=True)
buf = io.BytesIO()
qr.make_image(fill_color='#0b3d24', back_color='white').save(buf, format='PNG')
QR = base64.b64encode(buf.getvalue()).decode()
ICON = (ROOT / 'web' / 'icon.svg').read_text(encoding='utf-8')

PAGE = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Segoe UI", "Nirmala UI", Arial, sans-serif; color: #1b1f24; }}
.sheet {{ width: 210mm; height: 297mm; padding: 16mm 16mm 14mm; display: flex; flex-direction: column; }}
.brand {{ display: flex; align-items: center; gap: 5mm; font-size: 9mm; font-weight: 700; }}
.brand svg {{ width: 15mm; height: 15mm; }}
h1 {{ font-size: 15mm; line-height: 1.08; margin: 12mm 0 4mm; letter-spacing: -0.3mm; }}
.hi {{ font-size: 10mm; color: #0b6839; font-weight: 700; margin: 0 0 8mm; }}
.lead {{ font-size: 6.2mm; line-height: 1.45; color: #39414c; margin: 0 0 8mm; }}
.row {{ display: flex; gap: 10mm; align-items: center; }}
.qr {{ width: 82mm; height: 82mm; border: 1.2mm solid #0b6839; border-radius: 6mm; padding: 2mm; background: #fff; }}
.qr img {{ width: 100%; height: 100%; image-rendering: pixelated; }}
.steps {{ font-size: 6mm; line-height: 1.5; margin: 0; padding-left: 7mm; }}
.steps li {{ margin-bottom: 3mm; }}
.steps b {{ color: #0b6839; }}
.langs {{ margin-top: 9mm; font-size: 5.4mm; color: #5b6470; }}
.foot {{ margin-top: auto; border-top: 0.6mm solid #dfe3e8; padding-top: 5mm; font-size: 4.2mm; color: #5b6470;
         display: flex; justify-content: space-between; }}
.url {{ font-weight: 700; color: #1b1f24; white-space: nowrap; margin-right: 6mm; }}
</style></head><body><div class="sheet">
  <div class="brand">{ICON}Check Before You Pay</div>
  <h1>Got a "VIP stock tips" or<br>"guaranteed returns" message?</h1>
  <p class="hi">पैसे भेजने से पहले जाँचें</p>
  <p class="lead">Paste the message, a screenshot or a WhatsApp voice note. In about 3 seconds you see the red flags
    and the exact lines that gave it away, in your language. Free, no sign-up.</p>
  <div class="row">
    <div class="qr"><img src="data:image/png;base64,{QR}" alt="QR code"></div>
    <ol class="steps">
      <li><b>Scan</b> the code with your phone camera.</li>
      <li><b>Paste</b> the message or add a screenshot.</li>
      <li><b>Send the verdict</b> to your family group in one tap.</li>
    </ol>
  </div>
  <p class="langs">English · हिन्दी · Hinglish · मराठी · தமிழ் · తెలుగు · ಕನ್ನಡ · বাংলা</p>
  <div class="foot"><span class="url">34-45-129-243.sslip.io</span>
    <span>An independent tool, not run by SEBI, NPCI or any bank. Lost money? Call 1930.</span></div>
</div></body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    pg = b.new_page(viewport={'width': 794, 'height': 1123}, device_scale_factor=2)
    pg.set_content(PAGE)
    pg.pdf(path=str(ROOT / 'docs' / 'poster.pdf'), format='A4', print_background=True)
    pg.screenshot(path=str(ROOT / 'docs' / 'poster.png'), full_page=True)
    b.close()
print('docs/poster.pdf, docs/poster.png ->', URL)
