#!/usr/bin/env python3
"""방문자 카운터 서버(game.carroty.com).

  POST /hit   방문을 센다(같은 방문자는 하루에 한 번만). 현재 숫자를 돌려준다
  GET  /hit   세지 않고 현재 숫자만 돌려준다
응답: {"today": 오늘 방문자 수, "total": 전체(날마다 센 방문자의 합), "counted": 이번에 새로 셌는지}

방문자는 IP(Cloudflare 뒤라 CF-Connecting-IP)를 비밀 소금으로 섞어 해시한 값으로만 구분하고 IP 자체는 저장하지 않는다.
숫자는 count.json에, 오늘 이미 센 방문자 해시는 seen.json에 저장해서 재시작해도 남는다(`~/.local/share/game_counter/`, 웹 루트 밖이라 웹으로 안 읽힌다).
127.0.0.1에만 열고, 바깥에는 nginx(`location = /count`)가 프록시한다. 인증은 없다.
"""
import hashlib
import json
import os
import secrets
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 숫자 파일은 웹에서 읽히지 않게 웹 루트(app 폴더) 밖에 둔다
DATA = os.path.expanduser("~/.local/share/game_counter")
os.makedirs(DATA, exist_ok=True)
COUNT = os.environ.get("COUNTER_STORE", os.path.join(DATA, "count.json"))
SEEN = os.environ.get("COUNTER_SEEN", os.path.join(DATA, "seen.json"))
PORT = int(os.environ.get("COUNTER_PORT", "8004"))

lock = threading.Lock()


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def today():
    return datetime.now().strftime("%Y-%m-%d")


def load_state():
    count = read_json(COUNT, {})
    count.setdefault("total", 0)
    count.setdefault("days", {})
    seen = read_json(SEEN, {})
    seen.setdefault("salt", secrets.token_hex(16))
    seen.setdefault("date", today())
    seen.setdefault("ids", [])
    return count, seen


def hit(ip, do_count):
    """방문을 세고(do_count일 때) 숫자를 돌려준다."""
    with lock:
        count, seen = load_state()
        day = today()
        if seen["date"] != day:                  # 날이 바뀌면 오늘 본 사람 목록을 비운다
            seen["date"], seen["ids"] = day, []
        counted = False
        if do_count:
            h = hashlib.sha256((seen["salt"] + ip).encode()).hexdigest()[:16]
            if h not in seen["ids"]:
                seen["ids"].append(h)
                count["days"][day] = count["days"].get(day, 0) + 1
                count["total"] += 1
                counted = True
        if do_count:
            write_json(COUNT, count)
            write_json(SEEN, seen)
        return {"today": count["days"].get(day, 0), "total": count["total"], "counted": counted}


class Handler(BaseHTTPRequestHandler):
    def reply(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def client_ip(self):
        return (self.headers.get("CF-Connecting-IP")
                or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                or self.headers.get("X-Real-IP")
                or self.client_address[0])

    def handle_hit(self, do_count):
        try:
            self.reply(hit(self.client_ip(), do_count))
        except Exception:
            self.reply({"error": "server"}, 500)

    def do_GET(self):
        self.handle_hit(False)

    def do_POST(self):
        self.handle_hit(True)

    def log_message(self, fmt, *args):          # IP가 로그에 남지 않게 접속 로그는 끈다
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
