import requests
from bs4 import BeautifulSoup
import os
import time
import random

# 1. 설정
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# 재원님이 필터를 적용한 최신 URL
TARGET_URL = "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/entry-level-internship?rlistTab=0&rOrderTab=1&rSearchText=&bpart_no=10026%2C10030%2C10045&spart_no=&scd=I000%2CB000%2CK000&edu_no=&pref=&jtype=1&careerTypeCode=1%2F3&ctype=3%2C4%2C2&jobFilter=0&listDisplayCode=2&MainPageNo=1&FreePageNo=1&psTab=20&themeNo=169&tabNo=0&giDisplayCntLimitStat=0&GIOpenTypeCode=0&pay=&pay_type_code=&IsPartCodeSearch=false"

# 잡코리아 보안 우회를 위한 정밀 헤더
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.jobkorea.co.kr/',
    'Connection': 'keep-alive'
}

def get_jobs():
    session = requests.Session() # 세션을 사용해 연결 유지
    
    for attempt in range(5):
        try:
            print(f"{attempt + 1}번째 접속 시도 중...")
            # 타임아웃을 늘리고 실제 브라우저처럼 세션 접속
            response = session.get(TARGET_URL, headers=HEADERS, timeout=40)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_list = []
                
                # 새로운 표 형식(tr.devloopArea)에 맞춘 추출 로직
                items = soup.select('tr.devloopArea')
                
                for item in items:
                    try:
                        # 고유 번호 추출
                        scrap_btn = item.select_one('.devAddScrap')
                        job_id = scrap_btn['data-gno']
                        
                        # 회사명
                        company = item.select_one('.tplCo a.link').text.strip()
                        
                        # 공고 제목 및 주소
                        title_tag = item.select_one('.tplTit .titBx strong a')
                        title = title_tag.text.strip()
                        link = "https://www.jobkorea.co.kr" + title_tag['href']
                        
                        # 마감일
                        deadline = item.select_one('.odd .date.dotum').text.strip()
                        
                        job_list.append({
                            'id': job_id,
                            'company': company,
                            'title': title,
                            'link': link,
                            'deadline': deadline
                        })
                    except Exception:
                        continue
                return job_list
            else:
                print(f"상태 코드 이상: {response.status_code}")
        except Exception as e:
            print(f"접속 실패 사유: {e}")
            
        # 실패 시 랜덤하게 10~20초 쉬었다가 다시 시도 (차단 방지)
        time.sleep(random.uniform(10, 20))
            
    return []

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, data=data, timeout=10)
    except:
        pass

if __name__ == "__main__":
    jobs = get_jobs()
    
    if not jobs:
        print("공고 데이터를 가져오지 못했습니다. 서버 차단 혹은 구조 변경 가능성이 있습니다.")
    else:
        db_file = "processed_ids.txt"
        if os.path.exists(db_file):
            with open(db_file, "r") as f:
                processed_ids = f.read().splitlines()
        else:
            processed_ids = []

        new_count = 0
        new_id_list = []
        
        for job in jobs:
            if job['id'] not in processed_ids:
                message = (
                    f"🎯 *필터링 공고 노티*\n\n"
                    f"🏢 *{job['company']}*\n"
                    f"📝 {job['title']}\n"
                    f"📅 마감: {job['deadline']}\n"
                    f"🔗 [공고 바로가기]({job['link']})"
                )
                send_telegram(message)
                new_id_list.append(job['id'])
                new_count += 1
                time.sleep(1) # 전송 지연
        
        updated_ids = (new_id_list + processed_ids)[:200]
        with open(db_file, "w") as f:
            f.write("\n".join(updated_ids))
        print(f"알림 전송 완료: {new_count}개")
