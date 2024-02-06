import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def get_embedding(sentences, model, tokenizer):
    encoded_input = tokenizer(
        sentences, padding=True, truncation=True, return_tensors="pt"
    )
    with torch.no_grad():
        model_output = model(**encoded_input)
    last_hidden_states = model_output.hidden_states[-1]
    cls_embeddings = last_hidden_states[:, 0, :]
    return cls_embeddings


def semantic_search(question, input_texts, top_k):
    paragraphs = []
    model_path = "multilabel_model"

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path, output_hidden_states=True
    )

    target_embedding = get_embedding([question], model, tokenizer)
    sentence_embeddings = get_embedding(input_texts, model, tokenizer)

    similarities = cosine_similarity(target_embedding, sentence_embeddings)
    top_k_indices = np.argsort(similarities[0])[-top_k:][::-1]

    # numpy array to list
    top_k_indices = top_k_indices.tolist()

    return top_k_indices


class SemanticSearch:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model_path = "multilabel_model"

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, output_hidden_states=True
        ).to(self.device)

    def get_embedding(self, sentences):
        encoded_input = self.tokenizer(
            sentences, padding=True, truncation=True, return_tensors="pt"
        )
        encoded_input.to(self.device)

        with torch.no_grad():
            model_output = self.model(**encoded_input)
        last_hidden_states = model_output.hidden_states[-1]
        cls_embeddings = last_hidden_states[:, 0, :]
        return cls_embeddings

    def semantic_search(self, question, input_texts, top_k):
        paragraphs = []

        target_embedding = self.get_embedding([question])
        sentence_embeddings = self.get_embedding(input_texts)

        target_embedding = target_embedding.cpu().numpy()
        sentence_embeddings = sentence_embeddings.cpu().numpy()

        similarities = cosine_similarity(target_embedding, sentence_embeddings)
        top_k_indices = np.argsort(similarities[0])[-top_k:][::-1]

        # numpy array to list
        top_k_indices = top_k_indices.tolist()

        return top_k_indices
