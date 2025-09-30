from langchain_core.tools import tool
from langchain_upstage import UpstageEmbeddings
from langchain_chroma import Chroma
from .settings import QUERY_EMBEDDING_MODEL_NAME, PERSIST_DIRECTORY, COLLECTION_NAME

# nutrition_retriever 정의
query_embeddings = UpstageEmbeddings(model=QUERY_EMBEDDING_MODEL_NAME)

# vectorDB 로드
vectorDB = Chroma(
    persist_directory=PERSIST_DIRECTORY,
    embedding_function=query_embeddings,
    collection_name=COLLECTION_NAME
)

# retrievr 객체 생성
nutrition_retriever = vectorDB.as_retriever(search_kwargs={'k':3})

# RAG health_Check
print(nutrition_retriever.invoke("삽겹살 구이"))

# tools(도구 가방)
tools = []

# Document Retriever 도구(영양 성분 쿼리)
# 추후에 BM25와 결합한 Hybrid Retriever로 바꿀 필요 있음.
@tool
def nutrition_retriever_tool(query: str) -> str:
    """
    음식의 영양 정보를 확인할 때 사용합니다.
    '짬뽕', '김치볶음밥', '포도'과 같은 음식 이름 또는 원재료명이 들어왔을 때 사용합니다.
    100g 기준값이므로, 1인분용량에 맞게 곱해서 적절히 사용합니다.
    """

    datas = nutrition_retriever.invoke(query)

    if not datas:
        return "검색 결과, 해당 음식에 대한 정보를 찾을 수 없습니다."
    
    formatted_results = []

    for data in datas:
        food_name = data.metadata.get('식품명', '')
        carbs = data.metadata.get('탄수화물(g)', '')
        protein = data.metadata.get('단백질(g)', '')
        fat = data.metadata.get('지방(g)', '')
        standard_weight = data.metadata.get('기준량', '정보없음')
        serving_weight = data.metadata.get('1인분용량', '정보없음')
        # 계산의 정확도를 죽이는 듯.
        # one_weight = data.metadata.get('개당용량', '정보없음')

        result_str = f"""
음식명: {food_name}
탄수화물: {carbs}, 단백질: {protein}, 지방: {fat}
기준량: {standard_weight}, 1인분용량: {serving_weight}
"""
        formatted_results.append(result_str)
        
    return "\n\n".join(formatted_results)

tools.append(nutrition_retriever_tool)


# 2. 인슐린 계산 함수를 만들어 도구로 제공합니다.
@tool
def insulin_calculation(
    carbs: float = 0,
    blood_sugar: float = 120, 
    iob: float = 0, 
    exercise_factor: float = 1.0,
    morning_factor: float = 1.0,
    stress_factor: float = 1.0,
    ill_factor: float = 1.0,
    ) -> str:
    """
    사용자와의 대화를 통해 모든 정보 수집과 상황 판단이 끝났을 때, 
    결정된 보정 계수(factor)들을 이용해 최종 인슐린 용량을 '계산'만 할 때 사용하는 도구입니다.
    예를 들어, 운동으로 20% 감량이 필요하다고 판단되면 exercise_factor=0.8을 인자로 넣어 호출해야 합니다.
    모든 factor의 기본값은 1.0 (영향 없음)입니다.
    """

    ICR = 6.5
    CF = 35
    target = 120


    if carbs > 0:
        meal_bolus = round(carbs / ICR)
    else:
        meal_bolus = 0

    if blood_sugar >= 155:
        treatment_bolus = round((blood_sugar-target) / CF)
    else:
        treatment_bolus = 0

    if (meal_bolus + treatment_bolus - iob) <= 0:
        temp_total_bolus = 0
    else:
        temp_total_bolus = (meal_bolus + treatment_bolus - iob)

    # 각종 계수에 따른 보정
    final_total_bolus = temp_total_bolus * exercise_factor * morning_factor * stress_factor * ill_factor


    response = f"""계산 결과:
기본 인슐린: {temp_total_bolus} 단위 (식사량, 현재 혈당, IOB 고려)
- 적용된 보정 계수: 운동({exercise_factor}), 아침({morning_factor}), 스트레스({stress_factor}), 질병({ill_factor})
최종 권장 인슐린: {round(final_total_bolus, 1)} 단위
"""
    
    return response

tools.append(insulin_calculation)