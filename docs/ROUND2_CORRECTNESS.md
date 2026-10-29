# Refunds, negative domain lookups and sample-data guard

Refunds use the payment ID, not refund metadata. Verified payment events save a
mode-scoped payment-to-order link even if a subscription event marked the order
paid first. A verified `refund.succeeded` marks that paid order refunded. A
refund delivered first is retained and reconciled when its payment arrives.
Late success/failure events cannot restore a refunded order. The paid-order
statistic excludes all successful refunds, including partial refunds, following
the Round 2 requirement; this is an order count, not net revenue accounting.

Existing orders whose `dodo_ref` is a payment ID also reconcile directly. For an
older order whose only reference is a subscription ID, replay its verified
`payment.succeeded` event to establish the payment link (a verified duplicate
can backfill this link without counting another payment). No raw payment/customer
payload is retained. A cancellation is recorded
once in the signed-webhook ledger without reclassifying a historical payment.

RDAP 404 from the configured registry returns a successful negative lookup,
cached for one hour. It adds localized S3 evidence with **zero points**, after
scoring and explanation. Timeout, 429 and server errors remain unchecked.
`backend/signals.py` and `backend/weights.py` are unchanged.

The sample guard scans text in every `examples/` and `seed/` file, including
individual JSON values, for phone/UPI-shaped identifiers without `(sample)` in
that text. It reports locations only. All quiz messages are labelled consistently
so the label does not reveal which answer is correct. This is a shape check;
human redaction and consent review still apply to real collection and binary
media. A sample label is never permission to publish a real person's identifier.

Sources: [Dodo's refund schema](https://github.com/dodopayments/dodopayments-python/blob/main/src/dodopayments/types/refund.py),
[payment schema](https://github.com/dodopayments/dodopayments-python/blob/main/src/dodopayments/types/payment.py),
[RDAP negative answers, RFC 7480 section 5.3](https://www.rfc-editor.org/rfc/rfc7480#section-5.3).
