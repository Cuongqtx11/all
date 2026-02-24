from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

async def check_potential(text):
    prompt = f"""
    Message: {text}
    Is this person looking to buy something?
    Answer only YES or NO.
    """

    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}]
    )

    return "YES" in response.choices[0].message.content.upper()
