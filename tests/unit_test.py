import logging
import os
import unittest
from pprint import pprint

import numpy as np

from config import MULTILABEL_MODEL_PATH, APP_ROOT
from inference_paragraph import SemanticSearch
from tests.base import BaseTest
from utils.document_similarity import JeongguanSimilarity
from utils.splitter import filter_text, JeongguanSplitterText, find_title_idx_in_document
from utils.utils import read_file, load_json, save_to_json


class TestUnit(unittest.TestCase, BaseTest):
    def setUp(self):
        pass

    def test_split_jeongguan(self):
        file_dir = '../input_samples'
        normal_files = ['1.txt', '61.txt', '83.txt']
        abnormal_files = ['65e6964faef64e7ba7e76bae.txt']
        # files = ['1.txt']

        for file in abnormal_files:
            file_path = os.path.join(file_dir, file)
            print(f'file: {file}')

            is_error = False
            try:
                self.split_jeongguan(file_path)
            except AssertionError:
                self.logger.info(f'AssertionError: {file}')
                is_error = True
            finally:
                self.assertTrue(is_error)

        for file in normal_files:
            file_path = os.path.join(file_dir, file)
            print(f'file: {file}')

            self.split_jeongguan(file_path)
            self.logger.info(f'file: {file} is done')

    def test_split_jeongguan_and_save(self):
        file_dir = '../input_samples'
        normal_files = ['1.txt', '61.txt', '83.txt']

        file = normal_files[0]

        file_path = os.path.join(file_dir, file)
        file = os.path.basename(file_path)

        splitter = JeongguanSplitterText(file_path, verbose=True)
        documents = splitter.get_document(sub_chapter=True)
        print(documents)

        out_file = f'{file}.json'
        save_to_json(documents, out_file)
        self.logger.info(f'save to {out_file}')

    def split_jeongguan(self, file_path):

        file = os.path.basename(file_path)

        label_dict = load_json('../input_samples/label.json')
        label_info = label_dict[file]

        num_chapters = label_info['num_chapters']
        num_sub_chapters = label_info['num_sub_chapters']

        splitter = JeongguanSplitterText(file_path, verbose=True)

        titles = splitter.get_titles()
        chapters = splitter.get_chapters()
        sub_titles = splitter.get_sub_titles()
        sub_chapters = splitter.get_sub_chapters()
        merged_chapters = splitter.get_merged_chapters()

        self.assertEqual(num_chapters, len(chapters))

        for idx, sub_chapter_list in enumerate(sub_chapters):
            self.assertEqual(num_sub_chapters[idx], len(sub_chapter_list))

        # print merged chapters
        print(f'\nmerge sub_chapters:')
        for idx, sub_chapter_list in enumerate(merged_chapters):
            print(f'chapter {idx + 1}')
            for j, sub_chapter in enumerate(sub_chapter_list):
                filtered_content = filter_text(sub_chapter)
                print(f'  merged {j + 1}(len: {len(sub_chapter)}): {filtered_content}')

        # merged_chapters (single list)
        print(f'\nprint sub_chapters (single list):')
        print(splitter.get_merged_chapters())

        # print document
        print(f'\nprint document:')
        pprint(splitter.get_document()[0])

        document = splitter.get_document(sub_chapter=True)
        for chapter in document:
            print(chapter)

    def test_document_similarity(self):
        reference_doc = load_json(os.path.join(APP_ROOT, 'data/reference_document.json'))

        semantic_search_model = SemanticSearch(model_path=MULTILABEL_MODEL_PATH)

        file_path = os.path.join(APP_ROOT, 'input_samples/1.txt')

        splitter = JeongguanSplitterText(file_path, verbose=False)

        doc_sim = JeongguanSimilarity(semantic_search_model, splitter=splitter, ref_doc=reference_doc, verbose=True)
        sub_scores = doc_sim.get_result()
        print(sub_scores)

        splitter.set_scores(sub_scores)
        document = splitter.get_document(sub_chapter=True)

        for i, sub_score in enumerate(sub_scores):
            self.assertEqual(round(np.mean(sub_score), 3), round(document[i]['score'], 3))

        print(document)

    def test_find_sub_chapter_title(self):
        """
        문장이 포함된 조항의 이름을 찾는 테스트
        :return:
        """
        sentence = "② 회사는 임시주주총회의 소집 기타 필요한 경우 이사회의 결의로 3월을 경과하지 아니하는 일정한 기간을 정하여 권리에 관한 주주명부의 기재변경을 정지하거나 이사회의 결의로 정한 날에 주주명부에 기재되어 있는 주주를 그 권리를 행사할 주주로 할 수 있으며, 이사회가 필요하다고 인정하는 경우에는 주주명부의 기재변경 정지와 기준일의 지정을 함께 할 수 있다."

        file_dir = '../input_samples'
        file_path = os.path.join(file_dir, '1.txt')

        splitter = JeongguanSplitterText(file_path, verbose=False)

        print(f'title: {splitter.find_sub_chapter_title(sentence)}')

    def test_find_title_idx(self):
        #
        # json file에서 title의 index를 찾는 테스트
        #
        uid = 'test_full_result'

        uid_path = os.path.join(APP_ROOT, 'tmp', uid)
        json_file = os.path.join(uid_path, 'outputs.json')
        data = load_json(json_file)

        title = "제8조의4(종류주식의 수와 내용③)"

        result1 = find_title_idx_in_document(title, data['document'])

        #
        # text file에서 title의 index를 찾는 테스트
        #
        file_dir = '../input_samples'
        file_path = os.path.join(file_dir, '1.txt')

        splitter = JeongguanSplitterText(file_path, verbose=False)

        result2 = splitter.find_title_idx(title)

        #
        # 두 결과가 같은지 확인
        #
        self.assertEqual(result1, result2)

        spaced_title = "제8조의4 (종류주식의 수와 내용③)"
        result3 = splitter.find_title_idx(spaced_title)

        self.assertEqual(result2, result3)

    def tearDown(self):
        pass
