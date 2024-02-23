import os
import unittest
from pprint import pprint

from main import split_document_shorter
from utils.splitter import filter_text, JeongguanSplitterText
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
        file_dir = '../input_samples'
        files = ['1.txt', '61.txt', '83.txt', '138.txt', '148.txt']

        for file in files:
            file_path = os.path.join(file_dir, file)
            print(f'file: {file}')
            self.split_jeongguan(file_path)

    def split_jeongguan(self, file_path):

        file = os.path.basename(file_path)

        label_dict = load_json('../input_samples/label.json')
        label_info = label_dict[file]

        num_chapters = label_info['num_chapters']
        num_sub_chapters = label_info['num_sub_chapters']

        splitter = JeongguanSplitterText(file_path, verbose=True)

        titles = splitter.get_titles()
        chapters = splitter.get_chapters()
        sub_chapters = splitter.get_sub_chapters()
        merged_chapters = splitter.get_merged_chapters()

        self.assertEquals(num_chapters, len(chapters))

        for idx, sub_chapter_list in enumerate(sub_chapters):
            self.assertEquals(num_sub_chapters[idx], len(sub_chapter_list))

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

    def tearDown(self):
        pass
