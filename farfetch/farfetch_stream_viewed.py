import requests
import json
from datetime import datetime

def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("올바른 날짜 형식이 아닙니다. YYYY-MM-DD 형식으로 입력해주세요.")

# API 정보
url = "https://api.cloudflare.com/client/v4/graphql"
headers = {
    "Content-Type": "application/json",
    "X-Auth-Email": "hakang@mz.co.kr",
    "X-Auth-Key": "f6f652701a00dc80fc3c5e764adb1b84461e3"
}

# 계정 ID
account_id = "98d26011d91e2c6c00a1fe006dc4b865"

# 사용자 입력
start_date = get_date_input("시작 날짜를 입력하세요 (YYYY-MM-DD): ")
end_date = get_date_input("종료 날짜를 입력하세요 (YYYY-MM-DD): ")

# GraphQL 쿼리
query = """
{
    viewer {
        accounts(filter: {accountTag: $accountTag}) {
            Total: streamMinutesViewedAdaptiveGroups(filter: $filter, limit: 10000) {
                sum {
                    minutesViewed
                }
            }
        }
    }
}
"""

# 변수
variables = {
    "accountTag": account_id,
    "filter": {
        "date_geq": start_date,
        "date_leq": end_date
    }
}

# API 요청
response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)

# 응답 처리 및 파일 저장
if response.status_code == 200:
    data = response.json()
    minutes_viewed = data["data"]["viewer"]["accounts"][0]["Total"][0]["sum"]["minutesViewed"]
    
    # 결과 JSON 생성
    result = {
        "query_period": f"{start_date}_{end_date}",
        "account_id": account_id,
        "minutes_viewed": minutes_viewed
    }
    
    # 파일명 생성
    filename = f"stream_viewed_{start_date}_{end_date}_{account_id}.json"
    
    # JSON 파일로 저장
    with open(filename, 'w') as f:
        json.dump(result, f, indent=4)
    
    print(f"결과가 {filename} 파일로 저장되었습니다.")
    print(f"시청 시간(분): {minutes_viewed}")
else:
    print(f"오류 발생: {response.status_code}")
    print(response.text)
