import inspect
import os
import re

from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import LANGCHAIN_PROJECT, LANGSMITH_API_KEY
from prompt.template import *
from logger import logger


class LawLLM():
    def __init__(self, model_name):
        self.llm = ChatOpenAI(model=model_name)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        self.logger = logger.getChild(self.__class__.__name__)

        # Set Langsmith environment variables
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY  # Update to your API key

    def generate_answer_detail(self, paragraphs, question):
        response_schemas = [
            ResponseSchema(name="answer", description="The answer to the user's question."),
            ResponseSchema(name="title",
                           description="The title of the paragraph to which the sentence belongs, always in the form '제#조(title)'. If the answer is not supported by the context, output N/A."),
            ResponseSchema(
                name="sentence",
                description="Print the sentence that supports your answer. If the answer is not supported by the context, output N/A."
            ),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(ANSWER_TEMPLATE_v3,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser
        chain = chain.with_config({
            "run_name": inspect.currentframe().f_code.co_name,
            "tags": [self.llm.model_name]
        })

        result = chain.invoke({
            "paragraph": "\n".join(paragraphs),
            "question": question
        })

        self.logger.debug(f'LLM result: {result}')

        # post-process
        if result['title'] == 'N/A' or result['sentence'] == 'N/A':
            result['title'] = ''
            result['sentence'] = ''

        if result['answer'] == 'N/A':
            result['answer'] = '없음'

        return result

    def generate_advice(self, question, answer, sangbub):
        response_schemas = [
            ResponseSchema(name="advice", description="advice to the user's question"),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(ADVICE_TEMPLATE_v2,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser
        chain = chain.with_config({
            "run_name": inspect.currentframe().f_code.co_name,
            "tags": [self.llm.model_name]
        })

        result = chain.invoke({
            "question": question,
            "answer": answer,
            "retrieval_results": sangbub
        })

        return result

    def generate_advice_detail(self, question, answer, sangbub):
        response_schemas = [
            ResponseSchema(name="advice", type="string", description="advice to the user's question"),
            ResponseSchema(name="is_satisfied", type="integer",
                           description="whether the answer satisfies the context or requires verification. (0: Unsatisfied, 1: Verification required, 2: Satisfied)"),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

        format_instructions = output_parser.get_format_instructions()
        self.logger.debug(format_instructions)

        prompt = ChatPromptTemplate.from_template(ADVICE_TEMPLATE_v3,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser
        chain = chain.with_config({
            "run_name": inspect.currentframe().f_code.co_name,
            "tags": [self.llm.model_name]
        })

        result = chain.invoke({
            "question": question,
            "answer": answer,
            "retrieval_results": sangbub
        })

        return result

    def generate_rewrite_query(self, question):
        response_schemas = [
            ResponseSchema(name="result", type="string", description="generated example query"),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

        format_instructions = output_parser.get_format_instructions()
        self.logger.debug(format_instructions)

        prompt = ChatPromptTemplate.from_template(RETRIEVAL_REWRITE_TEMPLATE,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser
        chain = chain.with_config({
            "run_name": inspect.currentframe().f_code.co_name,
            "tags": [self.llm.model_name]
        })

        result = chain.invoke({
            "question": question,
        })

        generated_text = result['result']
        cleaned_res = re.sub(r"제\s*\d+조", '', generated_text)

        result['result'] = cleaned_res

        return result

    def get_embedding(self, text):
        return self.embeddings.embed_query(text)

    def get_embedding_from_documents(self, documents):
        """Get embeddings from a list of documents.
        Args:
            documents (List[str]): List of documents.
        Returns:
            List of embeddings. (size: [num_paragraphs, 3072])
        """
        return self.embeddings.embed_documents(documents)
