import requests
from bs4 import BeautifulSoup
import os
import time

# 1. 설정
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
# URL을 모바일 버전이나 다른 경로로 시도해볼 수 있습니다.
TARGET_URL = "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/entry-level-internship?themeNo=169"

# 헤더를 더 상세하게 수정 (진짜 크롬 브라우저처럼 보이게 함)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.jobkorea.co.kr/',
}

def get_jobs():
    # 접속 실패 시 최대 3번까지 다시 시도합니다.
    for attempt in range(3):
        try:
            response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_list = []
                items = soup.select('.recruitList ul li')
                
                for item in items:
                    try:
                        scrap_btn = item.select_one('.dev-scrap')
                        if not scrap_btn: continue
                        
                        job_id = scrap_btn['data-gno']
                        company = item.select_one('.corNm').text.strip()
                        title_tag = item.select_one('.rTit a')
                        title = title_tag.text.strip()
                        link = "https://www.jobkorea.co.kr" + title_tag['href']
                        deadline = item.select_one('.rPeriod').text.strip()
                        
                        job_list.append({
                            'id': job_id, 'company': company, 'title': title, 'link': link, 'deadline': deadline
                        })
                    except:
                        continue
                return job_list
            else:
                print(f"접속 실패 (상태 코드: {response.status_code})")
        except Exception as e:
            print(f"{attempt + 1}번째 시도 실패: {e}")
            time.sleep(5) # 5초 기다렸다가 다시 시도
            
    return []

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        params = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

if __name__ == "__main__":
    jobs = get_jobs()
    
    if not jobs:
        print("공고를 가져오지 못했습니다. 사이트 구조 변경이나 차단 여부를 확인하세요.")
        # 만약 차단되었다면 알림을 하나 보내줍니다. (테스트용)
        # send_telegram("⚠️ 잡코리아 접속에 실패했습니다. 확인이 필요합니다.")
    else:
        db_file = "processed_ids.txt"
        if os.path.exists(db_file):
            with open(db_file, "r") as f:
                processed_ids = f.read().splitlines()
        else:
            processed_ids = []

        new_id_list = []
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
                time.sleep(1) # 텔레그램 도배 방지
        
        updated_ids = (new_id_list + processed_ids)[:100]
        with open(db_file, "w") as f:
            f.write("\n".join(updated_ids))
        print(f"{len(new_id_list)}개의 새로운 공고를 보냈습니다.")
