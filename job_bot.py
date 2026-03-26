import requests
from bs4 import BeautifulSoup
import os
import time
import random

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
        except Exception as e:
            print(f"에러: {e}")
        time.sleep(10)
    return []

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    # HTML 모드를 사용하여 특수문자 충돌을 방지합니다.
    data = {
        "chat_id": TG_CHAT_ID, 
        "text": msg, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    res = requests.post(url, data=data, timeout=10)
    if res.status_code != 200:
        print(f"전송 실패 사유: {res.text}")

if __name__ == "__main__":
    jobs = get_jobs()
    db_file = "processed_ids.txt"
    processed_ids = open(db_file, "r").read().splitlines() if os.path.exists(db_file) else []

    new_count = 0
    new_id_list = []
    
    for job in reversed(jobs):
        if job['id'] not in processed_ids:
            # HTML 태그를 사용한 깔끔한 포맷
            message = (
                f"<b>{job['company']}</b> - <b>{job['title']}</b> 신규 업데이트 노티\n\n"
                f"• {job['company']}\n"
                f"• <a href='{job['link']}'><b>{job['title']}</b></a>\n"
                f"• {job['deadline']}\n\n"
                f"reg_time {job['reg_time']}"
            )
            send_telegram(message)
            new_id_list.append(job['id'])
            new_count += 1
            time.sleep(1.2)

    with open(db_file, "w") as f:
        f.write("\n".join((new_id_list + processed_ids)[:200]))
    print(f"완료: {new_count}개 발송 시도됨")
