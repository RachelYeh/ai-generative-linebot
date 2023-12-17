from settings import app, HOSTNAME, STATIC_ROOT
from flask import request
from flask import send_from_directory

import logging
from os.path import join
import json, requests, threading#, base64
from urllib.parse import parse_qs


from template.line_template import LINE_AUTH_HEADER
from template.line_template import push_system_hint_message, push_agent_response, send_switch_mode_message
from template.openai_template import MODEL, OPENAI_AUTH_HEADER, OPENAI_CHAT_URL


from collection.user import create_user_doc, set_user_mode, get_user_mode, delete_user_doc, check_user_existence
from collection.dialog import save_user_dialog, append_user_dialog, get_dialog_if_last_type_is_image, save_assistant_dialog, delete_all_dialogs_of_user, start_new_dialog, form_chat_payload_outof_history_dialog
from collection.image import send_origin_request, send_option_request, create_image, get_image_info_by_custom_id


from discord_logic import asynchronously_handle_message
# =========================================================
from template.discord_template import DISCORD_MESSAGES_URL, DISCORD_AUTH_HEADER

@app.route('/discord/messages', methods = ['GET', 'POST'])
def messages():
    r = requests.get(DISCORD_MESSAGES_URL, headers = DISCORD_AUTH_HEADER)
    return r.content, 200
    
# =========================================================
from settings import STATIC_ROOT

@app.route("/<path:path>")
def download_static(path):
    return send_from_directory(STATIC_ROOT, path)
    
# =========================================================

@app.route('/linebot/webhook', methods = ['GET', 'POST'])
def webhook():
    #logging.debug(request.json)
    
    if 'json' not in request.mimetype:
        logging.debug(request.data.decode('utf-8'))
        return "not in json", 400

    # parse json data
    json_data = json.loads(request.data.decode('utf-8'))

    for event in json_data["events"]:
        timestamp = event["timestamp"]
        user_id = None
        if event["source"]["type"] == "user":
            user_id = event["source"]["userId"]

        # =============================
        if event["type"] == "follow" or event["type"] == "unfollow":
            
            if event["type"] == "follow":
                # save new user doc
                create_user_doc(user_id, timestamp)
                logging.info("Received 'follow' event, add new user.")
                    
                # send initial message
                send_switch_mode_message(reply_token=event["replyToken"])

            elif event["type"] == "unfollow":
                # delete user's related resource first
                if delete_all_dialogs_of_user(user_id):
                    # delete user
                    delete_user_doc(user_id)
                    logging.info("Received 'unfollow' event, remove user info.")


        # =============================
        elif event["type"] == "postback":
            postback_str = event["postback"]["data"]
            
            if "=" in postback_str:
                parsed_form = parse_qs(event["postback"]["data"])
                logging.debug(f"parsed_form: {parsed_form}")
                    
                if "mode" in list(parsed_form.keys()):
                    mode = parsed_form['mode'][0]
                    
                    # change current mode in user document
                    set_user_mode(user_id, mode)

                    # push hint message
                    text = "已切換至"
                    if mode == "chat":
                        text += "聊天模式"
                        start_new_dialog(user_id)
                    elif mode == "imagine":
                        text += "生成模式"
                    push_system_hint_message(user_id, text)


                if "custom_id" in list(parsed_form.keys()):
                    
                    custom_id = parsed_form['custom_id'][0]
                    logging.debug(f"custom_id: {custom_id}")
                    
                    # send system meesage
                    index = parsed_form['index'][0]
                    operation = parsed_form['operation'][0]
                    EXPLAIN_OPERATION_MAPPING = {'vary_strong' : '大幅變化', 'vary_subtle' : '小幅變化'}
                    push_text = "以#"+str(index)+"為基底"+EXPLAIN_OPERATION_MAPPING[operation]
                    push_system_hint_message(user_id, push_text)
                    
                    # get referenced messageId according to the opreation
                    operation_column = operation + "_id"
                    messageId, prompt = get_image_info_by_custom_id(custom_id, operation_column) 

                    # create new image record
                    doc_id = create_image(user_id, "vary", prompt, custom_id=custom_id, reference_id=messageId)

                    # send request to discord to collect detailed info
                    if send_option_request(messageId, custom_id):

                        # generate thread to wait for discord's response
                        waittask_thread = threading.Thread(target=asynchronously_handle_message, args=(doc_id, user_id, prompt,), kwargs={'image_type': "vary", 'custom_id' : custom_id, 'reference_id' : messageId})
                        waittask_thread.start()

            else:
                if postback_str == "menu":
                    send_switch_mode_message(user_id = user_id)
                
                elif postback_str == "new":
                    start_new_dialog(user_id)                        
                    logging.info("Start new dialog for user: {user_id}")
                    
                    # send system message
                    push_system_hint_message(user_id, "已開啟新對話")

        # =============================
        elif event["type"] == "message":
            # check if sender is friend
            if not check_user_existence(user_id):
                logging.info("Stranger user send message, stop handling.")
                continue

            # -- start handling message
            # check the message type
            current_mode = get_user_mode(user_id)
            
            if event["message"]["type"] == "text":

                if current_mode == "chat":
                
                    if "gpt-4-vision" in MODEL:
                        # check if the text is associate with previous image message
                        dialog_doc_id = get_dialog_if_last_type_is_image(user_id)
                        if dialog_doc_id == None:
                            # (a) start new dialog with text
                            print("scenaio a")
                            save_user_dialog(user_id, event)
                        else:
                            # (b) append text in current dialog
                            print("scenaio b")
                            append_user_dialog(dialog_doc_id, event, "text", event['message']['text'])
                            logging.info(f"Received 'message' event, save text: {event['message']['text']}")
                    else:
                        save_user_dialog(user_id, event)

                    # form json data for chat completion
                    chat_dict = form_chat_payload_outof_history_dialog(user_id)

                    # send to chatGPT
                    response = requests.post(OPENAI_CHAT_URL, json=chat_dict, headers=OPENAI_AUTH_HEADER)
                    if response.status_code != 200:
                        logging.error(f"Cannot send text to ChatGPT: {response.content}")
                        continue

                    json_data = json.loads(response.content.decode('utf-8'))
                    logging.info(f"Receive ChatGPT's response: {json_data['choices'][0]['message']['content']}")
                    
                    
                    # save response from ChatGPT
                    save_assistant_dialog(user_id, json_data)

                    # push message to LINE user
                    push_agent_response(user_id, json_data['choices'][0]['message']['content'])
                    logging.info(f"Received response from ChatGPT, push text to user: {json_data['choices'][0]['message']['content']}")


                elif current_mode == "imagine":
                        
                    prompt = event["message"]["text"]
                    if send_origin_request(prompt):
                        # send system message
                        push_system_hint_message(user_id, "生成中，請耐心等候")

                        # create image record in db
                        #doc_id = create_origin_image(user_id, prompt)
                        doc_id = create_image(user_id, "origin", prompt)

                        # use thread to wait for midjourney return generated images
                        waittask_thread = threading.Thread(target=asynchronously_handle_message, args=(doc_id, user_id, prompt,), kwargs={'image_type': 'origin'})
                        waittask_thread.start()


            elif event["message"]["type"] == "image":
            
                if current_mode == "chat" and "gpt-4-vision" in MODEL: # only 'gpt4' support image understanding
                
                    # get image content by another api
                    image_id = event["message"]["id"]
                    r = requests.get("https://api-data.line.me/v2/bot/message/"+ image_id +"/content", headers = LINE_AUTH_HEADER)
                    
                    if r.status_code == 200:
                        # 1. save image in static file
                        image_format = r.headers.get('content-type').split('/')[1]
                        filename = image_id + "." + image_format
                        image_path = join(STATIC_ROOT, "images", filename)
                        with open(image_path, 'wb') as f:
                            for chunk in r:
                                f.write(chunk)
                        """
                        # [other approach] transform image to base64 string
                        base64_str = None
                        with open(image_path, "rb") as f:
                            base64_str = base64.b64encode(f.read()).decode('utf-8')
                                  
                        image_url = None          
                        if base64_str != None:
                            # send to chatGPT
                            image_url = f"data:image/jpeg;base64,{base64_image}"
                        """
                        
                        # 2. get image url and save extension dialog
                        image_url = "https://" + HOSTNAME + "/images/" + filename
                        
                        dialog_doc_id = get_dialog_if_last_type_is_image(user_id)
                        if dialog_doc_id == None:
                            # (a) start new dialog with image
                            save_user_dialog(user_id, event, image_url=image_url)
                        else:
                            # (b) append image in current dialog
                            append_user_dialog(dialog_doc_id, event, "image_url", image_url)
                            
    return "OK!", 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(443), ssl_context=('../ssl/chained.crt', '../ssl/private.key'), debug=True, threaded=True)
