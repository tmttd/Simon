import os
import pymongo
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# 환경 변수 로드
load_dotenv()

# pymongo를 통해 mongodb client 생성
MONGODB_URI = os.environ.get('MONGODB_URI')
client = pymongo.MongoClient(MONGODB_URI)

db = client['test']

# 각 collection을 변수에 할당
entries = db['entries']
treatments = db['treatments']


# 1. get_health_data() 생성
def get_health_data() -> dict:
    """
    데이터베이스에서 사용자의 혈당 및 인슐린 정보를 가져옵니다.
    이 도구는 별도의 입력 없이 항상 최신 정보를 반환합니다.
    """

    # 현재 시간 설정(utc 기준)
    now_utc = datetime.now(timezone.utc)
    # 현재 시간 설정(한국 기준)
    now_korea = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat()

    # 1. 최근 혈당 데이터 가져오기
    latest_entry = entries.find_one(sort=[('date', pymongo.DESCENDING)])

    # 2. 최근 5시간 사이의 모든 주사 기록 가져오기
    # 5시간 전 시간 계산
    five_hours_ago = datetime.now(timezone.utc) - timedelta(hours=5)

    # 최근 5시간 내에 생성되었고, 인슐린이나 탄수화물 값이 존재하는 모든 문서 조회
    cursor = treatments.find({
        'created_at': {
            '$gte': five_hours_ago.isoformat()
        },
        '$or': [
            {
                'insulin': {
                    '$exists': True,
                    '$gt': 0
                }
            },
            {
                'carbs': {
                    '$exists': True,
                    '$gt': 0
                }
            }
        ]
    },
        sort=[('created_at', pymongo.DESCENDING)]
    )

    # 3. 최근 인슐린 주사 기록을 리스트로 저장합니다.
    recent_boluses_list = []
    # 4. 최근 탄수화물 섭취 기록을 리스트로 저장합니다.
    recent_carbs_list = []

    for bolus in cursor:
        # DB에서 가져온 created_at 문자열을
        treatment_time_str = bolus.get('created_at')

        # 이를 datetime으로 변환해야 함.
        # Z(Zulu)를 처리하기 위해 00:00으로 바꿔줘야 함.
        treatment_time_utc = datetime.fromisoformat(treatment_time_str.replace('Z', '+00:00'))

        # 시간 차이 계산
        time_difference = now_utc - treatment_time_utc

        # 시간 차이를 초로 바꿨다가 다시 분으로 변환
        minutes_ago = int(time_difference.total_seconds() / 60)

        # 인슐린 값이 None이 아닌 경우에만 리스트에 추가
        insulin = bolus.get('insulin')
        if insulin is not None:
            temp_dict = {"recent_bolus": insulin,
                        "minutes_ago": minutes_ago}
            recent_boluses_list.append(temp_dict)

        # 탄수화물 값이 None이 아닌 경우에만 리스트에 추가
        carbs = bolus.get('carbs')
        if carbs is not None:
            temp_dict_2 = {"recent_carb": carbs,
                          "minutes_ago": minutes_ago}
            recent_carbs_list.append(temp_dict_2)

    # 5. 결과를 LLM이 이해하기 쉽게 포장.
    result = {
        "latest_blood_sugar": latest_entry.get('sgv') if latest_entry else None,
        "time": now_korea,
        "recent_boluses": recent_boluses_list,
        "recent_carbs": recent_carbs_list,
    }

    return result


# 2. IOB(체내 잔존 인슐린) 계산 함수
def IOB_calculator(boluses:list) -> float:
    """
    최근 주사 기록을 입력 받아 체내 잔존 인슐린(IOB)를 계산한다.
    """

    total_IOB = 0

    if boluses:
        for bolus in boluses:
            minutes_ago = int(bolus.get('minutes_ago'))
            dose = int(bolus.get('recent_bolus'))

            # IOB = dose * (0.5 ** (minutes_ago / 120.0))
            IOB = dose * max(0, 1 - (minutes_ago / 300.0))
            total_IOB += IOB

    # 계산된 총 IOB를 소수점 두 자리까지 반올림하여 반환합니다.
    return round(total_IOB, 2)


# 3. 체내 잔존 탄수화물(COB) 계산 함수
def COB_calculator(carbs:list, digest_speed:int = 20) -> float:
    """
    최근 탄수화물 섭취 기록을 입력 받아 위장 내 잔존 탄수화물(COB)을 계산한다.
    """

    total_cob = 0

    if carbs:
        for carb in carbs:
            minutes_ago = int(carb.get('minutes_ago'))
            eaten_carb = int(carb.get('recent_carb'))

            cob = max(0, eaten_carb - (digest_speed / 60) * minutes_ago)
            total_cob += cob

    # 계산된 총 COB를 소수점 두 자리까지 반올림하여 반환합니다.
    return round(total_cob, 2)


# 4. LLM에게 제공하기 위해 데이터를 정제하고 텍스트로 변환.
def prepare_context_data():
    """
    에이전트 호출 전 필요한 혈당과 IOB를 계산하여 입력해주는 함수
    """
    health_data = get_health_data()

    time = health_data['time'][11:13] + "시 " + health_data['time'][14:16] + "분"

    iob = IOB_calculator(health_data['recent_boluses'])

    cob = COB_calculator(health_data['recent_carbs'])

    return {
        'time': time,
        "blood_sugar": (health_data.get('latest_blood_sugar')),
        'iob': (iob),
        'cob': (cob),
    }