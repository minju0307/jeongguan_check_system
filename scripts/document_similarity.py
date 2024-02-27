import os
import re
from sklearn.metrics.pairwise import cosine_similarity

from config import MULTILABEL_MODEL_PATH, APP_ROOT
from inference_paragraph import SemanticSearch
from utils.splitter import JeongguanSplitterText
from utils.utils import load_json

reference_doc = load_json(os.path.join(APP_ROOT, 'data/reference_document.json'))


class DocumentSimilarity:
    def __init__(self, semantic_search_model: SemanticSearch, reference_doc: list, file_path: str):
        self.splitter = JeongguanSplitterText(file_path, verbose=False)
        self.semantic_search_model = semantic_search_model

        sub_titles = self.splitter.get_sub_titles()
        sub_chapters = self.splitter.get_sub_chapters()

        # sub_chapters to single list
        sub_titles = [title for title_list in sub_titles for title in title_list]
        sub_chapters = [sub_chapter for sub_chapter_list in sub_chapters for sub_chapter in sub_chapter_list]

        # sub_titles: remove parentheses
        new_sub_titles = []
        for sub_title in sub_titles:
            pattern = r'\((.+)\)'
            sub_title = re.findall(pattern, sub_title)
            sub_title = sub_title[0] if sub_title else ''
            new_sub_titles.append(sub_title)

        #
        # 제목 처리
        #
        input_embeddings = semantic_search_model.get_embedding(new_sub_titles)
        input_embeddings = input_embeddings.cpu().numpy()

        # get reference titles in reference_doc
        reference_titles = []
        for ref_chapter in reference_doc:
            for ref_sub_chapter in ref_chapter:
                reference_titles.append(ref_sub_chapter['title'])

        ref_embeddings = semantic_search_model.get_embedding(reference_titles)
        ref_embeddings = ref_embeddings.cpu().numpy()

        title_similarities = cosine_similarity(input_embeddings, ref_embeddings)

        #
        # 내용 처리
        #
        input_embeddings = semantic_search_model.get_embedding(sub_chapters)
        input_embeddings = input_embeddings.cpu().numpy()

        reference_contents = []
        for ref_chapter in reference_doc:
            for ref_sub_chapter in ref_chapter:
                reference_contents.append(ref_sub_chapter['content'])

        ref_embeddings = semantic_search_model.get_embedding(reference_contents)
        ref_embeddings = ref_embeddings.cpu().numpy()

        content_similarities = cosine_similarity(input_embeddings, ref_embeddings)

        warning_list = []
        document_list = []

        for sub_title, title_similarity, content_similarity in zip(sub_titles, title_similarities,
                                                                   content_similarities):
            # get top 1
            top_title_idx = title_similarity.argmax()
            title_score = title_similarity[top_title_idx]
            content_score = content_similarity[top_title_idx]

            print(f'\nsub_title: {sub_title}')
            print(f'similarity: {title_similarity[top_title_idx]}')
            print(f'reference: {reference_titles[top_title_idx]}')

            top_content_idx = content_similarity.argmax()
            top_content_score = content_similarity[top_content_idx]

            print(f'similarity top content_idx({top_content_idx}): {top_content_score}')
            print(f'similarity top title_idx({top_title_idx}): {content_score}')

            final_score = 0
            final_idx = -1
            if title_score >= 0.85:
                final_score = title_score
                final_idx = top_title_idx
            else:
                if top_content_score >= 0.85:
                    final_score = top_content_score
                    final_idx = top_content_idx
                else:
                    if top_title_idx == top_content_idx:
                        final_score = max(title_score, content_score)

                        if final_score == title_score:
                            final_idx = top_title_idx
                        else:
                            final_idx = top_content_idx

                    else:
                        final_score = max(title_score, content_score, top_content_score)

                        if final_score == title_score:
                            final_idx = top_title_idx
                        elif final_score == content_score:
                            final_idx = top_content_idx
                        else:
                            final_idx = top_content_idx

                        warning_list.append(
                            (sub_title, reference_titles[top_title_idx], title_score, content_score, top_content_score))

            final_score = min(1.0, final_score)
            print(f'final_score: {final_score}')
            print(f'final_idx: {final_idx}')
            print(f'reference: {reference_titles[final_idx]}')

            sub_chapter_dict = {
                'title': sub_title,
                'content': sub_chapters[sub_titles.index(sub_title)],
                'score': final_score
            }
            document_list.append(sub_chapter_dict)

        print(f'\nwarning_list: (count: {len(warning_list)})')
        for warning in warning_list:
            print(warning)

        self.document_list = document_list

    def get_result(self):
        return self.document_list


def main():
    semantic_search_model = SemanticSearch(model_path=MULTILABEL_MODEL_PATH)

    file_path = os.path.join(APP_ROOT, 'input_samples/1.txt')

    splitter = DocumentSimilarity(semantic_search_model, reference_doc, file_path)

    print(splitter.get_result())


if __name__ == "__main__":
    main()
