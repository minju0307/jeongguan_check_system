import unittest
from pprint import pprint

from main import split_document_shorter
from utils.utils import read_file


def filter_text(text):
    text = ' '.join(text.split())
    return text[:100]


def split_content(content, chapter_pattern, verbose=False):
    import re

    # find chapter index from content
    chapter_idx = [m.start() for m in re.finditer(chapter_pattern, content)]

    if verbose:
        print(f'\nsplit_content: {chapter_pattern}')

    # print chapeter content
    split_content = []
    prev_idx = 0
    for idx, chapter in enumerate(chapter_idx):
        chapter_content = content[prev_idx:chapter]
        split_content.append(chapter_content)
        filtered_content = filter_text(chapter_content)

        if verbose:
            print(f'split {idx + 1}(len:{len(chapter_content)}): {filtered_content}')

        prev_idx = chapter

    return split_content


class JeongguanSplitter:
    def __init__(self, content, verbose=False):
        self.content = content
        self.verbose = verbose

        chapter_pattern = r'((\n)제\d+장.+)'
        sub_chapter_pattern = r'((\n)제\d+조.+)'

        self.chapters = self.split_chapters(chapter_pattern)
        self.sub_chapters = self.split_sub_chapters(sub_chapter_pattern)

        self.merged_chapters = self.merge_sub_chapters(self.sub_chapters)

    def split_chapters(self, chapter_pattern):
        chapters = split_content(self.content, chapter_pattern, verbose=self.verbose)
        return chapters[1:]  # 첫번째 항목에는 일반적인 내용만 있어서 제외

    def split_sub_chapters(self, sub_chapter_pattern):
        sub_chapters = []
        for chapter in self.chapters:
            splitted_content = split_content(chapter, sub_chapter_pattern, verbose=self.verbose)
            sub_chapters.append(splitted_content)

        return sub_chapters

    def merge_sub_chapters(self, sub_chapters):
        # merge sub_chapters to around 1200 length

        merged_chapters = []

        for sub_chapter_list in sub_chapters:
            merged_sub_chapters = []
            merged_text = ''

            for sub_chapter in sub_chapter_list:
                if len(merged_text) + len(sub_chapter) > 1200:
                    merged_sub_chapters.append(merged_text)
                    merged_text = sub_chapter
                else:
                    merged_text += sub_chapter

            if merged_text:
                merged_sub_chapters.append(merged_text)

            merged_chapters.append(merged_sub_chapters)

        return merged_chapters

    def get_chapters(self):
        return self.chapters

    def get_sub_chapters(self):
        return self.sub_chapters

    def get_merged_chapters(self):
        return self.merged_chapters


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
        input_lines = read_file('../input_samples/1.txt')
        len_chapter = 7

        content = '\n'.join(input_lines).strip()

        splitter = JeongguanSplitter(content, verbose=True)

        chapters = splitter.get_chapters()
        sub_chapters = splitter.get_sub_chapters()
        merged_chapters = splitter.get_merged_chapters()

        self.assertEquals(len_chapter, len(chapters))

        # print merged chapters
        print(f'\nmerge sub_chapters')
        for idx, sub_chapter_list in enumerate(merged_chapters):
            print(f'chapter {idx + 1}')
            for sub_chapter in sub_chapter_list:
                filtered_content = filter_text(sub_chapter)
                print(f'merged {idx + 1}(len: {len(sub_chapter)}): {filtered_content}')

    def tearDown(self):
        pass
