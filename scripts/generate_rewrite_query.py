import os
import pickle

import pandas as pd

from config import QUESTION_DB_FILE, OPENAI_API_KEY, APP_ROOT
from utils.langchain_llm import LawLLM


def generate_query():
    # read question file
    questions_df = pd.read_csv(QUESTION_DB_FILE)
    questions_list = questions_df['question'].tolist()

    print(questions_list)

    gpt_model = 'gpt-4-0125-preview'

    law_llm = LawLLM(model_name=gpt_model)

    # generate rewrite query
    outputs = []
    for i, question in enumerate(questions_list):
        output = law_llm.generate_rewrite_query(question)
        outputs.append((i + 1, output['result']))
        break

    out_file = os.path.join(APP_ROOT, 'data/rewrite_query.csv')
    # save to csv
    outputs_df = pd.DataFrame(outputs, columns=['idx', 'rewrite_query'])
    outputs_df.to_csv(out_file, index=False)


def generate_embedding():
    csv_file = os.path.join(APP_ROOT, 'data/rewrite_query.csv')
    rewrite_query_df = pd.read_csv(csv_file)

    gpt_model = 'gpt-4-0125-preview'

    law_llm = LawLLM(model_name=gpt_model)

    # get rewrite query
    rewrite_query_list = rewrite_query_df['rewrite_query'].tolist()

    # generate embedding
    paragraph_vectors = law_llm.get_embedding_from_documents(rewrite_query_list)

    # save to pickle
    out_file = os.path.join(APP_ROOT, 'data/rewrite_query_vectors.pkl')
    pickle.dump(paragraph_vectors, open(out_file, 'wb'))


# main
if __name__ == '__main__':
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    # generate_query()
    generate_embedding()
