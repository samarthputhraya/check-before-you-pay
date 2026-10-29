"""S1 wording: real tip-group payment requests in 8 languages get S1; ordinary bills, fees, shop names and family
payments don't. Every message here came from one of three independent reviews on 29 Oct."""
from __future__ import annotations

import pytest

from backend.extraction import Claim, Extraction, regex_extract, verified_extraction
from backend.signals import evaluate


@pytest.mark.parametrize(('text', 'upi'), [
    ('Invest in our stock tips group. Pay ₹10,000 to stockpro@ybl.', 'stockpro@ybl'),
    ('UPI: rk.sharma@okaxis.', 'rk.sharma@okaxis'),
    ('Send it to 9876543210@ybl.', '9876543210@ybl'),
    ('Pay rahul.sharma@okaxis.Thanks', 'rahul.sharma@okaxis'),
    ('rk@ybl.धन्यवाद', 'rk@ybl'),
])
def test_upi_id_at_the_end_of_a_sentence_is_found(text, upi):
    assert regex_extract(text).entities.upi_ids == [upi]


@pytest.mark.parametrize('text', ['Write to rk@gmail.com for details', 'Write to rk@gmail.com.'])
def test_email_address_is_not_a_upi_id(text):
    assert regex_extract(text).entities.upi_ids == []


@pytest.mark.parametrize('text', ['Pay to tradepro.vip@ybl now', 'Pay rahul.sharma@okaxis today',
                                  'Pay to stock.guru.in@ybl', 'trade.pro.vip@ybl now', 'tradepro.vip.1@ybl'])
def test_upi_name_is_never_read_as_a_website(text):
    assert regex_extract(text).entities.domains == []


def test_real_website_at_the_end_of_a_sentence_is_still_found():
    assert regex_extract('Download from kite-zerodha-app.in.').entities.domains == ['kite-zerodha-app.in']


@pytest.mark.parametrize('text', [
    'Invest in our stock tips group. Pay ₹10,000 to stockpro@ybl.',
    'स्टॉक मार्केट टिप्स: रोज़ 5% मुनाफ़ा। rk.sharma@ybl पर भेजें',
    'हर महीने 30% गारंटीड रिटर्न। rk.sharma@ybl पर 5000 भेजें',
    'Daily 5% profit guaranteed in crypto. Deposit 10000 to rk.sharma@ybl',
    'Bank Nifty option tips. Pay 4999 to rk.sharma@ybl',
    'Forex signals group. Pay 2999 to rk.sharma@ybl to join',
])
def test_tip_group_payment_requests_get_s1(text):
    assert 'S1' in [s.id for s in evaluate(text, regex_extract(text), {})]


@pytest.mark.parametrize('text', [
    'Please pay 500 to shop@ybl for the groceries and return the bag',
    'Send 1000 to help@ybl for our non-profit food drive',
    # second review: ordinary bills, fees and family messages the first widening scored as investment
    'Your bill from Gupta Traders is 1,240. Please pay to guptatraders@okaxis.',
    'Electricity bill 2,310. Pay to msedcl.bill@okicici. Late fee 2% per month after the due date',
    'Society maintenance due, 1.5% per month interest after the 10th. Pay to society@ybl',
    'Donate to our not-for-profit animal shelter: send 500 to pawsshelter@sbi',
    'Pay your CA 1500 for the GST monthly return to ca.office@ybl',
    'Mangoes 100% guaranteed fresh, pay 800 to fruits@ybl',
    'Photoshoot for your portfolio, pay advance 2000 to studio@ybl',
    'BSE Odisha exam form fee: pay 300 to school@ybl',
    'Pay 450 for the nifty little speaker to gadgets@ybl',
    'I made a small profit on the stall, send 200 to ravi@ybl',
    'Dukaan ka profit share 2000 bhej do ravi@ybl pe',
    'रिटर्न टिकट के 640 रुपये ravi@ybl पर भेज दो',
    'रिटर्न गिफ्ट के लिए 300 रुपये ravi@ybl पर भेजो',
    'दुकान का स्टॉक आ गया, 5000 supplier@ybl पर भेज दो',
    'यह मैसेज शेयर करें और 100 रुपये ravi@ybl पर भेजें',
    'অলাভজনক সংস্থায় 500 টাকা পাঠান help@ybl',
])
def test_ordinary_payments_get_no_s1(text):
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]


def test_verified_investment_claim_gives_s1_context():
    text = 'Join our VIP club. Pay 5000 to club@ybl'
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]
    claimed = verified_extraction(Extraction(claims=[Claim(type='vip_or_institutional_account', quote='VIP club')]), text)
    assert 'S1' in [s.id for s in evaluate(text, claimed, {})]


@pytest.mark.parametrize('text', [
    'Join our premium stock group. Get 10% weekly returns. Pay Rs 25,000 to vipadvisory@ybl to activate your account',
    'Earn 3% daily on USDT. Send 10000 to usdt.desk@ybl',
    'Hamare VIP group me 20% monthly munafa pakka. 5000 bhejo vip@ybl',
    'Trading account kholne ke liye 10000 jama karein tradedesk@ybl',
    'शेयर बाजार में निवेश करें, 10000 रुपये invest@ybl पर भेजें',
    'शेअर मार्केट मध्ये गुंतवणूक करा, 5000 पाठवा abc@ybl',
    'பங்குச் சந்தை டிப்ஸ், 5000 செலுத்து abc@ybl',
    'Multibagger penny stock call! Pay 2999 to calls@ybl for the premium list',
])
def test_more_tip_group_wordings_get_s1(text):
    assert 'S1' in [s.id for s in evaluate(text, regex_extract(text), {})]


@pytest.mark.parametrize('text', [
    # third review: shop names, property brokers, hospital tests, first names and UPI names are not investing
    'Your bill from Shree Ganesh Trading Co. is Rs 4,500. Please pay to ganeshtrading@okaxis',
    'Mahalaxmi Trading Company: invoice 2231, amount 12,400. Kindly pay to mahalaxmi.trading@okicici',
    'Gupta Trading Co ka bill 3200 hai, guptatrading@ybl pe bhej dena',
    'शर्मा ट्रेडिंग कंपनी का बिल 4500 रुपये, sharmatrading@ybl पर भेज दें',
    'সাহা ট্রেডিং কোম্পানির বিল 3000 টাকা saha@ybl তে পাঠান',
    'Flat on rent 25k, brokerage one month. Pay token 5000 to rajesh.k@ybl to block the flat',
    'Hi, I am the property broker. Send the commission 15000 to sunil@okhdfcbank today',
    'City Hospital: investigation charges Rs 2,400 (CBC, LFT, X-ray). Please pay to cityhospital@okicici',
    'Send 2000 to Nivesh for the Goa trip, his UPI is nivesh.sharma@okaxis',
    'Load your forex card for the US trip: transfer 50000 to globetravels@okicici',
    '100% return policy within 7 days. Pay 1,200 for the kurta to fashionhub@ybl',
    'Shriram chit: this month dividend is 450, so pay 4550 to srirama.chits@ybl',
    'Surat stock lot sarees, buy stock at 40% off. Pay 5000 advance to suratsarees@ybl',
])
def test_third_review_ordinary_payments_get_no_s1(text):
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]


@pytest.mark.parametrize('text', [
    'Tomorrow this stock will hit upper circuit. Pay 2999 for membership to calls@ybl',
    'Earn 3% daily. Send 10000 to desk.official@ybl to start',
    'Returns guaranteed. Pay 10000 to growthplan@ybl',
    'Munafa pakka hai bhai, 5000 bhejo vip@ybl',
    'यह शेयर कल 40% ऊपर जाएगा, 5000 रुपये भेजें abc@ybl',
    'ட்ரேடிங் குழுவில் சேர 5000 abc@ybl க்கு செலுத்து',
    "Yesterday's call gave 18% in TATA MOTORS. Join premium membership, pay 4999 to equitycalls@ybl",
    'Deposit 20,000 in the app wallet to buy the allotted shares, pay to app.wallet@ybl',
])
def test_third_review_scam_wordings_get_s1(text):
    assert 'S1' in [s.id for s in evaluate(text, regex_extract(text), {})]


@pytest.mark.parametrize('text', ['Mail RK@GMAIL.COM today', 'Support@Zerodha.Com', 'HTTPS://USER@EXAMPLE.COM'])
def test_uppercase_email_is_not_a_upi_id(text):
    assert regex_extract(text).entities.upi_ids == []


def test_valid_handle_next_to_an_uppercase_email_gets_no_s1():
    text = 'Investment queries: SUPPORT@ZERODHA.COM. Pay only via zerodha.broker@validhdfc'
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]
