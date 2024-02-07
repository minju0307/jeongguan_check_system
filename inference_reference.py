import os
import numpy as np
import pandas as pd

import torch
import transformers
from transformers import AutoTokenizer
import faiss

from encoder import BiEncoder
import os
import json

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_training_state(model, optimizer, scheduler, model_path, optim_path) -> None:
    """모델, optimizer와 기타 정보를 로드합니다"""
    model.load(model_path)
    training_state = torch.load(optim_path)
    optimizer.load_state_dict(training_state["optimizer_state"])
    scheduler.load_state_dict(training_state["scheduler_state"])


def retrieval_query(tokenizer, model, query, index, top_k, device):
    """하나의 질문과 관련 있는 상법 조항을 검색합니다"""
    model.to(device)

    with open("data/reference_sangbub.json", "r", encoding="utf-8-sig") as f:
        reference = json.load(f)

    dict = tokenizer.batch_encode_plus([query], return_tensors="pt")
    q_ids = dict["input_ids"].to(device)
    q_atten = dict["attention_mask"].to(device)
    model.eval()
    with torch.no_grad():
        query_embedding = model(q_ids, q_atten, "query")
    search_index = list(
        index.search(np.float32(query_embedding.detach().cpu()), int(top_k))[1][0]
    )

    # print(search_index)

    references = "\n\n".join([reference[ii] for ii in search_index])
    # print(references)

    return query, references


def main(top_k, query):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    config_dict = {
        "model_path": "dpr_model/my_model.pt",
        "optim_path": "dpr_model/my_model_optim.pt",
        "lr": 1e-5,
        "betas": (0.9, 0.99),
        "num_warmup_steps": 1000,
        "num_training_steps": 2670,
        "output_path": "dpr_model/answeronly.index",
        "test_set": "dataset/question_45.csv",
        "top_k": top_k,
    }

    """모델 로드하기 """
    model = BiEncoder().to(device)
    tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config_dict["lr"], betas=config_dict["betas"]
    )
    scheduler = transformers.get_linear_schedule_with_warmup(
        optimizer, config_dict["num_warmup_steps"], config_dict["num_training_steps"]
    )
    load_training_state(
        model,
        optimizer,
        scheduler,
        config_dict["model_path"],
        config_dict["optim_path"],
    )

    """index 불러오기"""
    index = faiss.read_index(config_dict["output_path"])
    query, references = retrieval_query(
        tokenizer, model, query, index, config_dict["top_k"], device
    )

    return references


class RetrievalSearch:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.config_dict = {
            "model_path": "dpr_model/my_model.pt",
            "optim_path": "dpr_model/my_model_optim.pt",
            "lr": 1e-5,
            "betas": (0.9, 0.99),
            "num_warmup_steps": 1000,
            "num_training_steps": 2670,
            "output_path": "dpr_model/answeronly.index",
            "test_set": "dataset/question_45.csv",
        }

        """모델 로드하기 """
        self.model = BiEncoder().to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=self.config_dict["lr"], betas=self.config_dict["betas"]
        )
        self.scheduler = transformers.get_linear_schedule_with_warmup(
            self.optimizer, self.config_dict["num_warmup_steps"], self.config_dict["num_training_steps"]
        )
        load_training_state(
            self.model,
            self.optimizer,
            self.scheduler,
            self.config_dict["model_path"],
            self.config_dict["optim_path"],
        )

        """index 불러오기"""
        self.index = faiss.read_index(self.config_dict["output_path"])

    def retrieval_query(self, query, top_k=3):
        """하나의 질문과 관련 있는 상법 조항을 검색합니다"""
        self.model.to(self.device)

        with open("data/reference_sangbub.json", "r", encoding="utf-8-sig") as f:
            reference = json.load(f)

        dict = self.tokenizer.batch_encode_plus([query], return_tensors="pt")
        q_ids = dict["input_ids"].to(self.device)
        q_atten = dict["attention_mask"].to(self.device)
        self.model.eval()
        with torch.no_grad():
            query_embedding = self.model(q_ids, q_atten, "query")
        search_index = list(
            self.index.search(np.float32(query_embedding.detach().cpu()), int(top_k))[1][0]
        )

        references = "\n\n".join([reference[ii] for ii in search_index])
        # print(references)

        return references
