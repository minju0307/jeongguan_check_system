import openai


def generate_gpt(gpt_ver, query):
    """Generate a GPT response."""
    messages = [{"role": "user", "content": query}]
    response = openai.ChatCompletion.create(model=gpt_ver, messages=messages)
    res = response["choices"][0]["message"]["content"]

    return res


def generate_answer(gpt_ver, jeongguan, question):
    template = """정관 문서: {paragraph}
    질문: {question}
    ===
    너는 변호사로서, 회사 정관을 검토해야 한다. 선생님께 정관 문서를 힌트로 받았다. 다음 질문에 대한 답은? 진위형 질문이면 예, 또는 아니오로 대답하고, 주관식 질문이면 한 줄로 대답하시오.
    """

    try:
        query = template.format(paragraph=jeongguan, question=question)
        result = generate_gpt(gpt_ver, query)

        return result

    except:
        print(f"\nmrc_error\n\n")
