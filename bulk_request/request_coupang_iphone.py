import requests
import random
import time

# 상품 ID 리스트
product_ids = ['8335434837', '8335434969', '8335434891', '8335434673']

# vendorItemId 리스트
vendor_item_ids = [
    '91088074282', '91088074265', '91088074397', '91088074335', '91088074446', 
    '91088074405', '91088074310', '91088074296', '91088074228', '91088074378', 
    '91088074353', '91088074424', '91088074242', '91088074436', '91088074324', 
    '91088074905', '91088074938', '91088074948', '91088074932', '91088074925', 
    '91088074871', '91088074875', '91088074976', '91088074881', '91088074888', 
    '91088074914', '91088074955', '91088074982', '91088074968', '91088074897', 
    '91088074520', '91088074618', '91088074593', '91088074547', '91088074492', 
    '91088074648', '91088074576', '91088074657', '91088074682', '91088074511', 
    '91088074533', '91088074501', '91088074607', '91088074634', '91088074560', 
    '91088074669', '91088073973', '91088073981', '91088073935', '91088073925', 
    '91088073919', '91088073942', '91088073904', '91088073964', '91088073913', 
    '91088073955', '91088073889', '91088073894'
]

# 기본 URL
base_url = "https://www.coupang.com/vp/products/"

# PCID 생성 함수
def generate_pcid():
    return ''.join([str(random.randint(0, 9)) for _ in range(49)])

print("요청 시작")

# 10번 요청
for i in range(10):
    # 랜덤하게 product_id와 vendor_item_id 선택
    product_id = random.choice(product_ids)
    vendor_item_id = random.choice(vendor_item_ids)
    
    # URL 생성
    url = f"{base_url}{product_id}?vendorItemId={vendor_item_id}"
    
    # PCID 생성
    pcid = generate_pcid()
    
    # 쿠키 설정
    cookies = {'Cookie': f'PCID={pcid};'}
    
    print(f"\n요청 #{i+1}")
    print(f"URL: {url}")
    print(f"쿠키: {cookies}")
    
    # 요청 시작 시간
    start_time = time.time()
    
    # 요청 보내기 (쿠키 포함)
    response = requests.get(url, cookies=cookies)
    
    # 요청 종료 시간
    end_time = time.time()
    
    # 응답 시간 계산 (밀리초 단위)
    response_time = (end_time - start_time) * 1000
    
    # 결과 출력
    print(f"응답 코드: {response.status_code}")
    print(f"응답 시간: {response_time:.2f} ms")
    print("-" * 50)
    
    # 요청 간 잠시 대기 (서버에 부하를 주지 않기 위해)
    time.sleep(0.3)

print("요청 완료")
