#!/usr/bin/env python3
"""
비동기 부하 테스트 스크립트
동시에 여러 요청을 보내서 서버 성능 확인
"""
import asyncio
import aiohttp
import time
from datetime import datetime

# 설정
BASE_URL = "https://www.simon.ai.kr"  # 또는 "http://localhost"
LOGIN_URL = f"{BASE_URL}/api/auth/token/"
CHAT_URL = f"{BASE_URL}/api/chat/ask/"

# 테스트 계정 (실제 계정으로 변경)
EMAIL = "test@test.com"
PASSWORD = "KXNipo285@"

# 부하 테스트 설정
NUM_CONCURRENT_REQUESTS = 50  # 동시 요청 수
TEST_MESSAGE = "안녕하세요, 이것은 부하 테스트 메시지입니다. 아무런 학습 세션이나 자유롭게 생성해주세요."


async def login(session):
    """로그인해서 access token 받기"""
    async with session.post(LOGIN_URL, json={
        "email": EMAIL,
        "password": PASSWORD
    }) as response:
        if response.status == 200:
            data = await response.json()
            return data.get('access')
        else:
            print(f"로그인 실패: {response.status}")
            return None


async def send_chat_request(session, token, request_id):
    """채팅 요청 보내기"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    try:
        async with session.post(CHAT_URL, json={
            "message": f"{TEST_MESSAGE} (요청 #{request_id})",
            "thread_id": None,
            "session_id": None
        }, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
            
            end_time = time.time()
            duration = end_time - start_time
            
            status = response.status
            if status == 200:
                data = await response.json()
                print(f"✅ 요청 #{request_id:2d} | 성공 | {duration:.2f}초 | 응답길이: {len(data.get('response', ''))}자")
                return {'success': True, 'duration': duration, 'request_id': request_id}
            else:
                error_text = await response.text()
                print(f"❌ 요청 #{request_id:2d} | 실패 ({status}) | {duration:.2f}초")
                return {'success': False, 'duration': duration, 'request_id': request_id, 'status': status}
                
    except asyncio.TimeoutError:
        end_time = time.time()
        duration = end_time - start_time
        print(f"⏱️  요청 #{request_id:2d} | 타임아웃 | {duration:.2f}초")
        return {'success': False, 'duration': duration, 'request_id': request_id, 'timeout': True}
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 요청 #{request_id:2d} | 에러: {str(e)[:50]} | {duration:.2f}초")
        return {'success': False, 'duration': duration, 'request_id': request_id, 'error': str(e)}


async def run_load_test():
    """부하 테스트 실행"""
    print("=" * 70)
    print(f"🚀 부하 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 서버: {BASE_URL}")
    print(f"👥 동시 요청 수: {NUM_CONCURRENT_REQUESTS}")
    print("=" * 70)
    
    async with aiohttp.ClientSession() as session:
        # 1. 로그인
        print("\n🔐 로그인 중...")
        token = await login(session)
        if not token:
            print("❌ 로그인 실패. 테스트 중단.")
            return
        print("✅ 로그인 성공!")
        
        # 2. 동시 요청 보내기
        print(f"\n📤 {NUM_CONCURRENT_REQUESTS}개의 동시 요청 전송 중...\n")
        
        overall_start = time.time()
        
        # 모든 요청을 동시에 실행
        tasks = [
            send_chat_request(session, token, i+1) 
            for i in range(NUM_CONCURRENT_REQUESTS)
        ]
        results = await asyncio.gather(*tasks)
        
        overall_end = time.time()
        total_duration = overall_end - overall_start
        
        # 3. 결과 분석
        print("\n" + "=" * 70)
        print("📊 테스트 결과")
        print("=" * 70)
        
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        print(f"\n✅ 성공: {len(successful)}/{NUM_CONCURRENT_REQUESTS}")
        print(f"❌ 실패: {len(failed)}/{NUM_CONCURRENT_REQUESTS}")
        print(f"⏱️  전체 소요 시간: {total_duration:.2f}초")
        
        if successful:
            durations = [r['duration'] for r in successful]
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            print(f"\n⏱️  응답 시간:")
            print(f"   - 평균: {avg_duration:.2f}초")
            print(f"   - 최소: {min_duration:.2f}초")
            print(f"   - 최대: {max_duration:.2f}초")
            
            # 동시성 효과 계산
            sequential_time = sum(durations)
            speedup = sequential_time / total_duration
            print(f"\n🚀 동시성 효과:")
            print(f"   - 순차 실행 예상 시간: {sequential_time:.2f}초")
            print(f"   - 실제 소요 시간: {total_duration:.2f}초")
            print(f"   - 속도 향상: {speedup:.1f}배")
        
        if failed:
            print(f"\n❌ 실패한 요청들:")
            for r in failed[:5]:  # 처음 5개만 출력
                reason = "타임아웃" if r.get('timeout') else f"상태코드 {r.get('status', 'N/A')}"
                print(f"   - 요청 #{r['request_id']}: {reason}")
        
        print("\n" + "=" * 70)
        
        # 4. 평가
        success_rate = len(successful) / NUM_CONCURRENT_REQUESTS * 100
        print(f"\n🎯 종합 평가:")
        print(f"   - 성공률: {success_rate:.1f}%")
        
        if success_rate >= 90 and total_duration < avg_duration * 1.5:
            print(f"   - 결과: ✨ 우수 (비동기가 잘 작동하고 있습니다!)")
        elif success_rate >= 70:
            print(f"   - 결과: 👍 양호 (대부분 정상 작동)")
        else:
            print(f"   - 결과: ⚠️  개선 필요")
        
        print("=" * 70)


if __name__ == "__main__":
    print("\n⚙️  aiohttp 설치 확인 중...")
    try:
        import aiohttp
        print("✅ aiohttp 설치됨")
    except ImportError:
        print("❌ aiohttp가 설치되지 않았습니다.")
        print("📦 설치 명령어: pip install aiohttp")
        exit(1)
    
    # 테스트 실행
    asyncio.run(run_load_test())

