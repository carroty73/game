#!/bin/bash
# game.carroty.com nginx 설정 설치: sudo bash install_nginx_game.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$DIR/game.carroty.com.conf" /etc/nginx/sites-available/game.carroty.com
ln -sf /etc/nginx/sites-available/game.carroty.com /etc/nginx/sites-enabled/game.carroty.com
nginx -t
systemctl reload nginx
echo "완료. Cloudflare에 game 레코드(app과 같은 서버 IP)를 추가하세요."
