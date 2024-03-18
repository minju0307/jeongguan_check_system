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

    def test_dummy_callback(self):
        url = urljoin(self.url, "callback_test")

        data = {}

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


if __name__ == "__main__":
    unittest.main()
