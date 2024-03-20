from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from prompt.template import *
from logger import logger


class LawLLM():
    def __init__(self, model_name):
        self.llm = ChatOpenAI(model=model_name)
        self.logger = logger.getChild(self.__class__.__name__)

    def generate_answer(self, paragraphs, question):
        response_schemas = [
            ResponseSchema(name="answer", description="answer to the user's question"),
            ResponseSchema(
                name="sentence",
                description=" print out the clauses and supporting statements for your answer.",
            ),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(ANSWER_TEMPLATE_v2,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser

        result = chain.invoke({
            "paragraph": "\n".join(paragraphs),
            "question": question
        })

        return result

    def generate_answer_detail(self, paragraphs, question):
        response_schemas = [
            ResponseSchema(name="answer", description="answer to the user's question."),
            ResponseSchema(name="title", description="The title of the paragraph the sentence belongs to."),
            ResponseSchema(
                name="sentence",
                description=" print out the clauses and supporting statements for your answer.",
            ),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(ANSWER_TEMPLATE_v3,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser

        result = chain.invoke({
            "paragraph": "\n".join(paragraphs),
            "question": question
        })

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

        result = chain.invoke({
            "question": question,
            "answer": answer,
            "retrieval_results": sangbub
        })

        return result
