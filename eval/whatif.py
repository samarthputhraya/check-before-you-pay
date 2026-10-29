"""Re-score saved eval results under alternative weights, without calling the model again.

S1, S2, S3 and S7 keep the points the run recorded (S1 re-weighted). S6 is rebuilt from the verified claims the run
saved, with the same rules as backend/signals.py: one claim per type, ipo_allotment grouped with
vip_or_institutional_account, a SEBI claim with a registration number scores nothing, and the total is capped.

    python eval/whatif.py eval/results_v2.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = {'guaranteed_returns': 10, 'vip_or_institutional_account': 10, 'ipo_allotment': 10, 'install_app_or_apk': 10,
        'withdrawal_fee': 10, 'urgency_pressure': 5, 'sebi_registered_claim': 5,
        'insider_tip': 10, 'task_deposit': 10, 'recovery_fee': 10}
CONFIGS = {
    'now (S1 35)': dict(s1=35, claims={}, cap=30),
    'S1 50': dict(s1=50, claims={}, cap=30),
    'S1 50, guarantee 20, cap 40': dict(s1=50, claims={'guaranteed_returns': 20}, cap=40),
    'S1 45, guarantee 20, cap 40': dict(s1=45, claims={'guaranteed_returns': 20}, cap=40),
    'S1 50, guarantee+withdrawal+task 20, cap 40': dict(
        s1=50, claims={'guaranteed_returns': 20, 'withdrawal_fee': 20, 'task_deposit': 20}, cap=40),
    'S1 50, five scam-only claims 30 each, cap 40': dict(
        s1=50, claims={k: 30 for k in ('guaranteed_returns', 'withdrawal_fee', 'task_deposit', 'insider_tip',
                                       'recovery_fee')}, cap=40),
    'S1 45, five scam-only claims 30 each, cap 40': dict(
        s1=45, claims={k: 30 for k in ('guaranteed_returns', 'withdrawal_fee', 'task_deposit', 'insider_tip',
                                       'recovery_fee')}, cap=40),
}


def s6(row: dict, claims: dict, cap: int) -> int:
    weights = {**BASE, **claims}
    seen, total = set(), 0
    has_reg = bool(row['extraction']['entities'].get('sebi_reg_numbers'))
    for claim in row['extraction']['claims']:
        group = 'vip_or_institutional_account' if claim['type'] == 'ipo_allotment' else claim['type']
        if group not in weights or group in seen or (group == 'sebi_registered_claim' and has_reg):
            continue
        seen.add(group)
        total += weights[group]
    return min(cap, total)


def band(score: int) -> str:
    return 'high_risk' if score >= 60 else 'caution' if score >= 30 else 'no_known_signals'


def rescore(row: dict, s1: int, claims: dict, cap: int) -> int:
    points = sum(s['points'] for s in row['signals'] if s['id'] not in ('S1', 'S6'))
    points += s1 if any(s['id'] == 'S1' for s in row['signals']) else 0
    points += s6(row, claims, cap) if row.get('extraction') else next(
        (s['points'] for s in row['signals'] if s['id'] == 'S6'), 0)
    return max(0, min(100, points))


def table(path: Path) -> None:
    rows = json.loads(path.read_text(encoding='utf-8'))['results']
    scams = [r for r in rows if r['label'] == 'scam']
    ordinary = [r for r in rows if r['label'] == 'ordinary']
    print(f'{path.name}: {len(scams)} scam, {len(ordinary)} ordinary')
    print(f"{'weights':46s} | scam high / caution / missed | flagged | ordinary caution / high")
    for name, cfg in CONFIGS.items():
        sb = [band(rescore(r, **cfg)) for r in scams]
        ob = [band(rescore(r, **cfg)) for r in ordinary]
        flagged = sum(b != 'no_known_signals' for b in sb)
        print(f"{name:46s} | {sb.count('high_risk'):4d} / {sb.count('caution'):4d} / {sb.count('no_known_signals'):4d}"
              f"     | {flagged:3d}/{len(scams)} | {ob.count('caution'):4d} / {ob.count('high_risk'):4d}")


if __name__ == '__main__':
    for arg in sys.argv[1:] or ['eval/results_v2.json']:
        table(Path(arg))
