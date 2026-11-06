#!/bin/bash
# 방문자 카운터 설치: sudo bash install_counter.sh
# 1) systemd 서비스 game_counter 등록과 시작  2) nginx 설정(game.carroty.com)에 /count 프록시 반영
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$DIR/game_counter.service" /etc/systemd/system/game_counter.service
systemctl daemon-reload
systemctl enable --now game_counter
systemctl restart game_counter
cp /etc/nginx/sites-available/game.carroty.com /etc/nginx/sites-available/game.carroty.com.bak-counter 2>/dev/null || true
cp "$DIR/game.carroty.com.conf" /etc/nginx/sites-available/game.carroty.com
ln -sf /etc/nginx/sites-available/game.carroty.com /etc/nginx/sites-enabled/game.carroty.com
nginx -t
systemctl reload nginx
echo "완료: systemctl status game_counter / curl -s https://game.carroty.com/count"
