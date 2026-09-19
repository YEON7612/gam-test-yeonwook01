# -*- coding: utf-8 -*-
"""Gemini 촌평 — Vercel 서버리스 함수.

이 앱에서 서버가 필요한 유일한 자리다. **키를 숨기기 위해서** 존재한다.
키를 app.js 에 적으면 브라우저에서 그대로 보인다.

  받는 것   {"score": 62, "grade": "수습 딱지 뗌",
             "directions": ["맞힘", "높게", "틀림", "높게", "틀림"]}
  주는 것   {"comment": "...", "nickname": "..."}

**숫자를 보내지 않는다.** 방향만 보낸다 — 숫자를 주면 그 숫자로 새 숫자를
만들어낸다. 점수·등급·오차는 전부 브라우저가 이미 계산했다.

키가 없거나 호출이 실패하면 {"comment": null} 을 200 으로 돌려준다.
**앱은 촌평 없이도 그대로 돈다.**

외부 라이브러리를 쓰지 않는다 (requirements.txt 가 필요 없다).
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

# AI Studio(aistudio.google.com)에서 지금 쓸 수 있는 모델 이름으로 맞춘다.
# 모델 이름과 무료 한도는 자주 바뀐다 — 교안의 이름을 그대로 믿지 말 것.
MODEL = "gemini-3.6-flash"
ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/"
            "models/{model}:generateContent")
TIMEOUT = 6

PROMPT = """너는 직장 데이터 퀴즈 앱의 촌평 담당이다.

사용자가 방금 '입사 첫날 테스트'를 풀었다. 결과는 이렇다.

  점수: {score}점 ({grade})
  문항별로 어느 방향으로 빗나갔는지: {directions}

  '높게' = 실제보다 크게 잡음, '낮게' = 실제보다 작게 잡음,
  '비슷' = 거의 맞음, '맞힘'/'틀림' = 객관식

규칙
- 두 문장 이내로 짧게. 존댓말.
- **숫자를 새로 만들지 마라.** 위에 없는 수치를 쓰면 안 된다.
- 어느 방향으로 치우쳤는지를 짚고, 회사 생활에 빗대 가볍게 말한다.
- 비꼬거나 훈계하지 않는다. 읽고 웃을 수 있게.
- 마지막 줄에 별명을 하나 붙인다. 6글자 이내.

형식(JSON 만 출력):
{{"comment": "두 문장", "nickname": "별명"}}"""


def _ask(score, grade, directions):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None                      # 키가 없으면 조용히 건너뛴다

    body = {
        "contents": [{
            "parts": [{
                "text": PROMPT.format(score=score, grade=grade,
                                      directions=", ".join(directions))
            }]
        }],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 500,
            "responseMimeType": "application/json",
            # gemini-2.5/3.x flash 는 기본적으로 '생각'에 먼저 토큰을 쓴다.
            # 짧은 촌평 하나에는 필요 없으니 꺼서 답변 토큰을 확보한다.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    req = urllib.request.Request(
        ENDPOINT.format(model=MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        out = json.loads(r.read().decode("utf-8"))
    cands = out.get("candidates") or []
    if not cands or not cands[0].get("content", {}).get("parts"):
        print(f"comment 빈 응답: finishReason="
              f"{cands[0].get('finishReason') if cands else None} "
              f"promptFeedback={out.get('promptFeedback')}")
        return None
    text = cands[0]["content"]["parts"][0]["text"]
    got = json.loads(text)
    return {"comment": str(got.get("comment", ""))[:300],
            "nickname": str(got.get("nickname", ""))[:20]}


class handler(BaseHTTPRequestHandler):
    def _send(self, payload, code=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
            got = _ask(int(req.get("score", 0)),
                       str(req.get("grade", "")),
                       [str(x) for x in req.get("directions", [])][:10])
            self._send(got or {"comment": None})
        except Exception as e:
            print(f"comment 실패: {e}")  # Vercel Logs 에서 원인 확인용
            # 무엇이 실패하든 앱을 멈추지 않는다
            self._send({"comment": None})

    def do_GET(self):
        self._send({"ok": True, "key": bool(os.environ.get("GEMINI_API_KEY"))})
