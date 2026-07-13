import requests
from bs4 import BeautifulSoup
import os
import re
import html
import json
import time
import random
import traceback
from datetime import datetime, timezone, timedelta

# 1. 설정
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
TARGET_URL = "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/entry-level-internship?rlistTab=0&rOrderTab=2&rSearchText=&bpart_no=10026%2C10030%2C10045&spart_no=&scd=I000%2CB000%2CK000&edu_no=&pref=&jtype=1&careerTypeCode=1%2F3&ctype=3%2C4%2C2&jobFilter=0&listDisplayCode=2&MainPageNo=1&FreePageNo=1&psTab=20&themeNo=169&tabNo=0&giDisplayCntLimitStat=0&GIOpenTypeCode=0&pay=&pay_type_code=&IsPartCodeSearch=false"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://www.jobkorea.co.kr/',
}

def get_jobs():
    session = requests.Session()
    for attempt in range(5):
        try:
            print(f"{attempt + 1}번째 접속 시도 중...")
            response = session.get(TARGET_URL, headers=HEADERS, timeout=40)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_list = []
                items = soup.select('tr.devloopArea')

                for item in items:
                    try:
                        scrap_btn = item.select_one('.devAddScrap')
                        job_id = scrap_btn['data-gno']
                        company = item.select_one('.tplCo a.link').get_text(strip=True)
                        title_tag = item.select_one('.tplTit .titBx strong a')
                        title = title_tag.get_text(strip=True)
                        link = "https://www.jobkorea.co.kr" + title_tag['href']
                        deadline = item.select_one('.odd .date.dotum').get_text(strip=True)
                        reg_time_tag = item.select_one('.odd .time.dotum')
                        reg_time = reg_time_tag.get_text(strip=True) if reg_time_tag else "정보 없음"

                        job_list.append({
                            'id': job_id, 'company': company, 'title': title, 'link': link, 'deadline': deadline, 'reg_time': reg_time
                        })
                    except: continue
                return job_list
            else:
                print(f"HTTP {response.status_code}")
        except Exception as e:
            print(f"에러: {e}")
        time.sleep(10)
    # 5회 모두 실패 = 사이트 접속 불가 → 예외로 알려서 오류 노티되게 함
    raise RuntimeError("잡코리아 접속 5회 모두 실패(사이트 접근 불가)")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    # TG_CHAT_ID 에 콤마/공백으로 여러 명을 넣을 수 있습니다. (예: "8755814064,8467039744")
    chat_ids = [c for c in re.split(r"[,\s]+", TG_CHAT_ID or "") if c]
    for cid in chat_ids:
        # HTML 모드를 사용하여 특수문자 충돌을 방지합니다.
        data = {
            "chat_id": cid,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, data=data, timeout=10)
        if res.status_code != 200:
            print(f"전송 실패 (chat_id={cid}): {res.text}")

# ─────────────────────────────────────────────────────────────
# 상태(bot_state.json) + 오류 노티 + 12시간 무신규 하트비트
# ─────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
STATE_FILE = "bot_state.json"
HEARTBEAT_HOURS = 12       # 이 시간 동안 새 공고가 없으면 '신규 없음' 노티
ERROR_DEDUP_HOURS = 12     # 같은 오류는 이 시간에 한 번만 노티(스팸 방지)
BOT_NAME = "잡코리아봇"

def _now_iso():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

def _parse_iso(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
    except Exception:
        return None

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
                d = json.load(f)
                return d if isinstance(d, dict) else {}
        except Exception:
            pass
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("state 저장 실패:", e)

def send_plain(text):
    """모든 chat_id 에 일반텍스트 전송(오류/하트비트 노티용)."""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    for cid in [c for c in re.split(r"[,\s]+", TG_CHAT_ID or "") if c]:
        try:
            requests.post(url, data={"chat_id": cid, "text": text[:3900],
                                     "disable_web_page_preview": True}, timeout=10)
        except Exception as e:
            print("노티 전송 실패:", cid, e)

def notify_error(state, raw_text):
    raw_text = (raw_text or "").strip() or "알 수 없는 오류"
    sig = raw_text.splitlines()[-1][:120]
    now = datetime.now(KST)
    last_at = _parse_iso(state.get("last_error_at"))
    if state.get("last_error_sig") == sig and last_at and (now - last_at) < timedelta(hours=ERROR_DEDUP_HOURS):
        print("동일 오류 최근 노티됨 → 생략")
        return
    send_plain(f"⚠️ [{BOT_NAME}] 오류가 발생했어요 (원문):\n\n{raw_text}\n\n(발생 시각: {_now_iso()})")
    state["last_error_sig"] = sig
    state["last_error_at"] = _now_iso()

def maybe_heartbeat(state, collected, new_count):
    now = datetime.now(KST)
    last = _parse_iso(state.get("last_activity_at"))
    if last is None:
        state["last_activity_at"] = _now_iso()   # 최초: 타이머 시작(즉시 노티 방지)
        return
    if (now - last) >= timedelta(hours=HEARTBEAT_HOURS):
        send_plain(f"⏰ [{BOT_NAME}] 최근 {HEARTBEAT_HOURS}시간 내 새로 스크래핑된 채용공고가 없어요.\n"
                   f"수집완료 {collected}건, 신규후보 {new_count}건\n(확인 시각: {_now_iso()})")
        state["last_activity_at"] = _now_iso()

if __name__ == "__main__":
    state = load_state()
    try:
        jobs = get_jobs()
        db_file = "processed_ids.txt"
        processed_ids = open(db_file, "r").read().splitlines() if os.path.exists(db_file) else []

        new_count = 0
        new_id_list = []
        for job in reversed(jobs):
            if job['id'] not in processed_ids:
                # 공고명/회사명에 <, >, & 가 있어도 메시지가 깨지지 않도록 이스케이프
                c = html.escape(job['company'])
                t = html.escape(job['title'])
                lk = html.escape(job['link'])
                dl = html.escape(job['deadline'])
                rt = html.escape(job['reg_time'])
                # HTML 태그를 사용한 깔끔한 포맷
                message = (
                    f"<b>{c}</b> - <b>{t}</b>\n\n"
                    f"• {c}\n"
                    f"• <a href='{lk}'><b>{t}</b></a>\n\n"
                    f"⏳ {dl}\n"
                    f"본 공고는 {rt}됐어요"
                )
                send_telegram(message)
                new_id_list.append(job['id'])
                new_count += 1
                time.sleep(1.2)

        with open(db_file, "w") as f:
            f.write("\n".join((new_id_list + processed_ids)[:200]))
        print(f"완료: 수집완료 {len(jobs)}건, 신규후보 {new_count}건 발송 시도됨")

        # 활동 기록 / 12시간 무신규 하트비트
        if new_count > 0:
            state["last_activity_at"] = _now_iso()
        else:
            maybe_heartbeat(state, len(jobs), 0)
    except Exception:
        tb = traceback.format_exc()
        print(tb)
        notify_error(state, tb)   # 오류 원문을 텔레그램으로 노티(같은 오류는 12h 1회)
    finally:
        save_state(state)
