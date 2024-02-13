from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import requests
from celery import Celery

from config import MQ_CELERY_BROKER_URL, MQ_CELERY_BACKEND_URL, CELERY_TASK_NAME, GPT_MODEL, DEBUG
from main import get_advice
from mrc import generate_answer

app = Celery(CELERY_TASK_NAME, broker=MQ_CELERY_BROKER_URL, backend=MQ_CELERY_BACKEND_URL)

# set OpenAI API key
import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
VERIFY_SSL = False if DEBUG else True

@app.task(bind=True)
def llm_answer(self, uid, idx, paragraphs, q, callback_url):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    # print(f'({task_id}) x: {x}, y: {y}')
    answer = generate_answer(GPT_MODEL, "\n".join(paragraphs), q)
    logger.debug(answer)

    #
    # 1. uid not exist
    #
    auth_token = ""
    data = {
        "uid": uid,
        "idx": idx,
        "answer": answer
    }

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

    return answer


@app.task(bind=True)
def llm_advice(self, answer, uid, idx, q, sangbub, callback_url):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    # print(f'({task_id}) x: {x}, y: {y}')
    advice = get_advice(GPT_MODEL, q, answer, sangbub)
    logger.debug(advice)

    #
    # 1. uid not exist
    #
    auth_token = ""

    data = {
        "uid": uid,
        "idx": idx,
        "advice": advice
    }

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

    return advice


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
