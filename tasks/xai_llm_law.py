import os
import time

from celery.utils.log import get_task_logger
from openai import RateLimitError

from utils.langchain_llm import LawLLM
from utils.splitter import find_title_idx_in_document
from utils.utils import load_json

logger = get_task_logger(__name__)

import requests
from celery import Celery

from config import MQ_CELERY_BROKER_URL, MQ_CELERY_BACKEND_URL, CELERY_TASK_NAME, GPT_MODEL, DEBUG, LANGSMITH_API_KEY, \
    OPENAI_API_KEY, LANGCHAIN_PROJECT, APP_ROOT

if DEBUG:
    logger.setLevel('DEBUG')

app = Celery(CELERY_TASK_NAME, broker=MQ_CELERY_BROKER_URL, backend=MQ_CELERY_BACKEND_URL)

# Set Langsmith environment variables
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY  # Update to your API key

# Set OpenAI environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

VERIFY_SSL = False if DEBUG else True

law_llm = LawLLM(model_name=GPT_MODEL)

RETRY_COUNT = 5
RETRY_WAIT = 10


@app.task(bind=True)
def llm_answer(self, uid, idx, paragraphs, question, callback_url):
    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    retry_count = RETRY_COUNT

    has_error = False
    result_dict = None
    error_msg = ""

    while retry_count > 0:
        try:
            result_dict = law_llm.generate_answer_detail(paragraphs, question)
            logger.debug(result_dict)
        except RateLimitError as e:
            print("Hit error")
            has_error = True
            error_msg = e.message
            time.sleep(RETRY_WAIT)
        else:
            has_error = False
            break

        retry_count -= 1

    #
    # 1. uid not exist
    #
    auth_token = ""
    data = {
        "uid": uid,
        "idx": idx,
    }

    if has_error:
        data["error"] = "RateLimitError"
        logger.error(f'({task_id}) RateLimitError: {error_msg}')
    else:
        data.update(result_dict)

    uid_path = os.path.join(APP_ROOT, 'tmp', uid)
    json_file = os.path.join(uid_path, 'outputs.json')

    try:
        parsed_output = load_json(json_file)

        idx_tuple = find_title_idx_in_document(result_dict['title'], parsed_output['document'])
        data['doc_idx_i'] = idx_tuple[0]
        data['doc_idx_j'] = idx_tuple[1]

    except FileNotFoundError:
        pass

    try:
        response = requests.post(callback_url, headers={"Authorization": auth_token}, data=data, verify=VERIFY_SSL)
    except requests.exceptions.ConnectionError as e:
        logger.error(f'({task_id}) ConnectionError: {e}, {callback_url}')
        return False

    # 200 OK
    if response.status_code not in [200, 201]:
        logger.error(f'({task_id}) HTTP Error: {response.status_code} - {response.text}')
        return False

    return data


@app.task(bind=True)
def llm_advice(self, result_dict, uid, idx, question, sangbub, callback_url):
    # type check
    if not isinstance(result_dict, dict):
        logger.error(f'({self.request.id}) result_dict is not a dict: {result_dict}')
        return False

    # shorten the task_id
    task_id = self.request.id
    task_id = task_id[:8]

    answer = result_dict['answer']
    sentence = result_dict['sentence']

    retry_count = RETRY_COUNT

    has_error = False
    result_dict = None
    error_msg = ""

    while retry_count > 0:
        try:
            result_dict = law_llm.generate_advice_detail(question, answer, sangbub)
            logger.debug(result_dict)
        except RateLimitError as e:
            print("Hit error")
            has_error = True
            error_msg = e.message
            time.sleep(RETRY_WAIT)
        else:
            has_error = False
            break

        retry_count -= 1

    #
    # 1. uid not exist
    #
    auth_token = ""

    data = {
        "uid": uid,
        "idx": idx,
    }

    if has_error:
        data["error"] = "RateLimitError"
        logger.error(f'({task_id}) RateLimitError: {error_msg}')
    else:
        data.update(result_dict)

    try:
        response = requests.post(callback_url, headers={"Authorization": auth_token}, data=data, verify=VERIFY_SSL)
    except requests.exceptions.ConnectionError as e:
        logger.error(f'({task_id}) ConnectionError: {e}, {callback_url}')
        return False

    # 200 OK
    if response.status_code not in [200, 201]:
        logger.error(f'({task_id}) Error: {response.status_code} - {response.text}')
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
