import requests, copy, logging
from settings import db, HOSTNAME

LINE_AUTH_HEADER = {"Authorization": "Bearer ..."}

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

PUSH_TEMPLATE = {
        "to" : None,
        "messages" : []
}

REPLY_TEMPLATE = {
        "replyToken" : None,
        "messages" : []
}

CHAT_QUICK_RESPONSE_MESSAGE = {
        "type" : "text",
        "text" : None,
        "quickReply" : {
            "items" : [
                {
                    "type" : "action",
                    "action" : {
                        "type": "postback",
                        "label": "返回選單",
                        "data": "menu"
                    }
                },
                {
                    "type" : "action",
                    "action" : {
                        "type": "postback",
                        "label": "開啟新話題",
                        "data": "new"
                    }
                }
            ]
        }
}


SWITCH_MODE_MESSAGE = {
  "type": "template",
  "altText": "選擇使用模式",
  "template": {
    "type": "confirm",
    "text": "請問要使用哪種模式？",
    "actions": [
      {
        "type": "postback",
        "label": "聊天模式",
        "data": "mode=chat"
      },
      {
        "type": "postback",
        "label": "生成模式",
        "data": "mode=imagine",
      }
    ]
  }
}


IMAGE_CAROUSEL_MESSAGE = {
        "type": "template",
        "altText": "選擇生成圖片效果",
        "template": {
            "type": "carousel",
            "columns": [
                {
                    "thumbnailImageUrl": None,
                    "imageBackgroundColor": "#FFFFFF",
                    "title": "Image #1",
                    "text": "選擇此圖為基底",
                    "defaultAction": {
                        "type": "uri",
                        "label": "View detail",
                        "uri": None
                    },
                    "actions": [
                        {   "type": "postback",
                            "label": "大幅變化",
                            "data": "index=1&operation=vary_strong&custom_id="
                        },
                        {   "type": "postback",
                            "label": "小幅變化",
                            "data": "index=1&operation=vary_subtle&custom_id="
                        }
                    ]
                },
                {
                    "thumbnailImageUrl": None,
                    "imageBackgroundColor": "#000000",
                    "title": "Image #2",
                    "text": "選擇此圖為基底",
                    "defaultAction": {
                        "type": "uri",
                        "label": "View detail",
                        "uri": None
                    },
                    "actions": [
                        {   "type": "postback",
                            "label": "大幅變化",
                            "data": "index=2&operation=vary_strong&custom_id="
                        },
                        {   "type": "postback",
                            "label": "小幅變化",
                            "data": "index=2&operation=vary_subtle&custom_id="
                        }
                    ]
                },
                {
                    "thumbnailImageUrl": None,
                    "imageBackgroundColor": "#000000",
                    "title": "Image #3",
                    "text": "選擇此圖為基底",
                    "defaultAction": {
                        "type": "uri",
                        "label": "View detail",
                        "uri": None
                    },
                    "actions": [
                        {   "type": "postback",
                            "label": "大幅變化",
                            "data": "index=3&operation=vary_strong&custom_id="
                        },
                        {   "type": "postback",
                            "label": "小幅變化",
                            "data": "index=3&operation=vary_subtle&custom_id="
                        }
                    ]
                },
                {
                    "thumbnailImageUrl": None,
                    "imageBackgroundColor": "#000000",
                    "title": "Image #4",
                    "text": "選擇此圖為基底",
                    "defaultAction": {
                        "type": "uri",
                        "label": "View detail",
                        "uri": None
                    },
                    "actions": [
                        {   "type": "postback",
                            "label": "大幅變化",
                            "data": "index=4&operation=vary_strong&custom_id="
                        },
                        {   "type": "postback",
                            "label": "小幅變化",
                            "data": "index=4&operation=vary_subtle&custom_id="
                        }
                    ]
                }
            ],
            "imageAspectRatio": "rectangle",
            "imageSize": "cover"
        },
        "quickReply" : {
            "items" : [
                {
                    "type" : "action",
                    "action" : {
                        "type": "postback",
                        "label": "返回選單",
                        "data": "menu"
                    }
                }
            ]
        }
} 


IMAGE_BUTTON_MESSAGE = {
        "type": "template",
        "altText": "選擇生成圖片效果",
        "template": {
            "type": "buttons",
            "thumbnailImageUrl": None,
            "imageAspectRatio": "rectangle",
            "imageSize": "cover",
            "imageBackgroundColor": "#FFFFFF",
            #"title": "Menu",
            "text": "請選擇圖片",
            "defaultAction": {
                "type": "uri",
                "label": "View detail",
                "uri": None
            },
            "actions": [
                {   "type": "postback",
                    "label": "U1",
                    "data": "custom_id="
                },
                {   "type": "postback",
                    "label": "U2",
                    "data": "custom_id="
                },
                {
                    "type": "postback",
                    "label": "U3",
                    "data": "custom_id="
                },
                {
                    "type": "postback",
                    "label": "U4",
                    "data": "custom_id="
                }
            ]
        },
        "quickReply" : {
            "items" : [
                {
                    "type" : "action",
                    "action" : {
                        "type": "postback",
                        "label": "返回選單",
                        "data": "menu"
                    }
                }
            ]
        }
}


TEXT_MESSAGE = {
        "type": "text",
        "text": None
}

IMAGE_MESSAGE = {
        "type": "image",
        "originalContentUrl": None,
        "previewImageUrl": None
}

# ============================================

def push_system_hint_message(user_id, text):
    push_msg = copy.deepcopy(PUSH_TEMPLATE)
    push_msg["to"] = user_id
    TEXT_MESSAGE["text"] = "🪧"+text
    push_msg["messages"].append(TEXT_MESSAGE)
    response = requests.post(LINE_PUSH_URL, json=push_msg, headers=LINE_AUTH_HEADER)
    logging.info(f"Push text message: {text}")

    if response.status_code != 200:
        logging.error(f"Cannot push text message: {response.content}")


def push_agent_response(user_id, text):
    push_msg = copy.deepcopy(PUSH_TEMPLATE)
    push_msg["to"] = user_id
    CHAT_QUICK_RESPONSE_MESSAGE["text"] = text
    push_msg["messages"].append(CHAT_QUICK_RESPONSE_MESSAGE)

    response = requests.post(LINE_PUSH_URL, json=push_msg, headers=LINE_AUTH_HEADER)
    logging.info(f"Push text message with quick response: {text}")

    if response.status_code != 200:
        logging.error(f"Cannot push text message: {response.content}")


def send_switch_mode_message(reply_token=None, user_id=None):
    response = None

    if reply_token != None and user_id == None:
        # reply message
        reply_msg = copy.deepcopy(REPLY_TEMPLATE)
        reply_msg["messages"].append(SWITCH_MODE_MESSAGE)
        reply_msg["replyToken"] = reply_token
        response = requests.post(LINE_REPLY_URL, json=reply_msg, headers=LINE_AUTH_HEADER)

    elif reply_token == None and user_id != None:
        # push message
        push_msg = copy.deepcopy(PUSH_TEMPLATE)
        push_msg["to"] = user_id
        push_msg["messages"].append(SWITCH_MODE_MESSAGE)
        response = requests.post(LINE_PUSH_URL, json=push_msg, headers=LINE_AUTH_HEADER)

    logging.info("Send switch mode message")
    if response.status_code != 200:
        logging.error(f"Cannot send confirm template: {response.content}")



def push_generated_images(doc_dict):

    # message type of doc_dict can be: 'origin', 'vary' ...
    # the derived upscale info will form push message

    push_msg = copy.deepcopy(PUSH_TEMPLATE)
    push_msg["to"] = doc_dict["userId"]
    template = copy.deepcopy(IMAGE_CAROUSEL_MESSAGE)


    for idx, obj in enumerate(template["template"]["columns"]):
        # get corresponding upscale info
        upscale_dict = db["Image"].find_one({'messageId': doc_dict["U"+str(idx+1)]})

        if upscale_dict == None:
            return False

        # set image link
        #obj["thumbnailImageUrl"] = upscale_dict["imageUrl"]
        #obj["defaultAction"]["uri"] = upscale_dict["imageUrl"]
        local_link = "https://" + HOSTNAME + "/images/" + upscale_dict["reference"] + "/" + upscale_dict["imageId"] + ".png"
        obj["thumbnailImageUrl"] = local_link
        obj["defaultAction"]["uri"] = local_link

        # set varation options
        obj["actions"][0]["data"] += upscale_dict["vary_strong_id"]
        obj["actions"][1]["data"] += upscale_dict["vary_subtle_id"]


    push_msg["messages"].append(template)
    #logging.debug(f"image_carousel_template: {template}")

    # send to line server 
    response = requests.post(LINE_PUSH_URL, json=push_msg, headers=LINE_AUTH_HEADER)
    logging.info(f"Push image message")

    if response.status_code != 200:
        logging.error(f"Cannot push image message: {response.content}")
        return False
    return True


