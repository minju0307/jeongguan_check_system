import os

from celery.utils.log import get_task_logger

from utils.langchain_llm import LawLLM

logger = get_task_logger(__name__)

import requests
from celery import Celery

from config import MQ_CELERY_BROKER_URL, MQ_CELERY_BACKEND_URL, CELERY_TASK_NAME, GPT_MODEL, DEBUG, LANGSMITH_API_KEY, \
    OPENAI_API_KEY

app = Celery(CELERY_TASK_NAME, broker=MQ_CELERY_BROKER_URL, backend=MQ_CELERY_BACKEND_URL)

# Set Langsmith environment variables
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = f"XAI_Jeongguan - CeleryWorker"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY  # Update to your API key

# Set OpenAI environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

VERIFY_SSL = False if DEBUG else True

law_llm = LawLLM(model_name=GPT_MODEL)


@app.task(bind=True)
def llm_answer(self, uid, idx, paragraphs, q, callback_url):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    result_dict = law_llm.generate_answer(paragraphs, q)

    logger.debug(result_dict)

    #
    # 1. uid not exist
    #
    auth_token = ""
    data = {
        "uid": uid,
        "idx": idx,
    }
    data.update(result_dict)

    try:
        response = requests.post(callback_url, headers={"Authorization": auth_token}, data=data, verify=VERIFY_SSL)
    except requests.exceptions.ConnectionError as e:
        logger.error(f'({task_id}) ConnectionError: {e}, {callback_url}')
        return False

    # 200 OK
    if response.status_code != 200:
        logger.error(f'({task_id}) Error: {response.status_code} - {response.text}')
        return False

    result = response.json()
    code = result.get('code')
    msg = result.get('msg')

    if code != 200:
        logger.error(f'({task_id}) Error: {code} - {msg}')
        return False

    return result_dict


@app.task(bind=True)
def llm_advice(self, result_dict, uid, idx, question, sangbub, callback_url):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    answer = result_dict['answer']
    sentence = result_dict['sentence']

    result_dict = law_llm.generate_advice(question, answer, sangbub)

    logger.debug(result_dict)

    #
    # 1. uid not exist
    #
    auth_token = ""

    data = {
        "uid": uid,
        "idx": idx,
    }
    data.update(result_dict)

    try:
        response = requests.post(callback_url, headers={"Authorization": auth_token}, data=data, verify=VERIFY_SSL)
    except requests.exceptions.ConnectionError as e:
        logger.error(f'({task_id}) ConnectionError: {e}, {callback_url}')
        return False

    # 200 OK
    if response.status_code != 200:
        logger.error(f'({task_id}) Error: {response.status_code} - {response.text}')
        return False

    result = response.json()
    code = result.get('code')
    msg = result.get('msg')

    if code != 200:
        logger.error(f'({task_id}) Error: {code} - {msg}')
        return False

    return result_dict


if __name__ == "__main__":
    # set worker options
    worker_options = {
        'loglevel': 'INFO',
        'traceback': True,
        'concurrency': 30,
    }

    # set queue
    app.conf.task_default_queue = CELERY_TASK_NAME

    worker = app.Worker(**worker_options)

    # start worker
    worker.start()
