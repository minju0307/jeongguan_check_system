import os
import unittest

from main import split_document_shorter
from utils.splitter import filter_text, JeongguanSplitter
from utils.utils import read_file, load_json


class TestUnit(unittest.TestCase):
    def setUp(self):
        pass

    def test_split_paragraph(self):
        print('test_1')
        input_lines = read_file('../input_samples/1.txt')
        input_text = '\n'.join(input_lines)

        input_texts = split_document_shorter(input_text)

        for idx, line_text in enumerate(input_texts):
            filtered_content = filter_text(line_text)
            print(f'split {idx + 1}(len: {len(line_text)}): {filtered_content}')
        print()

    def test_split_jeongguan(self):
        # file_path = '../input_samples/1.txt'
        # file_path = '../input_samples/61.txt'
        # file_path = '../input_samples/83.txt'
        # file_path = '../input_samples/138.txt'
        file_path = '../input_samples/148.txt'
        file = os.path.basename(file_path)
        input_lines = read_file(file_path)

        label_dict = load_json('../input_samples/label.json')
        label_info = label_dict[file]

        num_chapters = label_info['num_chapters']
        num_sub_chapters = label_info['num_sub_chapters']

        content = '\n'.join(input_lines).strip()

        splitter = JeongguanSplitter(content, verbose=True)

        chapters = splitter.get_chapters()
        sub_chapters = splitter.get_sub_chapters()
        merged_chapters = splitter.get_merged_chapters()

        self.assertEquals(num_chapters, len(chapters))

        for idx, sub_chapter_list in enumerate(sub_chapters):
            self.assertEquals(num_sub_chapters[idx], len(sub_chapter_list))

        # print merged chapters
        print(f'\nmerge sub_chapters')
        for idx, sub_chapter_list in enumerate(merged_chapters):
            print(f'chapter {idx + 1}')
            for j, sub_chapter in enumerate(sub_chapter_list):
                filtered_content = filter_text(sub_chapter)
                print(f'  merged {j + 1}(len: {len(sub_chapter)}): {filtered_content}')

        # merged_chapters (single list)
        print(splitter.get_merged_chapters(single_list=True))

    def tearDown(self):
        pass
