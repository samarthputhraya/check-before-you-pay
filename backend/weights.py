"""Brief section 6. Changes require team agreement and updated tests."""
S1 = 35
S2 = 30
S3_NEW = 25
S3_RECENT = 10
S4_PER_TYPE = 10
S4_CAP = 30
S5 = 15
S6_CAP = 30
S7 = 40
SCRIPT_SIMILARITY = 0.90
CLAIMS = {
    'guaranteed_returns': 10, 'vip_or_institutional_account': 10,
    'ipo_allotment': 10, 'install_app_or_apk': 10, 'withdrawal_fee': 10,
    'urgency_pressure': 5, 'sebi_registered_claim': 5,
    # Added 29 Oct from the eval misses (docs/EVAL.md): sure-shot tips, pay-to-unlock tasks, pay-to-recover fees.
    'insider_tip': 10, 'task_deposit': 10, 'recovery_fee': 10,
}
