MODEL = "gpt-4-vision-preview"  #"gpt-3.5-turbo"
PARAM_OPTIONS = ["max_tokens", "n", "presense_penalty", "frequency_penalty", "logit_bias", "temperature", "top_p"]
CHAT_PARAMS = {'max_tokens' : 250 } # {'max_tokens' : 200 }

OPENAI_AUTH_HEADER = {'Authorization' : 'Bearer ...' , 'OpenAI-Organization' : '...'}
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


CHAT_OBJ = { "role": None, # 'system', 'user' or 'assistant'
        "content" : None
}

TEXT_EXTENSION_ELEMENT = {
    "type": "text",
    "text": None
}

IMAGE_EXTENSION_ELEMENT = {
    "type": "image_url",
    "image_url": { 
        "url" : None,
        "detail": "low"
     }
}

CHAT_TEMPLATE = { "model": MODEL,
        "messages": []
}
# add controlling parameters
for key in list(CHAT_PARAMS.keys()):
    if key in PARAM_OPTIONS:
        CHAT_TEMPLATE[key] = CHAT_PARAMS[key]

