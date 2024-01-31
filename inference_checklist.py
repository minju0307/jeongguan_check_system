import json
import argparse
import numpy as np

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def inference(input_text, model_path):
    with open("data/jeongguan_questions_56.json", "r", encoding="utf-8-sig") as f:
        questions = json.load(f)

    label2id = {k: v for v, k in enumerate(list(questions.keys()))}
    id2label = {k: v for k, v in enumerate(list(questions.keys()))}

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path,
        num_labels=len(id2label),
        id2label=id2label,
        label2id=label2id,
        problem_type="multi_label_classification",
    )

    device = "cuda"
    model.to(device)
    encoding = tokenizer(
        input_text, return_tensors="pt", truncation=True, max_length=512
    )
    encoding = {k: v.to(model.device) for k, v in encoding.items()}

    outputs = model(**encoding)
    logits = outputs.logits

    # apply sigmoid + threshold
    sigmoid = torch.nn.Sigmoid()
    probs = sigmoid(logits.squeeze().cpu())
    predictions = np.zeros(probs.shape)
    predictions[np.where(probs >= 0.5)] = 1
    # turn predicted id's into actual label names
    predicted_labels = [idx for idx, label in enumerate(predictions) if label == 1.0]
    predicted_questions = [
        id2label[idx] for idx, label in enumerate(predictions) if label == 1.0
    ]

    return predicted_questions
