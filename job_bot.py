import requests
from bs4 import BeautifulSoup
import os
import time
import random

# 1. 설정
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
TARGET_URL = "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/entry-level-internship?rlistTab=0&rOrderTab=1&rSearchText=&bpart_no=10026%2C10030%2C10045&spart_no=&scd=I000%2CB000%2CK000&edu_no=&pref=&jtype=1&careerTypeCode=1%2F3&ctype=3%2C4%2C2&jobFilter=0&listDisplayCode=2&MainPageNo=1&FreePageNo=1&psTab=20&themeNo=169&tabNo=0&giDisplayCntLimitStat=0&GIOpenTypeCode=0&pay=&pay_type_code=&IsPartCodeSearch=false"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
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
                        
                        # 마감일 정보
                        deadline = item.select_one('.odd .date.dotum').get_text(strip=True)
                        
                        # 등록일시 정보 (방금 전, 9시간 전 등)
                        reg_time_tag = item.select_one('.odd .time.dotum')
                        reg_time = reg_time_tag.get_text(strip=True) if reg_time_tag else "시간 정보 없음"
                        
                        job_list.append({
                            'id': job_id,
                            'company': company,
                            'title': title,
                            'link': link,
                            'deadline': deadline,
                            'reg_time': reg_time
                        })
                    except Exception:
                        continue
                return job_list
            else:
                print(f"상태 코드 이상: {response.status_code}")
        except Exception as e:
            print(f"접속 실패: {e}")
        
        time.sleep(random.uniform(10, 20))
    return []

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHAT_ID, 
            "text": msg, 
            "parse_mode": "Markdown",
            "disable_web_page_preview": True # 썸네일(미리보기) 제거 설정
        }
        requests.post(url, data=data, timeout=10)
    except:
        pass

if __name__ == "__main__":
    jobs = get_jobs()
    
    if jobs:
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
                # 재원님이 요청하신 새로운 메시지 포맷 적용
                message = (
                    f"*필터링 채용공고 노티*\n\n"
                    f"- 회사명 : {job['company']}\n"
                    f"- 공고명 : [*{job['title']}*]({job['link']})\n"
                    f"- 마감일 : {job['deadline']}\n\n"
                    f"{job['reg_time']}"
                )
                send_telegram(message)
                new_id_list.append(job['id'])
                new_count += 1
                time.sleep(1.2)
        
        updated_ids = (new_id_list + processed_ids)[:200]
        with open(db_file, "w") as f:
            f.write("\n".join(updated_ids))
        print(f"전송 완료: {new_count}개")
    else:
        print("데이터를 가져오지 못했습니다.")
