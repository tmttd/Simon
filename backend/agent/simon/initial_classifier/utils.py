# %%
from io import BytesIO
from typing import List, Union, Optional
from PIL import Image
import base64

def _encode_pil_image(image: Image.Image, format: str = "PNG") -> str:
    """PIL 이미지 객체를 Data URL(Base64)로 인코딩합니다."""
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    buffer = BytesIO()
    image.save(buffer, format=format)
    encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/{format.lower()};base64,{encoded_string}"


def encode_image(image_path: str, format: str = "PNG") -> Optional[str]:
    """단일 이미지 파일 경로를 Data URL(Base64)로 인코딩합니다.(기존 호환)"""
    try:
        with Image.open(image_path) as image:
            return _encode_pil_image(image, format=format)
    except FileNotFoundError:
        print(f"오류: '{image_path}'를 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"이미지 처리 중 오류 발생: {e}")
        return None


def encode_image_any(file: Union[str, bytes, BytesIO], format: str = "PNG") -> Optional[str]:
    """경로 또는 바이트/버퍼 입력을 Data URL(Base64)로 인코딩합니다."""
    try:
        if isinstance(file, str):
            with Image.open(file) as image:
                return _encode_pil_image(image, format=format)
        elif isinstance(file, bytes):
            with Image.open(BytesIO(file)) as image:
                return _encode_pil_image(image, format=format)
        elif isinstance(file, BytesIO):
            file.seek(0)
            with Image.open(file) as image:
                return _encode_pil_image(image, format=format)
        else:
            print("지원하지 않는 이미지 입력 타입입니다.")
            return None
    except Exception as e:
        print(f"이미지 처리 중 오류 발생: {e}")
        return None


def encode_images(files: List[Union[str, bytes, BytesIO]], format: str = "PNG", max_images: int = 10) -> List[str]:
    """다중 이미지를 Data URL(Base64) 리스트로 인코딩합니다."""
    if not files:
        return []
    results: List[str] = []
    for file in files[:max_images]:
        encoded = encode_image_any(file, format=format)
        if encoded:
            results.append(encoded)
    return results
# %%
