from datetime import datetime, timedelta
import requests
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

def parse_date(date_str: str) -> datetime:
    """날짜 문자열을 datetime 객체로 변환"""
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d')
    except ValueError:
        raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력해주세요.")

def format_count(count: int) -> str:
    """숫자를 M 단위로 포맷팅"""
    millions = count / 1_000_000
    return f"{millions:.2f}M({count:,})"

@dataclass
class ZoneStats:
    zone_id: str
    count: int

class BotManagementStats:
    COUPANG_ZONE_IDS = [
        "2d2b409ac15216d05407cb2a35b8cbc9",  # cmapi.coupang.com
        "e4e90a478bd59fd109451f4fa1bcded2",  # coupa.ng
        "9f298a37f22afc2a9dd6d6a90f043ad4",  # coupang.com
        "b959a0af7e1b10f63bb191d05a8034f6",  # coupangcorp.com
        "acc53312d880dca1c83c7938281abfb1",  # coupangeats.com
        "af53edde284d7a35b2ad05e355763d2b",  # coupangfinancial.com
        "329eb2b6704f40b127f94f3baf1e3ad7",  # coupang.kr
        "a0c9d773a004adebf7fb6be35a1e3916",  # coupangls.com
        "ead5f9571bbfd34d5d9b2f05209abd00",  # coupangpay.com
        "2d31fb504321a965f77dcc6d3816852b",  # coupangplay.com
        "314d27529f1b5d9ccf9bebc38e68a1b8",  # cp-redteam.com
        "d9140787a3c211b4976c119f5d7965f8",  # coupangpos.com
        "fbab553c31652e53d28c9f87320f798a",  # coupangstreaming.com
        "f00c8f33c4aa5419a0c50c05bd7e9f05",  # ddnayo.com
        "241750d06755d7d70b9016c2e5009ecb",  # devcoupangstreaming.com
        "03365665ab121a2e5ee7239fa9964e9d",  # mugpos.com
        "49fe9c55a9da6b9f3bdb9badf3031bb9",  # tw.coupang.com
        "b3847fc9df2f7be3cf322039e69c99dd", # jp.coupang.com
        "67cfcbde492843b0a5326df83037118b",  # rocketnow.co.jp
    ]

    FARFETCH_ZONE_IDS = [
        "c6506e0fa56e19e2f665b2630fdb760a",  # blackandwhite-ff.com
        "6c7286ec807229969935b58c8e8bb92a",  # brownsfashion.com
        "329d2de0b2fac7e59a6b2b0564b996ff",  # farfetchplatform.com
        "24f98b614a0f681891d4f1947aff6272"   # off---white.com
    ]

    QUERY = """
    query ZoneHttpRequestsAdaptive($zoneTag: String!, $likelyHumanFilter: ZoneHttpRequestsAdaptiveGroupsFilter_InputObject!) {
        viewer {
            zones(filter: {zoneTag: $zoneTag}) {
                likely_human: httpRequestsAdaptiveGroups(
                    filter: $likelyHumanFilter,
                    limit: 10000
                ) {
                    count
                }
            }
        }
    }
    """

    def __init__(self, cf_api_token: str, debug: bool = False):
        self.cf_api_token = cf_api_token
        self.debug = debug

    def format_datetime(self, dt_str: str) -> str:
        """UTC datetime 문자열을 KST로 변환하여 원하는 형식으로 반환"""
        # UTC 문자열을 datetime 객체로 변환
        dt = datetime.strptime(dt_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
        # UTC를 KST로 변환 (+9시간)
        kst_dt = dt + timedelta(hours=9)
        # 원하는 형식으로 포맷팅
        return kst_dt.strftime('%Y-%m-%d %H:%M:%S')

    def get_date_range(self, target_date: datetime) -> Dict[str, str]:
        """특정 날짜에 대한 KST 기준 05:00:00부터 다음날 04:59:59까지의 시간 범위를 반환"""
        # 해당 날짜의 05:00:00 KST (UTC로는 전날 20:00:00)
        start = target_date.replace(hour=5, minute=0, second=0)
        # 다음 날의 04:59:59 KST (UTC로는 19:59:59)
        end = (target_date + timedelta(days=1)).replace(hour=4, minute=59, second=59)

        # UTC 시간으로 변환
        utc_start = (start - timedelta(hours=9))
        utc_end = (end - timedelta(hours=9))

        return {
            'start': utc_start.isoformat() + "Z",
            'end': utc_end.isoformat() + "Z"
        }

    def create_query_variables(self, start_date: str, end_date: str, zone_id: str) -> Dict[str, Any]:
        """GraphQL 쿼리 변수 생성"""
        return {
            'zoneTag': zone_id,
            'likelyHumanFilter': {
                'requestSource': 'eyeball',
                'botScore_geq': 30,
                'botScore_leq': 99,
                'datetime_geq': start_date,
                'datetime_leq': end_date,
                'botManagementDecision_neq': 'other'
            }
        }

    def fetch_cloudflare_data(self, zone_id: str, date_range: Dict[str, str]) -> Optional[int]:
        """Cloudflare GraphQL API를 호출하여 데이터 조회"""
        variables = self.create_query_variables(
            date_range['start'], 
            date_range['end'], 
            zone_id
        )

        try:
            response = requests.post(
                'https://api.cloudflare.com/client/v4/graphql',
                headers={
                    'Authorization': f'Bearer {self.cf_api_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'query': self.QUERY,
                    'variables': variables
                }
            )

            if self.debug:
                print(f"\nRequest for zone {zone_id}:")
                print("Query:", self.QUERY)
                print(f"Variables: {json.dumps(variables, indent=2)}")
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}\n")

            if not response.ok:
                print(f"Error for zone {zone_id}: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None

            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"GraphQL errors for zone {zone_id}:")
                print(json.dumps(data['errors'], indent=2))
                return None

            # 응답 데이터에서 count 값을 추출
            zones = data.get('data', {}).get('viewer', {}).get('zones', [])
            if zones and len(zones) > 0:
                likely_human = zones[0].get('likely_human', [])
                if likely_human and len(likely_human) > 0:
                    count = likely_human[0].get('count')
                    if count is not None:
                        if self.debug:
                            print(f"Found count for zone {zone_id}: {count}")
                        return count

            if self.debug:
                print(f"No count data found for zone {zone_id}")
            return 0

        except Exception as e:
            print(f"Exception for zone {zone_id}: {str(e)}")
            if self.debug:
                import traceback
                print(traceback.format_exc())
            return None

    def collect_stats(self, target_date: datetime) -> Dict[str, Any]:
        """특정 날짜의 모든 zone 통계 수집"""
        date_range = self.get_date_range(target_date)
        stats = {
            'date': target_date.strftime('%Y-%m-%d'),
            'coupang': {
                'cmapi': 0,
                'non_cmapi': 0,
                'total': 0,
                'details': []
            },
            'farfetch': {'total': 0, 'details': []}
        }

        # Coupang stats
        cmapi_zone_id = "2d2b409ac15216d05407cb2a35b8cbc9"  # cmapi.coupang.com
        
        # First collect cmapi stats
        cmapi_count = self.fetch_cloudflare_data(cmapi_zone_id, date_range)
        if cmapi_count is not None:
            stats['coupang']['cmapi'] = cmapi_count
            stats['coupang']['total'] += cmapi_count
            stats['coupang']['details'].append(ZoneStats(cmapi_zone_id, cmapi_count))

        # Then collect other Coupang zones
        for zone_id in self.COUPANG_ZONE_IDS:
            if zone_id == cmapi_zone_id:
                continue
            
            count = self.fetch_cloudflare_data(zone_id, date_range)
            if count is not None:
                stats['coupang']['non_cmapi'] += count
                stats['coupang']['total'] += count
                stats['coupang']['details'].append(ZoneStats(zone_id, count))

        # Farfetch stats
        for zone_id in self.FARFETCH_ZONE_IDS:
            count = self.fetch_cloudflare_data(zone_id, date_range)
            if count is not None:
                stats['farfetch']['total'] += count
                stats['farfetch']['details'].append(ZoneStats(zone_id, count))

        return stats

def format_datetime(self, dt_str: str) -> str:
    """UTC datetime 문자열을 KST로 변환하여 원하는 형식으로 반환"""
    # UTC 문자열을 datetime 객체로 변환
    dt = datetime.strptime(dt_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
    # UTC를 KST로 변환 (+9시간)
    kst_dt = dt + timedelta(hours=9)
    # 원하는 형식으로 포맷팅
    return kst_dt.strftime('%Y-%m-%d %H:%M:%S')

def main():
    import os
    
    # 환경 변수에서 API 토큰 가져오기
    cf_api_token = os.getenv('CF_API_TOKEN')
    if not cf_api_token:
        print("CF_API_TOKEN 환경변수가 설정되지 않았습니다.")
        cf_api_token = input("Cloudflare API 토큰을 입력하세요: ")

    try:
        # 디버그 모드 선택
        debug_mode = input("디버그 정보를 출력할까요? (y/N): ").lower() == 'y'

        # 날짜 입력 받기
        print("\n조회할 날짜들을 입력하세요 (YYYY-MM-DD 형식, 여러 날짜는 쉼표로 구분)")
        print("예시: 2024-03-15, 2024-03-16, 2024-03-17")
        date_input = input("날짜 입력: ")
        
        # 입력된 날짜들을 처리
        date_strings = [d.strip() for d in date_input.split(',')]
        dates = [parse_date(d) for d in date_strings]
        
        bot_stats = BotManagementStats(cf_api_token, debug_mode)
        
        # 각 날짜별로 통계 수집 및 출력
        for date in dates:
            stats = bot_stats.collect_stats(date)
            
            # 날짜 범위를 KST로 표시
            start_time = bot_stats.format_datetime(bot_stats.get_date_range(date)['start'])
            end_time = bot_stats.format_datetime(bot_stats.get_date_range(date)['end'])
            
            print(f"\n[{start_time} ~ {end_time}] Bot Management Usage Summary")
            
            print("\n🚀 Coupang")
            print(f"• cmapi: {format_count(stats['coupang']['cmapi'])}")
            print(f"• non-cmapi: {format_count(stats['coupang']['non_cmapi'])}")
            print(f"• total: {format_count(stats['coupang']['total'])}")
            
            print("\n🛍️ Farfetch")
            print(f"• Total likely human: {format_count(stats['farfetch']['total'])}")

    except ValueError as ve:
        print(f"날짜 형식 오류: {str(ve)}")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        if debug_mode:
            import traceback
            print(traceback.format_exc())

if __name__ == "__main__":
    main()
