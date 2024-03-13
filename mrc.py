import traceback

import openai

from config import DEBUG
from prompt.template import ANSWER_TEMPLATE
from utils.utils import print_exception


def generate_gpt(gpt_ver, query):
    """Generate a GPT response."""
    messages = [{"role": "user", "content": query}]
    completion = openai.chat.completions.create(model=gpt_ver, messages=messages)
    res = completion.choices[0].message.content

    return res


def generate_answer(gpt_ver, jeongguan, question):
    template = ANSWER_TEMPLATE

    try:
        query = template.format(paragraph=jeongguan, question=question)
        result = generate_gpt(gpt_ver, query)

        return result

    except Exception as e:
        print_exception()
        if DEBUG:
            traceback.print_exc()
        return "Error: Failed to generate answer."
