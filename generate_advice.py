import os
import json
import traceback

import openai

from config import DEBUG
from prompt.template import ADVICE_TEMPLATE
from utils.utils import print_exception


def prompt_generator(question, answer, retrieval_results):
    ## 객관식 label을 따로따로 넣는 프롬프트 만들기
    ## todo : 주관식 프롬프트도 넣을 수 있게 하기
    # second_prompt = []

    template = ADVICE_TEMPLATE
    prompt = template.format(question=question, answer=answer, retrieval_results=retrieval_results[:2000])

    return prompt


def generate_gpt(gpt_ver, query):
    """Generate a GPT response."""
    messages = [
        {"role": "system", "content": "you are a professional lawyer."},
        {"role": "user", "content": query},
    ]
    completion = openai.chat.completions.create(model=gpt_ver, messages=messages)
    res = completion.choices[0].message.content

    return res


def generate_advice(gpt_ver, prompt):
    try:
        answer = generate_gpt(gpt_ver, prompt)
        return answer
    except Exception as e:
        print_exception()
        if DEBUG:
            traceback.print_exc()
        return "Error: Failed to generate advice."
