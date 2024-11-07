import requests
import time
import logging
from http.cookies import SimpleCookie
import random

# 로깅 설정
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='request_log.txt',
                    filemode='w')

# 콘솔에도 로그 출력
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# 고정된 쿠키 문자열 (PCID 제외)
cookie_string = "sid=a945715636fa467d98cfaae723a409551d37d13d; overrideAbTestGroup=%5B%5D; MARKETID=21868289239461214812586; x-coupang-accept-language=ko-KR; x-coupang-target-market=KR; __cf_bm=CZdjaNq5PxHv51CCHhI7yd6kWPVdlvSKBiDQX2ar4bc-1725514833-1.0.1.1-Z9FWohRK7J_qPwp3sqd43noYLRMovJGLp7ffNNKJTSujJDe7Tiydc66Hlb_zLbOGS5V6PsHtz._bHMqa0emczg; *fbp=fb.1.1725514841787.28740479256780913; cto*bundle=9K_jO18ya2Q2aHVKalExa2NNekVPWFU2bnolMkZ4a1VQQ3Bidk4ycVJSNEcxSlZBMHg2SUlmb1FFdmpSSWRtTWRLN1FsU1ZObiUyQmhPTGMyOWJIWDZGRG0zUmlGekRSeEYwZEIyZVU5VjZPdDY1eG9DZ2RVWDRVUDRIS1FwMnZhMFg3dUJ3dEElMkJ2ciUyRkd2UFE5NmFDMSUyQmdNT0VQWWFnJTNEJTNE; cf_clearance=oYLRsqn4tR3woYSnNJ3ob2.J9OHEHDNPdo4nluvEfF8-1725514842-1.2.1.1-QYRwQkvkf5hG3zQfMnstrzupLGj0ed3ay2gMiEMXNAApBFdyeTdrXdQXCa5PgtFwuNVJV9jaDuCw7PzzDjHvgSWees34l0I2wnxwke3K6uhFW6AtF9n0ejFxeC0sWMlGeDS1YgF9ktpl5YYNlkxnFN7qNZNmZqolswV8SDmUaxgfPrA5p5bEChkfyD39ArFOE8qbjrG0ekl8NI64kA0SM_NHTabFpvmfxPTA9krMZlO1XMz7lrD_OrZ5tn36n_TkqkBe2mrmiYnwncJ6OC_AOpX7b3MH3FkcIk72r9yU9F2_CrH_H02X6.zwlfVy4UTW189z.JrM_lRsTPVap2VVNbVG5uMjl.UYnbTdEKtnoIJizSyD5ZGAe5XmcRSNBbBvwzvbU1Hgj3YiSALC.4uc2w; baby-isWide=small"
base_url = "https://hakang.cflare.kr/vp/products/"
num_requests = 1501

# PCID 생성 함수
def generate_pcid():
    return ''.join([str(random.randint(0, 9)) for _ in range(20)])

# 3개의 PCID 생성
pcid_list = [generate_pcid() for _ in range(3)]

# 쿠키 문자열을 파싱
cookie = SimpleCookie()
cookie.load(cookie_string)

# 세션 생성 및 쿠키 설정
session = requests.Session()
for key, morsel in cookie.items():
    session.cookies.set(key, morsel.value)

logging.info("Using fixed cookies (except PCID):")
for key, value in session.cookies.items():
    if key != 'PCID':
        logging.info(f"  {key}: {value}")

logging.info("Generated PCIDs:")
for i, pcid in enumerate(pcid_list):
    logging.info(f"  PCID {i+1}: {pcid}")

for i in range(num_requests):
    try:
        # 3개의 PCID를 번갈아가며 사용
        current_pcid = pcid_list[i % 3]
        session.cookies.set('PCID', current_pcid)
        
        # 9자리 랜덤 숫자 생성
        random_product_id = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        
        # URL 생성
        url = f"{base_url}{random_product_id}"
        
        start_time = time.time()
        response = session.get(url, timeout=10)  # 10초 타임아웃 설정
        end_time = time.time()
        
        logging.info(f"Request {i+1}: "
                     f"URL = {url}, "
                     f"PCID = {current_pcid}, "
                     f"Status Code = {response.status_code}, "
                     f"Time = {end_time - start_time:.2f}s")
        
        # 응답 내용 로깅 (선택적)
        logging.debug(f"Response content: {response.text[:200]}...")  # 처음 200자만 로깅
    except requests.exceptions.RequestException as e:
        logging.error(f"Request {i+1} failed: {str(e)}")
    
    time.sleep(0.1)  # 0.5초 대기

logging.info("All requests completed.")
