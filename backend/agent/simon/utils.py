import base64
from io import BytesIO
from typing import List, Union, Optional
from PIL import Image
from langchain_core.messages import HumanMessage

def _encode_pil_image(image: Image.Image, format: str = "PNG") -> str:
    """PIL 이미지 객체를 Data URL(Base64)로 인코딩합니다."""
    # RGBA 모드 이미지는 LLM이 지원하는 RGB로 변환 (알파 채널 제거)
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    buffer = BytesIO()
    image.save(buffer, format=format)
    encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/{format.lower()};base64,{encoded_string}"


def encode_image_any(file: Union[str, bytes, BytesIO], format: str = "PNG") -> Optional[str]:
    """
    다양한 형식의 이미지 입력을 Data URL(Base64)로 인코딩합니다.
    (파일 경로, 바이트 스트림, BytesIO 객체)
    """
    try:
        if isinstance(file, str): # 파일 경로
            with Image.open(file) as image:
                return _encode_pil_image(image, format=format)
        elif isinstance(file, bytes): # 바이트 스트림
            with Image.open(BytesIO(file)) as image:
                return _encode_pil_image(image, format=format)
        elif isinstance(file, BytesIO): # BytesIO 객체
            file.seek(0) # 스트림 시작점으로 이동하여 PIL이 읽을 수 있도록 함
            with Image.open(file) as image:
                return _encode_pil_image(image, format=format)
        else:
            print(f"경고: 지원하지 않는 이미지 입력 타입입니다: {type(file)}")
            return None
    except FileNotFoundError:
        print(f"오류: 이미지 파일 '{file}'를 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"오류: 이미지 처리 중 오류 발생: {e}")
        return None


def encode_images(files: List[Union[str, bytes, BytesIO]], format: str = "PNG", max_images: int = 10) -> List[str]:
    """
    다중 이미지를 Data URL(Base64) 리스트로 인코딩합니다.
    최대 'max_images' 개수만큼만 처리합니다.
    """
    if not files:
        return []
    results: List[str] = []
    for file in files[:max_images]:
        encoded = encode_image_any(file, format=format)
        if encoded:
            results.append(encoded)
    return results

def prepare_contents(files: Optional[List[Union[str, bytes, BytesIO]]], user_text: Optional[str]) -> list:
    """
    사용자 입력(텍스트, 이미지)을 받아 LLM이 이해할 수 있는 content 리스트로 변환합니다.
    (시스템 프롬프트는 여기서 포함하지 않습니다.)

    Args:
        files: 이미지 파일 경로, 바이트 스트림, 또는 BytesIO 객체 리스트.
        user_text: 사용자 텍스트 입력.

    Returns:
        LLM의 content 필드에 들어갈 딕셔너리 리스트.

    Raises:
        ValueError: 텍스트 또는 이미지 중 어느 것도 제공되지 않았을 경우.
    """
    if not user_text and not files:
        raise ValueError("텍스트 또는 이미지 중 하나는 반드시 제공되어야 합니다.")

    contents = []
    if user_text:
        contents.append({"type": "text", "text": user_text})

    encoded_list = encode_images(files or [])
    for data_url in encoded_list:
        contents.append({
            "type": "image_url",
            "image_url": {"url": data_url}
        })

    return contents

print("✅ utils.py: 이미지 처리 및 LLM 콘텐츠 준비 유틸리티 함수 로드 완료.")