import logging
import time
from typing import List, Union

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class SemanticSearch:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, output_hidden_states=True
        ).to(self.device)

    def get_embedding(self, sentences: List[str]):
        encoded_input = self.tokenizer(
            sentences, padding=True, truncation=True, return_tensors="pt"
        )
        encoded_input.to(self.device)

        with torch.no_grad():
            model_output = self.model(**encoded_input)
        last_hidden_states = model_output.hidden_states[-1]
        cls_embeddings = last_hidden_states[:, 0, :]
        return cls_embeddings

    def semantic_search(self, question: str, input_texts: Union[List[str], np.ndarray], top_k: int):
        target_embedding = self.get_embedding([question])
        target_embedding = target_embedding.cpu().numpy()

        if isinstance(input_texts, list):
            input_texts = np.array(input_texts)
            sentence_embeddings = self.get_embedding(input_texts)
            sentence_embeddings = sentence_embeddings.cpu().numpy()
        else:
            sentence_embeddings = input_texts

        similarities = cosine_similarity(target_embedding, sentence_embeddings)
        top_k_indices = np.argsort(similarities[0])[-top_k:][::-1]

        # numpy array to list
        top_k_indices = top_k_indices.tolist()

        return top_k_indices
