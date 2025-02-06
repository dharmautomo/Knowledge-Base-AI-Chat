import os
import logging
from openai import OpenAI
import time
from utils.text_processor import TextProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
text_processor = TextProcessor()

def process_document(text):
    """Process an uploaded document and store its vectors."""
    return text_processor.process_document(text)

def process_message(message, history):
    start_time = time.time()
    try:
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant that helps users understand and analyze text content."}
        ]

        # Get relevant context from vector store
        context = text_processor.get_relevant_context(message)
        if context:
            messages.append({
                "role": "system",
                "content": f"Here is relevant context from the uploaded documents:\n{context}"
            })

        # Add history context
        for entry in history[-5:]:  # Only use last 5 messages for context
            messages.append({
                "role": entry["role"],
                "content": entry["content"]
            })

        # Add current message
        messages.append({"role": "user", "content": message})

        logger.debug(f"Sending request to OpenAI API with {len(messages)} messages")

        response = client.chat.completions.create(
            model="gpt-4",  # Fixed model name
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        elapsed_time = time.time() - start_time
        logger.debug(f"OpenAI API request completed in {elapsed_time:.2f} seconds")

        return response.choices[0].message.content

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"OpenAI API error after {elapsed_time:.2f} seconds: {str(e)}")
        if elapsed_time >= 30:
            raise Exception("Request timed out. Please try again.")
        raise Exception(f"Error processing message: {str(e)}")