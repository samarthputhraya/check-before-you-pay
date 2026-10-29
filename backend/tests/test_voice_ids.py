"""Voice notes dictate payment IDs. Spelled-out IDs after a known UPI handle become written IDs the fixed checks can
read; ordinary speech ("pay at Paytm", "meet at SBI") stays exactly as said."""
from __future__ import annotations

import pytest

from backend.extraction import regex_extract, written_ids


@pytest.mark.parametrize(('spoken', 'upi'), [
    ('UPI ID hai stockpro dot desk at ybl, abhi bhejiye', 'stockpro.desk@ybl'),
    ('deposit 25,000 to elite.desk at okaxis to activate', 'elite.desk@okaxis'),
    ('send it to elite dot desk at OKAXIS today', 'elite.desk@okaxis'),
    ('9876543210 at paytm par bhej do', '9876543210@paytm'),
    ('stockpro डॉट desk एट ybl पर भेजें', 'stockpro.desk@ybl'),
    ('pay to sharma.trades at validhdfc', 'sharma.trades@validhdfc'),
])
def test_dictated_ids_are_written_out(spoken, upi):
    assert regex_extract(written_ids(spoken)).entities.upi_ids == [upi]


@pytest.mark.parametrize('speech', [
    'You can pay at Paytm or at the counter',
    'Meet me at SBI near the station',
    'The rate was 5.5 at sbi last year',
    'We will talk at 5 at upi office',
    # review, 29 Oct: a full stop ends a sentence; it doesn't join a name to the next word
    'Mr. Sharma at ICICI said the mutual fund payment is due',
    'Okay. Meet at SBI tomorrow for the demat payment',
    'Rs. 5000 at paytm bhej do for the SIP',
    'Dr. Mehta at Airtel will call you',
    'St. Xavier at SBI branch',
])

def test_ordinary_speech_is_left_alone(speech):
    assert written_ids(speech) == speech


def test_typed_ids_are_unchanged():
    text = 'Pay to stockpro.desk@ybl now'
    assert written_ids(text) == text



def test_long_input_is_linear():
    import time
    text = 'ab. ' * 5000 + 'at ybl'
    started = time.perf_counter()
    written_ids(text)
    assert time.perf_counter() - started < 0.5
