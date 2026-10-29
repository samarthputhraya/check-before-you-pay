"""Brief section 6. Changes require team agreement and updated tests.

v2, 29 Oct (measured in docs/EVAL.md): S1 35 -> 50, five scam-only claims 10 -> 30, S6 cap 30 -> 40.
- A personal UPI ID for an investment, plus any claim, is now high risk; S1 alone stays at caution.
- Each of the five claims below is a sign of fraud on its own (SEBI: nobody can guarantee returns), so one verified
  quote reaches caution. Claims alone are capped at 40, so a high-risk verdict always needs a checked fact too:
  the UPI handle, a look-alike or new domain, or a link to earlier reports.
"""
S1 = 50
S2 = 30
S3_NEW = 25
S3_RECENT = 10
S4_PER_TYPE = 10
S4_CAP = 30
S5 = 15
S6_CAP = 40
S7 = 40
SCRIPT_SIMILARITY = 0.90
CLAIMS = {
    'guaranteed_returns': 30, 'withdrawal_fee': 30, 'task_deposit': 30, 'insider_tip': 30, 'recovery_fee': 30,
    'vip_or_institutional_account': 10, 'ipo_allotment': 10, 'install_app_or_apk': 10,
    'urgency_pressure': 5, 'sebi_registered_claim': 5,
}
