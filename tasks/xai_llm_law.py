from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

from urllib.parse import urljoin

import requests
from celery import Celery

from config import MQ_CELERY_BROKER_URL, MQ_CELERY_BACKEND_URL, SERVICE_URL, CELERY_TASK_NAME
from main import get_advice
from mrc import generate_answer

app = Celery(CELERY_TASK_NAME, broker=MQ_CELERY_BROKER_URL, backend=MQ_CELERY_BACKEND_URL)

# set OpenAI API key
import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY


@app.task(bind=True)
def llm_answer(self, uid, idx, paragraphs, q):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    gpt_ver = "gpt-4-1106-preview"
    # print(f'({task_id}) x: {x}, y: {y}')
    answer = generate_answer(gpt_ver, "\n".join(paragraphs), q)
    print(answer)

    # callback
    callback_url = urljoin(SERVICE_URL, 'callback_answer')

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
        response = requests.post(callback_url, headers={"Authorization": auth_token}, data=data)
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
def llm_advice(self, answer, uid, idx, q, sangbub):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    gpt_ver = "gpt-4-1106-preview"
    # print(f'({task_id}) x: {x}, y: {y}')
    advice = get_advice(gpt_ver, q, answer, sangbub)
    print(advice)

    # callback
    callback_url = urljoin(SERVICE_URL, 'callback_advice')

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
        response = requests.post(callback_url, headers={"Authorization": auth_token}, data=data)
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


if __name__ == "__main__":
    # set worker options
    worker_options = {
        'loglevel': 'INFO',
        'traceback': True,
        'concurrency': 10,
    }

    # set queue
    app.conf.task_default_queue = CELERY_TASK_NAME

    worker = app.Worker(**worker_options)

    # start worker
    worker.start()
