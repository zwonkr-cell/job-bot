import requests
from bs4 import BeautifulSoup
import os

# 1. 설정 (GitHub Secrets에서 불러옴)
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
TARGET_URL = "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/entry-level-internship?themeNo=169"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_jobs():
    response = requests.get(TARGET_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    job_list = []
    # HTML 구조에서 각 공고 항목을 찾습니다.
    items = soup.select('.recruitList ul li')
    
    for item in items:
        try:
            # 고유 ID (중복 알림 방지용)
            job_id = item.select_one('.dev-scrap')['data-gno']
            # 회사명
            company = item.select_one('.corNm').text.strip()
            # 공고 제목 및 링크
            title_tag = item.select_one('.rTit a')
            title = title_tag.text.strip()
            link = "https://www.jobkorea.co.kr" + title_tag['href']
            # 마감일
            deadline = item.select_one('.rPeriod').text.strip()
            
            job_list.append({
                'id': job_id,
                'company': company,
                'title': title,
                'link': link,
                'deadline': deadline
            })
        except:
            continue
    return job_list

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    params = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.get(url, params=params)

if __name__ == "__main__":
    jobs = get_jobs()
    
    # 이미 확인한 공고 ID 저장용 파일
    db_file = "processed_ids.txt"
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            processed_ids = f.read().splitlines()
    else:
        processed_ids = []

    new_id_list = []
    
    # 최신 공고부터 확인 (역순)
    for job in jobs:
        if job['id'] not in processed_ids:
            message = (
                f"🚀 *새로운 인턴 공고!*\n\n"
                f"🏢 *{job['company']}*\n"
                f"📝 {job['title']}\n"
                f"📅 마감: {job['deadline']}\n"
                f"🔗 [공고 자세히 보기]({job['link']})"
            )
            send_telegram(message)
            new_id_list.append(job['id'])
            
    # 새로 확인한 ID를 저장 (최대 100개)
    updated_ids = (new_id_list + processed_ids)[:100]
    with open(db_file, "w") as f:
        f.write("\n".join(updated_ids))
