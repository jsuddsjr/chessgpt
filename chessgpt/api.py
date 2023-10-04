from ninja import NinjaAPI
import openai

api = NinjaAPI(
    title="ChessGPT API",
    description="API for ChessGPT.",
    version="0.1.0"
)

@api.get("/hello")
def hello_world(request):
    completion = openai.Completion.create(model="davinci-002", prompt="Hello!")
    return completion.choices[0].text
