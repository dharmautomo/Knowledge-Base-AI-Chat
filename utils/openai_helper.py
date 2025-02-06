import os
import logging
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=OPENAI_API_KEY)

def process_message(message, history):
    try:
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant that helps users understand and analyze text content."}
        ]

        # Add history context
        for entry in history[-5:]:  # Only use last 5 messages for context
            messages.append({
                "role": entry["role"],
                "content": entry["content"]
            })

        # Add current message
        messages.append({"role": "user", "content": message})

        logging.debug(f"Sending request to OpenAI API with {len(messages)} messages")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        raise Exception(f"Error processing message: {str(e)}")