from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from prompt.template import ANSWER_TEMPLATE_v2, ADVICE_TEMPLATE_v2


class LawLLM():
    def __init__(self, model_name):
        self.llm = ChatOpenAI(model=model_name)

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

    def generate_advice(self, q, answer, sangbub):
        response_schemas = [
            ResponseSchema(name="advice", description="advice to the user's question"),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(ADVICE_TEMPLATE_v2,
                                                  partial_variables={"format_instructions": format_instructions})

        chain = prompt | self.llm | output_parser

        result = chain.invoke({
            "question": q,
            "answer": answer,
            "retrieval_results": sangbub
        })

        return result
