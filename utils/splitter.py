import re
from abc import abstractmethod, ABC

import numpy as np

from utils.utils import read_file


def filter_text(text):
    text = ' '.join(text.split())
    return text[:100]


def update_prev_idx(start, end, include_title):
    if include_title:
        return start
    else:
        return end


def split_content(content, chapter_pattern, include_title=True, verbose=False):
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

        if verbose:
            print(f'chapter {idx + 1}: {chapter_title}')

    prev_idx = 0

    # 패턴 인덱스를 이용한 텍스트 분리
    idx = 0
    for i, (start, end) in enumerate(chapter_idxs):
        if i == 0:
            prev_idx = update_prev_idx(start, end, include_title)
            continue

        chapter_content = content[prev_idx:start].strip()
        content_list.append(chapter_content)
        filtered_content = filter_text(chapter_content)

        if verbose:
            print(f'split {idx + 1}(len:{len(chapter_content)}): {filtered_content}')

        prev_idx = update_prev_idx(start, end, include_title)
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

        if cur_num == prev_num + 1 or cur_num == prev_num:
            prev_num = cur_num
            idx += 1
        else:
            # merge element to previous element
            print(f'## merge {i} and {i + 1} (idx: {idx})')

            new_content_list[idx - 1] += new_content_list[idx]

            new_title_list.pop(idx)
            new_content_list.pop(idx)

    assert len(new_title_list) == len(new_content_list)

    # print chapter title
    if verbose:
        for idx, title in enumerate(new_title_list):
            print(f'filtered {idx + 1}: {title}')

    return new_title_list, new_content_list


class JeongguanSplitter(ABC):
    titles = []
    chapters = []
    sub_titles = []
    sub_chapters = []

    def __init__(self, content, merge_len=1200, verbose=False):
        self.sub_scores = None
        self.merge_len = merge_len
        self.verbose = verbose

        chapter_pattern = r'((\n)제[ ]{0,}\d+[ ]{0,}장.+)'
        sub_chapter_pattern = r'((\n|^)제[ ]{0,}\d{,2}[ ]{0,}조[의]?[ ]{0,}\d{,2}[ ]{0,})\(([^\)]+)\)'

        space_pattern = r'[ ]{2,}'
        self.content = re.sub(space_pattern, ' ', content)

        self.split_chapters(chapter_pattern)
        self.sub_titles, self.sub_chapters = self.split_sub_chapters(sub_chapter_pattern)

        self.merged_chapters = self.merge_sub_chapters(self.sub_chapters)

    @abstractmethod
    def read_file(self, file_path):
        pass

    def split_chapters(self, chapter_pattern):
        titles, chapters = split_content(self.content, chapter_pattern, include_title=False, verbose=self.verbose)

        # 보칙 제거
        pattern_list = ['보칙', '부칙']
        for idx, title in enumerate(titles):
            new_title = ''.join(title.split())
            if any([pattern in new_title for pattern in pattern_list]):
                titles.pop(idx)
                chapters.pop(idx)

        assert len(titles) == len(chapters)

        self.titles = titles
        self.chapters = chapters

    def split_sub_chapters(self, sub_chapter_pattern):
        sub_titles = []
        sub_chapters = []
        for chapter in self.chapters:
            title_list, splitted_list = split_content(chapter, sub_chapter_pattern, verbose=self.verbose)
            sub_titles.append(title_list)
            sub_chapters.append(splitted_list)

            assert len(title_list) == len(splitted_list)

        return sub_titles, sub_chapters

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
                    if len(merged_text) > 0:
                        merged_text += '\n\n'

                    merged_text += sub_chapter

            if merged_text:
                merged_sub_chapters.append(merged_text)

            merged_chapters.append(merged_sub_chapters)

        return merged_chapters

    def get_titles(self):
        return self.titles

    def get_chapters(self):
        return self.chapters

    def get_sub_titles(self):
        return self.sub_titles

    def get_sub_chapters(self):
        return self.sub_chapters

    def get_merged_chapters(self):
        return self.merged_chapters

    def get_document(self, sub_chapter=False):
        document = []
        if sub_chapter:
            for i, (title, sub_title, chapter) in enumerate(zip(self.titles, self.sub_titles, self.sub_chapters)):
                sub_document = []
                for j, (sub_title, sub_chapter) in enumerate(zip(sub_title, chapter)):
                    sub_chapter_info = {'title': sub_title, 'content': sub_chapter}
                    if self.sub_scores:
                        sub_chapter_info['score'] = self.sub_scores[i][j]
                    sub_document.append(sub_chapter_info)

                score = np.mean(self.sub_scores[i]) if self.sub_scores else 0
                score = round(score, 3)

                chapter_info = {'title': title, 'content': sub_document, 'score': score}
                document.append(chapter_info)
        else:
            for title, chapter in zip(self.titles, self.chapters):
                chapter_info = {'title': title, 'content': chapter}
                document.append(chapter_info)

        return document

    def find_sub_chapter_title(self, sentence):
        for i, sub_chapter_list in enumerate(self.sub_chapters):
            for j, sub_chapter in enumerate(sub_chapter_list):
                if sentence in sub_chapter:
                    return self.sub_titles[i][j]

        return False

    def set_scores(self, sub_scores):
        self.sub_scores = sub_scores


class JeongguanSplitterText(JeongguanSplitter):
    def __init__(self, file_path, merge_len=1200, verbose=False):
        content = self.read_file(file_path)
        super().__init__(content, merge_len, verbose)

    def read_file(self, file_path):
        input_lines = read_file(file_path)
        return '\n'.join(input_lines).strip()
