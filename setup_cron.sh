#!/bin/bash
# cron 등록 + 결과 확인
SCRIPT_DIR="/home/ubuntu/school_bot"
LOG_FILE="/tmp/school_cron_setup.log"

{
    echo "=== cron 등록 시작 $(date) ==="

    (crontab -l 2>/dev/null | grep -v "school_bot";
    echo "# 아침 7:00 KST = 22:00 UTC (일~목 UTC = 월~금 KST)";
    echo "0 22 * * 0-4 cd $SCRIPT_DIR && source venv/bin/activate && python3 morning.py >> /tmp/school_morning.log 2>&1";
    echo "# 저녁 20:00 KST = 11:00 UTC (월~금 UTC)";
    echo "0 11 * * 1-5 cd $SCRIPT_DIR && source venv/bin/activate && python3 evening.py >> /tmp/school_evening.log 2>&1"
    ) | crontab -

    echo "=== 등록된 cron ==="
    crontab -l | grep school
    echo "=== 완료 ==="
} > "$LOG_FILE" 2>&1

cat "$LOG_FILE"
