import re
import requests
from django.utils.timezone import datetime
from django.http import HttpResponse

def home(request):
    return HttpResponse("Hello, Django!")

def hello_there(request, name):
    now = datetime.now()
    formatted_now = now.strftime("%A, %d %B, %Y at %X")

    # Filter the name argument to letters only using regular expressions. URL arguments
    # can contain arbitrary text, so we restrict to safe characters only.
    match_object = re.match("[a-zA-Z]+", name)

    if match_object:
        clean_name = match_object.group(0).title()
    else:
        clean_name = "Friend"

    content = "Hello there, " + clean_name + "! It's " + formatted_now

    url = request.build_absolute_uri("/api/hello")
    r = requests.get(url)
    if (r.status_code == 200):
        content += f"<br/>From ChatGPT: {r.text}"

    return HttpResponse(content)