import unittest
from pprint import pprint

from main import split_document_shorter
from utils.utils import read_file


class TestUnit(unittest.TestCase):
    def setUp(self):
        pass

    def test_split_paragraph(self):
        print('test_1')
        input_lines = read_file('../input_samples/1.txt')
        input_text = '\n'.join(input_lines)

        input_texts = split_document_shorter(input_text)

        for line_text in input_texts:
            print(f'len: {len(line_text)} / {line_text}')
        print()

    def test_split_jengguan(self):
        def filter_chapter(chapter):
            chapter = chapter.replace('\n', ' ')
            chapter = chapter.replace('  ', ' ')
            return chapter[:100]

        input_lines = read_file('../input_samples/1.txt')
        content = '\n'.join(input_lines).strip()

        import re

        chapter_pattern =  r'(제\d+장.+)'

        chapters = re.split(chapter_pattern, content)

        # find chapter index
        # chapter_idx = [idx for idx, chapter in enumerate(chapters) if re.match(chapter_pattern, chapter)]
        # print(chapter_idx)

        # find chapter index from content
        chapter_idx = [m.start() for m in re.finditer(chapter_pattern, content)]
        print(chapter_idx)

        # print chapeter content
        prev_idx = 0
        for idx, chapter in enumerate(chapter_idx):
            chapter_content = content[prev_idx:chapter]
            filtered_content = filter_chapter(chapter_content)
            print(f'chapter {idx+1}(len:{len(chapter_content)}): {filtered_content}')
            prev_idx = chapter

    def tearDown(self):
        pass