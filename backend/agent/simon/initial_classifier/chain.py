# %%
from typing import List, Union
from langchain_core.messages import HumanMessage

from .prompts import system_prompt_template
from .utils import encode_images


def prepare(files: List[Union[str, bytes]], user_text: str) -> HumanMessage:
    """모델 호출 입력 구성: 시스템 프롬프트 + 유저 텍스트 + 다중 이미지"""
    if not user_text and not files:
        raise ValueError("텍스트 또는 이미지 중 하나는 반드시 제공되어야 합니다.")

    contents = [
        {"type": "text", "text": system_prompt_template},
    ]
    if user_text:
        contents.append({"type": "text", "text": user_text})

    encoded_list = encode_images(files or [])
    for data_url in encoded_list:
        contents.append({
            "type": "image_url",
            "image_url": {"url": data_url}
        })

    return HumanMessage(contents)