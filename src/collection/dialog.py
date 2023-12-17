from template.openai_template import MODEL, CHAT_PARAMS, CHAT_OBJ, CHAT_TEMPLATE
from template.openai_template import TEXT_EXTENSION_ELEMENT, IMAGE_EXTENSION_ELEMENT
from collection.user import get_user_dialog_count

import copy, logging

import pymongo
from settings import db


# ============================

SYSTEM_DIALOG_DICT = {
    "userId" : None,
    "source" : "system",
    "content" : None,
    "dialog_count" : 0,
    "dialog_order" : 0,
    "timestamp" : None
}

USER_DIALOG_DICT = {
        "messageId" : None,
        "source" : "user", # include "system"
        "userId" : None,
        "dialog_count" : 0,
        "dialog_order" : 0,
        "content" : None,
        "contentType" : None, # 'normal' or 'extension'
        "timestamp" : None,
        "replyToken" : None,
        "agent_model" : MODEL,
        "parameters" : CHAT_PARAMS,
        "mere_prompt_tokens" : None,
}

AGENT_DIALOG_DICT = {
        "messageId" : None,
        "source" : "assistant",
        "userId" : None, 
        "dialog_count" : 0,
        "dialog_order" : 0,
        "content" : None,
        "timestamp" : None,
        "agent_model" : None,
        "prompt_tokens" : None,
        "completion_tokens" : None,
        "total_tokens" : None,
        "finish_reason" : None # 'stop' or 'length'
}

# ============================


def save_user_dialog(user_id, event, image_url=None):
    
    # save common message info
    dialog_dict = copy.deepcopy(USER_DIALOG_DICT)
    dialog_dict["userId"] = user_id
    
    if image_url == None:
        dialog_dict["contentType"] = "normal"
        dialog_dict["messageId"] = event["message"]["id"]
        dialog_dict["replyToken"] = event["replyToken"]
        dialog_dict["timestamp"] = event["timestamp"]
        # directly save text content
        dialog_dict["content"] = event["message"]["text"]
        
    else: 
        # turn into list
        dialog_dict["contentType"] = "extension"
        dialog_dict["messageId"] = [ event["message"]["id"] ]
        dialog_dict["replyToken"] = [ event["replyToken"] ]
        dialog_dict["timestamp"] = [ event["timestamp"] ]
        
        # tranform format to save image content
        image_ele = copy.deepcopy(IMAGE_EXTENSION_ELEMENT)
        image_ele["image_url"]["url"] = image_url
        dialog_dict["content"] =  [ image_ele ]
            

    dialog_count = get_user_dialog_count(user_id)
    dialog_dict["dialog_count"] = dialog_count
    dialog_dict["dialog_order"] = len(list(db["Dialog"].find({"userId" : user_id, "dialog_count" : dialog_count}))) + 1
    db["Dialog"].insert_one(dialog_dict)


def append_user_dialog(doc_id, event, element_type, content):
    extension_dialog = db["Dialog"].find_one({'_id' : doc_id})
    update_dialog_dict = {}

    # append message info
    update_dialog_dict["messageId"] = extension_dialog["messageId"] + [ event["message"]["id"] ]
    update_dialog_dict["replyToken"] = extension_dialog["replyToken"] + [ event["replyToken"] ]
    update_dialog_dict["timestamp"] = extension_dialog["timestamp"] + [ event["timestamp"] ]

    # form element according to type
    ele = None
    if element_type == "text":
        ele = copy.deepcopy(TEXT_EXTENSION_ELEMENT)
        ele["text"] = content
    elif element_type == "image_url":
        ele = copy.deepcopy(IMAGE_EXTENSION_ELEMENT)
        ele["image_url"]["url"] = content
        
    # append element in content list
    update_dialog_dict["content"] = extension_dialog["content"] + [ele]
    db["Dialog"].update_one({"_id" : doc_id}, {"$set" : update_dialog_dict})
        
        
def get_dialog_if_last_type_is_image(user_id):
    dialog_count = get_user_dialog_count(user_id)
    
    # find dialog with max order
    results = db["Dialog"].find({"dialog_count" : dialog_count})
    #if len(list(results)) > 1: # all dialog starts with system description, so there is at lease 1 record
    max_order = 0
    max_id = None
    for result in results:
        if result["dialog_order"] > max_order:
            max_order = result["dialog_order"]
            max_id = result["_id"]
                  
    # --check if last dialog is from user
    target = db["Dialog"].find_one({"_id" : max_id})
    if target["source"] != "user":
        return None
        
    # --check contentType
    if target["contentType"] != "extension":
        return None
    
    # --further check if the dialog is finished with a text 
    last_content_obj = list(target["content"])[-1]
    if last_content_obj['type'] == "image_url" :
        # -- the dialog hasn't finished yet, requires a text to describe image
        return max_id
            
    # -- the extension dialog is finished, should start new dialog next time 
    return None
    #return None


def save_assistant_dialog(user_id, json_data):

    # get current dialog's count order
    dialog_count = get_user_dialog_count(user_id)
    dialog_results = list(db["Dialog"].find({"userId" : user_id, "dialog_count" : dialog_count}).sort("dialog_order", pymongo.ASCENDING))
    current_dialog_order = len(dialog_results)

    # save dialog doc
    dialog_dict = copy.deepcopy(AGENT_DIALOG_DICT)
    dialog_dict["messageId"] = json_data["id"]
    dialog_dict["agent_model"] = json_data["model"]

    dialog_dict["userId"] = user_id
    #dialog_dict["source"] = "assistant"
    dialog_dict["content"] = json_data['choices'][0]['message']['content']
    dialog_dict["timestamp"] = json_data["created"]
    dialog_dict["finish_reason"] = json_data["choices"][0]["finish_reason"]

    dialog_dict["dialog_count"] = dialog_count
    dialog_dict["dialog_order"] = current_dialog_order + 1

    dialog_dict["prompt_tokens"] = json_data["usage"]["prompt_tokens"]
    dialog_dict["completion_tokens"] = json_data["usage"]["completion_tokens"]
    dialog_dict["total_tokens"] = json_data["usage"]["total_tokens"]
    db["Dialog"].insert_one(dialog_dict)

    # update token count of last dialog
    current_dialog_order -= 1
    last_total_tokens = 0
    while current_dialog_order >= 0:
        target_dialog = dialog_results[current_dialog_order-1] # minus 1 for list index
        #target_dialog = dialog_results.find_one({"dialog_order" : current_dialog_order})
        if target_dialog["source"] == "assistant":
            last_total_tokens = int(target_dialog["total_tokens"])
            break
        current_dialog_order -= 1

    mere_prompt_tokens = dialog_dict["prompt_tokens"] - last_total_tokens
    db["Dialog"].update_one({"userId" : user_id, "dialog_count" : dialog_dict["dialog_count"], "dialog_order" : dialog_dict["dialog_order"]-1}, {"$set" : {"mere_prompt_tokens": mere_prompt_tokens}})



def delete_all_dialogs_of_user(user_id):
    # get dialog count
    dialog_count = get_user_dialog_count(user_id)

    # proceed to remove user-related records
    result = db["Dialog"].delete_many({ "userId" : user_id })
    if dialog_count != 0 and result.deleted_count == 0:
        logging.error(f"Unable to remove dialogs of user: {user_id}")
        return False
    else:
        logging.info(f"Remove all dialogs of user: {user_id}")
        return True



def start_new_dialog(user_id):
    user_doc = db["User"].find_one({"userId" : user_id})

    # check if the user has initate any dialog 
    newTag = False
    if user_doc["dialog_count"] == 0:
        newTag = True

    # check if current_count has any dialog
    count = len(list(db["Dialog"].find({"userId" : user_id, "dialog_count" : user_doc["dialog_count"]})))
    if count > 1:
        newTag = True

    # -------------------
    if newTag:
        # increase dialog index
        new_dialog_count = user_doc["dialog_count"] + 1

        # generate initial hidden system instruction
        dialog_dict = copy.deepcopy(SYSTEM_DIALOG_DICT)
        dialog_dict["userId"] = user_id
        #dialog_dict["source"] = "system"
        dialog_dict["content"] = "請簡短回答，勿超出100字"

        dialog_dict["dialog_count"] = new_dialog_count
        dialog_dict["dialog_order"] = 1
        db["Dialog"].insert_one(dialog_dict)

        # update user document
        db["User"].update_one({"_id" : user_doc["_id"]}, {"$set" : {"dialog_count": new_dialog_count }})
        #logging.info("Start new dialog for user: {user_id}")


def form_chat_payload_outof_history_dialog(user_id):
    # get current dialog count of the user
    dialog_count = get_user_dialog_count(user_id)
    
    # form json payload data for chat request
    chat_dict = copy.deepcopy(CHAT_TEMPLATE)
    results = db["Dialog"].find({'userId' : user_id, 'dialog_count' : dialog_count}).sort("dialog_order", pymongo.ASCENDING)
    
    # form dict according to type: 'normal' or 'extension'
    for result in results:
        chat_obj = copy.deepcopy(CHAT_OBJ)
        chat_obj["role"] = result["source"]
        chat_obj["content"] = result["content"]
        chat_dict["messages"].append(chat_obj)
    return chat_dict


