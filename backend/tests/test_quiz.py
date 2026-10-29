"""'Spot the scam' quiz: content gates, server scoring, stored results and the share loop it feeds."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import app as app_module, db, quiz as quizzes
from backend.config import EXAMPLES_DIR
from backend.schemas import QuizAnswerResponse, QuizResponse

FILES = sorted(quizzes.QUIZ_DIR.glob('*.json'))
SETS = {file.stem: quizzes.QuizSet.model_validate_json(file.read_bytes()) for file in FILES}
# Words we never use in our own voice (BUILD_BRIEF section 13): "safe" in any form, and calling anyone a
# fraud or scammer, in every language we write.
BANNED = re.compile(r'safe|scammer|fraud|सुरक्षित|सेफ|धोखाधड़ी|धोखेबाज|ठग|जालसाज|फ्रॉड|फ़्रॉड|फसवणूक|भामट|'
                    r'thag|dhokebaaz|dhokhebaaz', re.IGNORECASE)


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'test.db'))
    monkeypatch.delenv('PUBLIC_BASE_URL', raising=False)
    return TestClient(app_module.app)


def correct_answers(lang: str = 'en') -> dict[str, str]:
    return {item.id: item.answer for item in SETS[lang].items}


def submit(client: TestClient, answers: dict, quiz_id: str = 'q_en_v1', anon_id: str = 'u_player'):
    return client.post('/api/quiz/answer', json={'quiz_id': quiz_id, 'anon_id': anon_id, 'answers': answers})


def rows(tmp_path, sql: str, *args) -> list[sqlite3.Row]:
    with db.session(tmp_path / 'test.db') as con:
        return con.execute(sql, args).fetchall()


# ---- content -------------------------------------------------------------------

def test_every_language_has_a_validated_set_of_ten():
    assert set(SETS) == {'en', 'hi', 'mr', 'hinglish'}
    for lang, quiz in SETS.items():
        assert quiz.lang == lang and quiz.quiz_id == f'q_{lang}_v1'
        assert quiz.source_note == 'Examples written by us from real scam patterns (SEBI, I4C advisories)'
        answers = [item.answer for item in quiz.items]
        assert len(answers) == 10 and answers.count('scam') == 6
        assert len({item.id for item in quiz.items}) == 10
        # Mixed, never a pattern a player can learn: no strict alternation and no long runs.
        assert any(a == b for a, b in zip(answers, answers[1:]))
        assert max(len(run) for run in re.findall(r'S+|G+', ''.join(a[0].upper() for a in answers))) <= 3
        assert Counter(item.difficulty for item in quiz.items) == {'easy': 3, 'medium': 4, 'hard': 3}
        assert '{score}' not in quiz.title(8, 10) and '8/10' in quiz.title(8, 10)


def test_the_bank_loads_every_file_once():
    assert set(quizzes.bank().by_id) == {f'q_{lang}_v1' for lang in SETS}
    assert quizzes.bank() is quizzes.bank()


def test_no_why_says_safe_or_calls_anyone_a_fraud():
    for lang, quiz in SETS.items():
        for item in quiz.items:
            assert not BANNED.search(item.why), (lang, item.id, BANNED.search(item.why).group())


def test_identifiers_in_messages_are_masked_or_made_up():
    for quiz in SETS.values():
        for item in quiz.items:
            assert not re.search(r'(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)', item.text), item.id  # phones are masked
            if '@valid' in item.text:
                assert item.answer == 'genuine', item.id  # only genuine items pay to a @valid handle


@pytest.mark.parametrize('change, problem', [
    (lambda d: d['items'][1].update(id=d['items'][0]['id']), 'unique'),
    (lambda d: [i.update(answer='scam') for i in d['items']], 'both'),
    (lambda d: d['items'][0].update(leak='extra field'), 'extra'),
    (lambda d: d.update(card_title='I spotted {score}. Can you?'), 'card_title'),
    (lambda d: d.update(quiz_id='q_hi_v1'), 'lang'),
    (lambda d: d.update(source_note='Real messages'), 'source note'),
])
def test_bad_content_fails_at_load(change, problem):
    data = json.loads(FILES[0].read_text(encoding='utf-8'))
    change(data)
    with pytest.raises(ValidationError):
        quizzes.QuizSet.model_validate(data)


# ---- GET /api/quiz ------------------------------------------------------------------

@pytest.mark.parametrize('lang', ['en', 'hi', 'mr', 'hinglish'])
def test_each_language_gets_its_own_messages_and_no_answers(client, lang):
    resp = client.get(f'/api/quiz?lang={lang}')
    assert resp.status_code == 200 and 'X-Sample' not in resp.headers
    body = resp.json()
    QuizResponse.model_validate(body)
    assert body['quiz_id'] == f'q_{lang}_v1'
    assert [item['text'] for item in body['items']] == [item.text for item in SETS[lang].items]
    for item in body['items']:
        assert set(item) == {'id', 'text', 'image_url'}
    for item in SETS[lang].items:  # neither the answer nor the explanation reaches the page early
        assert item.why not in resp.text
    assert '"answer"' not in resp.text and '"why"' not in resp.text


@pytest.mark.parametrize('lang', ['ta', 'te', 'kn', 'bn'])
def test_languages_without_a_set_fall_back_to_english(client, lang):
    body = client.get(f'/api/quiz?lang={lang}').json()
    assert body['quiz_id'] == 'q_en_v1'
    assert body['items'][0]['text'] == SETS['en'].items[0].text


def test_example_files_match_what_the_server_returns(client):
    example = lambda name: json.loads((EXAMPLES_DIR / f'{name}.json').read_text(encoding='utf-8'))
    assert client.get('/api/quiz?lang=hi').json() == example('quiz_response')
    body = client.post('/api/quiz/answer', json=example('quiz_answer_request')).json()
    body['share']['url'] = body['share']['url'].replace('http://testserver', 'https://<host>')
    assert body == example('quiz_answer_response')


# ---- POST /api/quiz/answer -----------------------------------------------------------

def test_perfect_score(client):
    resp = submit(client, correct_answers())
    assert resp.status_code == 200 and 'X-Sample' not in resp.headers
    body = QuizAnswerResponse.model_validate(resp.json())
    assert (body.score, body.total) == (10, 10)
    assert all(result.correct for result in body.results)
    assert body.share.url == 'http://testserver/quiz?ref=u_player'
    assert body.share.card_title == 'I spotted 10/10. Can you?'


def test_one_wrong_answer_lowers_the_score_and_shows_the_right_one(client):
    answers = correct_answers('hi')
    first = SETS['hi'].items[0]
    answers[first.id] = 'genuine' if first.answer == 'scam' else 'scam'
    body = submit(client, answers, 'q_hi_v1').json()
    assert (body['score'], body['total']) == (9, 10)
    assert body['share']['card_title'] == 'मैंने 9/10 पहचाने। क्या आप पहचान सकते हैं?'
    # Every item in quiz order; `answer` is the correct one, which Quiz.js shows beside the player's choice.
    assert [r['id'] for r in body['results']] == [item.id for item in SETS['hi'].items]
    assert body['results'][0] == {'id': first.id, 'correct': False, 'answer': first.answer, 'why': first.why}


def test_empty_and_unknown_answers_count_as_wrong(client):
    body = submit(client, {}).json()
    assert (body['score'], body['total']) == (0, 10) and len(body['results']) == 10
    partial = {'q1': SETS['en'].items[0].answer, 'q99': 'scam', 'x': 'genuine'}
    assert submit(client, partial).json()['score'] == 1


@pytest.mark.parametrize('quiz_id', ['q_xx_v1', 'q_en_v9', 'q_ta_v1'])
def test_unknown_quiz_is_a_400(client, quiz_id, tmp_path):
    resp = submit(client, correct_answers(), quiz_id)
    assert resp.status_code == 400 and resp.json()['error']['code'] == 'invalid_request'
    assert rows(tmp_path, 'SELECT * FROM quiz_results') == []


def test_answering_stores_a_result_and_a_server_quiz_done(client, tmp_path):
    answers = correct_answers('mr')
    answers['q1'] = 'scam'  # mr q1 is genuine
    assert submit(client, answers, 'q_mr_v1').json()['score'] == 9
    [result] = rows(tmp_path, 'SELECT anon_id,quiz_id,score FROM quiz_results')
    assert tuple(result) == ('u_player', 'q_mr_v1', 9)
    [done] = rows(tmp_path, "SELECT anon_id,props_json FROM events WHERE event='quiz_done'")
    assert done['anon_id'] == 'u_player' and json.loads(done['props_json']) == {'score': 9, 'lang': 'mr'}
    # A client's own quiz_done is ignored, so the count can't be inflated from the browser.
    assert client.post('/api/events', json={'anon_id': 'u_player', 'event': 'quiz_done'}).status_code == 204
    assert len(rows(tmp_path, "SELECT 1 FROM events WHERE event='quiz_done'")) == 1


def test_a_quiz_share_counts_toward_k_factor(client, tmp_path):
    submit(client, correct_answers(), anon_id='u_sharer')
    assert client.post('/api/events', json={'anon_id': 'u_sharer', 'event': 'quiz_shared'}).status_code == 204
    assert len(rows(tmp_path, "SELECT 1 FROM events WHERE event='quiz_shared'")) == 1
    friend = TestClient(app_module.app)  # a new browser, opening the shared /quiz?ref= link
    friend.post('/api/events', json={'anon_id': 'u_friend', 'event': 'visit', 'ref': 'u_sharer'})
    stats = client.get('/api/stats').json()
    assert stats['k_factor'] == 1 and stats['quiz_plays'] == 1 and stats['users'] == 2


def test_a_quiz_share_without_a_quiz_result_is_ignored(client, tmp_path):
    # This user holds a valid share proof (from a check) but never finished a quiz.
    check = client.post('/api/check', json={'lang': 'en', 'anon_id': 'u_lurker', 'input': {'text': 'Pay sample@ybl'}})
    assert check.status_code == 200
    assert client.post('/api/events', json={'anon_id': 'u_lurker', 'event': 'quiz_shared'}).status_code == 204
    # And one with a quiz result but no proof cookie (a script, not the browser that played).
    submit(TestClient(app_module.app), correct_answers(), anon_id='u_scripted')
    bare = TestClient(app_module.app)
    assert bare.post('/api/events', json={'anon_id': 'u_scripted', 'event': 'quiz_shared'}).status_code == 204
    assert rows(tmp_path, "SELECT 1 FROM events WHERE event='quiz_shared'") == []
    assert client.get('/api/stats').json()['k_factor'] == 0


def test_quiz_plays_counts_every_finished_quiz(client):
    assert client.get('/api/stats').json()['quiz_plays'] == 0
    submit(client, {}, anon_id='u_one')
    submit(client, correct_answers('hinglish'), 'q_hinglish_v1', anon_id='u_one')
    submit(client, correct_answers(), anon_id='u_two')
    assert client.get('/api/stats').json()['quiz_plays'] == 3


def test_answers_are_rate_limited_per_user(client):
    for _ in range(30):
        assert submit(client, {}).status_code == 200
    resp = submit(client, {})
    assert resp.status_code == 429 and resp.json()['error']['code'] == 'rate_limited'
    assert 'quiz' in resp.json()['error']['message']
    assert submit(client, {}, anon_id='u_other').status_code == 200


def test_answers_are_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setenv('IP_QUIZ_PER_HOUR', '2')
    assert submit(client, {}, anon_id='u_a').status_code == 200
    assert submit(client, {}, anon_id='u_b').status_code == 200
    assert submit(client, {}, anon_id='u_c').status_code == 429


def test_the_score_still_returns_when_the_database_is_down(client, monkeypatch):
    def down(*args):
        raise sqlite3.OperationalError('disk I/O error')
    monkeypatch.setattr(db, 'save_quiz_result', down)
    body = submit(client, correct_answers()).json()
    assert body['score'] == 10 and body['total'] == 10
