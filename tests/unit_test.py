import os.path
import re
import unittest
from pprint import pprint

from main import split_document_shorter
from utils.utils import read_file, load_json


def filter_text(text):
    text = ' '.join(text.split())
    return text[:100]


def split_content(content, chapter_pattern, verbose=False):
    # find chapter index from content
    chapter_idxs = [(m.start(), m.end()) for m in re.finditer(chapter_pattern, content)]

    if verbose:
        print(f'\nsplit_content: {chapter_pattern}')

    # print chapeter content
    title_list = []
    content_list = []

    # 패턴에 해당하는 텍스트
    for idx, (start, end) in enumerate(chapter_idxs):
        chapter_title = content[start:end].strip()
        title_list.append(chapter_title)
        print(f'chapter {idx + 1}: {chapter_title}')

    prev_idx = 0

    # 패턴 인덱스를 이용한 텍스트 분리
    idx = 0
    for i, (start, end) in enumerate(chapter_idxs):
        if prev_idx == 0:
            prev_idx = start
            continue

        chapter_content = content[prev_idx:start]
        content_list.append(chapter_content)
        filtered_content = filter_text(chapter_content)

        if verbose:
            print(f'split {idx + 1}(len:{len(chapter_content)}): {filtered_content}')

        prev_idx = start
        idx += 1

    # add last content
    last_content = content[prev_idx:]
    content_list.append(last_content)
    filtered_content = filter_text(last_content)

    if verbose:
        print(f'split {idx + 1}(len:{len(last_content)}): {filtered_content}')

    assert len(title_list) == len(content_list)

    # validate title numbering: 번호가 같거나 크지 않을 경우 제거
    prev_num = 0
    new_title_list = title_list.copy()
    new_content_list = content_list.copy()

    idx = 0
    for i, title in enumerate(title_list):
        cur_num = int(re.findall(r'\d+', title)[0])

        if prev_num == 0:
            prev_num = cur_num

        if cur_num  == prev_num + 1 or cur_num == prev_num:
            prev_num = cur_num
            idx += 1
        else:
            # remove element
            new_title_list.pop(idx)
            new_content_list.pop(idx)

    assert len(new_title_list) == len(new_content_list)

    # print chapter title
    for idx, title in enumerate(new_title_list):
        print(f'filtered {idx + 1}: {title}')

    return new_title_list, new_content_list


class JeongguanSplitter:
    def __init__(self, content, merge_len=1200, verbose=False):
        self.merge_len = merge_len
        self.verbose = verbose

        chapter_pattern = r'((\n)제[ ]{0,}\d+[ ]{0,}장.+)'
        sub_chapter_pattern = r'(\n)제[ ]{0,}\d{,2}[ ]{0,}조([의]?[ ]{0,}\d{,2})'

        space_pattern = r'[ ]{2,}'
        self.content = re.sub(space_pattern, ' ', content)

        self.chapters = self.split_chapters(chapter_pattern)
        self.sub_chapters = self.split_sub_chapters(sub_chapter_pattern)

        self.merged_chapters = self.merge_sub_chapters(self.sub_chapters)

    def split_chapters(self, chapter_pattern):
        titles, chapters = split_content(self.content, chapter_pattern, verbose=self.verbose)

        # 보칙 제거
        pattern_list = ['보칙', '부칙']
        for idx, title in enumerate(titles):
            new_title = ''.join(title.split())
            if any([pattern in new_title for pattern in pattern_list]):
                titles.pop(idx)
                chapters.pop(idx)

        return chapters

    def split_sub_chapters(self, sub_chapter_pattern):
        sub_chapters = []
        for chapter in self.chapters:
            _, splitted_list = split_content(chapter, sub_chapter_pattern, verbose=self.verbose)
            sub_chapters.append(splitted_list)

        return sub_chapters

    def merge_sub_chapters(self, sub_chapters):
        # merge sub_chapters to around merge_len
        merged_chapters = []

        for sub_chapter_list in sub_chapters:
            merged_sub_chapters = []
            merged_text = ''

            for sub_chapter in sub_chapter_list:
                if len(merged_text) + len(sub_chapter) > self.merge_len:
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
        # file_path = '../input_samples/1.txt'
        # file_path = '../input_samples/61.txt'
        # file_path = '../input_samples/83.txt'
        file_path = '../input_samples/138.txt'
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

    def tearDown(self):
        pass
