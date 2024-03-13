import logging
import os

from config import LANGSMITH_API_KEY, OPENAI_API_KEY


class BaseTest():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s (%(module)s:%(lineno)d) %(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Set Langsmith environment variables
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = f"XAI_Jeongguan - TestLLM"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY  # Update to your API key

    # Set OpenAI environment variables
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
