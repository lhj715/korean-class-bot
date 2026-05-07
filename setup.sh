#!/bin/bash
# Lightsail 서버 초기 설정 스크립트
# 실행: bash setup.sh

set -e

echo "=== 패키지 설치 ==="
pip3 install -r requirements.txt

echo ""
echo "=== 환경변수 설정 (~/.bashrc에 추가) ==="
echo "아래 세 줄을 ~/.bashrc 또는 ~/.profile에 추가하세요:"
echo ""
echo "  export TELEGRAM_BOT_TOKEN=\"your_bot_token\""
echo "  export TELEGRAM_CHANNEL_ID=\"@your_channel\""
echo "  export ANTHROPIC_API_KEY=\"your_api_key\""
echo ""

echo "=== cron 등록 (KST 기준) ==="
echo "아래 명령어로 crontab 편집: crontab -e"
echo ""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "# 아침 7:00 KST (= 22:00 UTC 전날) - 월~금 KST"
echo "0 22 * * 0-4 cd ${SCRIPT_DIR} && /usr/bin/python3 morning.py >> /var/log/school_bot_morning.log 2>&1"
echo ""
echo "# 저녁 20:00 KST (= 11:00 UTC) - 월~금 KST"
echo "0 11 * * 1-5 cd ${SCRIPT_DIR} && /usr/bin/python3 evening.py >> /var/log/school_bot_evening.log 2>&1"
echo ""
echo "설정 완료 후 테스트:"
echo "  python3 morning.py"
echo "  python3 evening.py"
