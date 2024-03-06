import os
from datetime import datetime
import json
import random
from pprint import pprint
import unittest
from shutil import rmtree
from urllib.parse import urljoin

import requests

from config import APP_ROOT, SERVICE_URL
from error_code import ErrorCode
from tests.base import BaseTest


class TestAPI(unittest.TestCase, BaseTest):
    def setUp(self):
        self.url = SERVICE_URL
        self.auth_token = "kimandhong"

    def test_paragraph_split(self):
        url = urljoin(self.url, "/upload")

        data = {
            "id": "0000",
            "text": "⑤ 전환으로 인하여 발행하는 주식에 대한 이익의 배당과 전환사채에 대한 이자의 지급에 관하여는 제13조의 규정을 준용한다. 제18조(신주인수권부사채의 발행) ① 본 회사는 이사회의 결의로 사채의 액면총액이 오천억원을 초과하지 않는 범위 내에서 주주 또는 주주 이외의 자에게 신주인수권부사채를 발행할 수 있다. ② 신주인수를 청구할 수 있는 금액은 사채의 액면총액을 초과하지 않는 범위 내에서 이사회가 정한다. ③ 신주인수권의 행사로 발행하는 주식은 보통주식으로 하고 그 발행가액은 액면금액 또는 그 이상의 가액으로 사채 발행 시 이사회가 정한다. ④ 신주인수권을 행사할 수 있는 기간은 당해 사채발행일 익일부터 그 상환기일의 1일전까지로 한다. 다만, 위 기간 내에서 관계법규에 따라 이사회의 결의로 신주인수권의 행사기간을 조정할 수 있다. ⑤ 신주인수권의 행사로 인하여 발행하는 주식에 대한 이익의 배당에 관하여는 제12조의 규정을 준용한다. 제19조(사채발행에 관한 준용규정) 제9조, 제10조의 규정은 사채발행의 경우에 준용한다. 제4장 주주총회 제20조(소집) ① 회사의 주주총회는 정기주주총회와 임시주주총회로 한다. ② 정기주주총회는 매 결산기 종료 후 3월이내에, 임시주주총회는 필요에 따라 이사회의 결의, 기타 법규에 정한 바에 의하여 대표이사가 소집한다. 제21조(총회의 소집) ① 주주총회의 소집은 법령에 다른 규정이 있는 경우를 제외하고는 이사회의 결의에 따라 대표이사가 이를 소집한다. 대표이사의 유고시에는 이사회규정에서 정한 순으로 그 직무를 대행한다. ② 주주총회를 소집할 때에는 법령에 다른 정함이 있는 경우를 제외하고 회의 예정일 2주간 전에 각 주주에게 개별통지를 하여야 한다. 다만, 위 기간은 회의 전에 모든 주주의 서면동의를 얻어 단축할 수 있다. 통지서에는 회의에서 처리될 안건과 회의 개회 일시 및 장소를 명기하여야 한다.",
        }

        response = requests.post(url, headers={"Authorization": self.auth_token}, json=data, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def test_get_paragraph(self):
        doc_id = "0000"

        url = urljoin(self.url, "/paragraph?doc_id=" + doc_id)

        response = requests.get(url, headers={"Authorization": self.auth_token}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def test_get_checklist(self):
        checklist_id = "1"

        url = urljoin(self.url, "/checklist?checklist_id=" + checklist_id)

        response = requests.get(url, headers={"Authorization": self.auth_token}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def test_get_sangbub(self):
        sangbub_id = "30"

        url = urljoin(self.url, "/reference_sangbub?sangbub_id=" + sangbub_id)

        response = requests.get(url, headers={"Authorization": self.auth_token}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def test_get_mapping_paragraph(self):
        doc_id = "0000"

        url = urljoin(self.url, "/qna/question_paragraph?doc_id=" + doc_id)

        response = requests.get(url, headers={"Authorization": self.auth_token}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def test_get_mrc_answer(self):
        doc_id = "0000"
        checklist_id = "0"

        url = urljoin(self.url, "/qna/mrc_answer?doc_id=" + doc_id + "&checklist_id=" + checklist_id)

        response = requests.get(url, headers={"Authorization": self.auth_token}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def test_get_checklist_sangbub(self):
        doc_id = "0000"
        checklist_id = "0"

        url = urljoin(self.url, "/advice/question_sangbub?doc_id=" + doc_id + "&checklist_id=" + checklist_id)

        response = requests.get(url, headers={"Authorization": self.auth_token}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        pprint(res)

    def request_api(self, url, data, files=None):
        if files:
            response = requests.post(url, headers={"Authorization": self.auth_token}, data=data, files=files,
                                     verify=False)
        else:
            response = requests.post(url, headers={"Authorization": self.auth_token}, json=data, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        return res

    def test_analyze(self):
        url = urljoin(self.url, "analyze")

        data = {}

        # Invalid document
        test_file = os.path.join(APP_ROOT, 'input_samples/65e6964faef64e7ba7e76bae.txt')

        res = self.request_api(url, data, files={'file': open(test_file, 'rb')})
        result_code = res['code']

        self.assertEqual(ErrorCode.INVALID_DOCUMENT.code, result_code)

        # Valid document
        test_file = os.path.join(APP_ROOT, 'input_samples/1.txt')

        res = self.request_api(url, data, files={'file': open(test_file, 'rb')})
        result_code = res['code']
        self.assertEqual(ErrorCode.SUCCESS.code, result_code)

        result_data = res['data']
        self.logger.debug(f'result_data: {result_data}')

        # validate keys in response
        self.assertIn('checklist_questions', result_data)
        self.assertIn('doc_paragraphs', result_data)
        self.assertIn('document', result_data)
        self.assertIn('mapping_paragraphs', result_data)
        self.assertIn('uid', result_data)

    def test_analyze_q_ids(self):
        url = urljoin(self.url, "analyze")
        uid = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))

        data = {
            'uid': uid,
            'q_ids': '3,4'
        }

        test_file = os.path.join(APP_ROOT, 'input_samples/1.txt')

        response = requests.post(url, headers={"Authorization": self.auth_token}, data=data,
                                 files={'file': open(test_file, 'rb')}, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()
        result_data = res['data']

        # validate keys in response
        self.assertIn('uid', result_data)
        self.assertIn('checklist_questions', result_data)
        self.assertNotIn('doc_paragraphs', result_data)
        self.assertNotIn('document', result_data)
        self.assertNotIn('mapping_paragraphs', result_data)

        pprint(res)

    def test_callback(self):
        url = urljoin(self.url, "callback_result")
        uid = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))

        #
        # 1. uid not exist
        #
        data = {
            "uid": uid,
            "idx": 1,
            "answer": "테스트 결과입니다."
        }
        response = requests.post(url, headers={"Authorization": self.auth_token}, data=data, verify=False)

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()

        self.assertEqual(ErrorCode.NOT_EXIST_UID.code, res['code'])

        #
        # 2. uid exist - callback_answer
        #

        # create directory for uid
        dest_dir = os.path.join(APP_ROOT, 'tmp', uid)
        os.makedirs(dest_dir, exist_ok=True)

        response = requests.post(url, headers={"Authorization": self.auth_token}, data=data, verify=False)
        res = response.json()

        self.assertEqual(ErrorCode.SUCCESS.code, res['code'])

        #
        # 3. uid exist - callback_advice
        #

        data = {
            "uid": uid,
            "idx": 1,
            "advice": "테스트 변호사 조언입니다."
        }

        try:
            response = requests.post(url, headers={"Authorization": self.auth_token}, data=data, verify=False)
        except requests.exceptions.ConnectionError as e:
            print(f'ConnectionError: {e}')
            return False

        # 200 OK
        if response.status_code != 200:
            print(response.text)
            self.assertEqual(200, response.status_code)

        res = response.json()

        self.assertEqual(ErrorCode.SUCCESS.code, res['code'])

        pprint(res)

        # remove directory for uid
        rmtree(dest_dir)


if __name__ == "__main__":
    unittest.main()
