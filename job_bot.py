import requests
from bs4 import BeautifulSoup
import os
import time

# 1. 설정
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# 재원님이 필터를 적용한 새로운 주소입니다.
TARGET_URL = "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/entry-level-internship?rlistTab=0&rOrderTab=2&rSearchText=&bpart_no=10026%2C10030%2C10045&spart_no=&scd=I000%2CB000%2CK000&edu_no=&pref=&jtype=1%2C3&careerTypeCode=1%2F3%2C4&ctype=3%2C4%2C2&jobFilter=0&listDisplayCode=3&MainPageNo=1&FreePageNo=1&psTab=21&themeNo=169&tabNo=0&giDisplayCntLimitStat=0&GIOpenTypeCode=0&pay=&pay_type_code=&IsPartCodeSearch=false"

# 잡코리아의 차단을 피하기 위한 "진짜 사람" 같은 헤더 설정
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Origin': 'https://www.jobkorea.co.kr',
    'Referer': 'https://www.jobkorea.co.kr/',
}

def get_jobs():
    # 접속 실패 시 최대 5번까지 다시 시도합니다. (지연 시간 추가)
    for attempt in range(5):
        try:
            print(f"{attempt + 1}번째 접속 시도 중...")
            response = requests.get(TARGET_URL, headers=HEADERS, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_list = []
                # 재원님이 주신 HTML 구조에 맞춘 셀렉터
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
                    except Exception:
                        continue
                return job_list
            else:
                print(f"상태 코드 오류: {response.status_code}")
        except Exception as e:
            print(f"오류 발생: {e}")
            
        # 실패 시 10초 쉬었다가 다시 시도 (차단 방지)
        time.sleep(10)
            
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
        print("공고를 가져오는 데 실패했습니다. 주소가 바뀌었거나 서버에서 차단했을 수 있습니다.")
    else:
        db_file = "processed_ids.txt"
        if os.path.exists(db_file):
            with open(db_file, "r") as f:
                processed_ids = f.read().splitlines()
        else:
            processed_ids = []

        new_count = 0
        new_id_list = []
        
        # 최신 공고부터 알림 전송
        for job in jobs:
            if job['id'] not in processed_ids:
                message = (
                    f"✨ *잡코리아 기업 필터링 맞춤 공고 노티*\n\n"
                    f"🏢 *{job['company']}*\n"
                    f"📝 {job['title']}\n"
                    f"📅 마감: {job['deadline']}\n"
                    f"🔗 [공고 열기]({job['link']})"
                )
                send_telegram(message)
                new_id_list.append(job['id'])
                new_count += 1
                time.sleep(1.5) # 텔레그램 도배 방지
        
        # 새로운 ID 저장
        updated_ids = (new_id_list + processed_ids)[:200]
        with open(db_file, "w") as f:
            f.write("\n".join(updated_ids))
        
        print(f"성공! 새로운 공고 {new_count}개를 전송했습니다.")
