import openai

class OpenAIService:
    def __init__(self, api_key):
        openai.api_key = api_key

    def generate_response(self, prompt):
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            n=1,
            temperature=0.7
        )
        return response.choices[0].text.strip()
