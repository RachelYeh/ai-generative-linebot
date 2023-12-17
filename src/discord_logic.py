import json, requests, re, threading, time
import logging

from collection.image import send_option_request, create_image, patch_image
from template.discord_template import DISCORD_MESSAGES_URL, DISCORD_AUTH_HEADER
from threading import Event


OPERATION_TAGS = {"upsample": "Image #", "high_variation" : "Variations (Strong)", "low_variation" : "Variations (Subtle)"}


def asynchronously_handle_message(doc_id, user_id, prompt, image_type="origin", custom_id=None, reference_id=None, event=None):
    # a)
    message, description = wait_target_message(prompt, custom_id = custom_id, reference_id = reference_id)

    if message != None:
        # c)
        parsed_dict = {}
        if image_type == "upscale":
            parsed_dict = parse_component_list(message["components"], image_type)
        else:
            parsed_dict = parse_component_list(message["components"], image_type, thread=True, user_id=user_id, messageId=message["id"], prompt=prompt)
        
        logging.debug(f"parsed_dict:{parsed_dict}")

        # b)
        patch_image(doc_id, message, description=description, parsed_dict=parsed_dict, push_event=event)         


def wait_target_message(prompt, custom_id=None, reference_id=None):
    # set message type code and operation
    TYPE_CODE = None
    OPERATION = None
    if custom_id == None:
        TYPE_CODE = 0
    else:
        TYPE_CODE = 19
        # parse custom_id
        # MJ::JOB::low_variation::1::b0a26a58-e13e-4ad5-97d3-0c0946daa5b7::SOLO
        temp = custom_id.split("::")
        OPERATION = OPERATION_TAGS[temp[2]]
        if OPERATION == "Image #":
            OPERATION += temp[3]
        logging.debug(f"custom_id:{custom_id}  OPERATION:{OPERATION}")


    # ----------------------
    #  start scan messages
    # ----------------------
    target_message = None
    description = None
    count = 0
    max_count = 30

    # loop until find target or exceed times limit
    while target_message == None and count <= max_count:
        logging.debug(f"-----------------------------------count: {count}")
        # get current messages
        response = requests.get(DISCORD_MESSAGES_URL, headers = DISCORD_AUTH_HEADER)
        messages_list = json.loads(response.content)

        # iterate through the messages and find the one matches the prompt
        for message in messages_list:
            
            # a) check type code
            if message["type"] == TYPE_CODE:
                # b) confirm if from correct reference
                if reference_id != None and "referenced_message" in list(message.keys()):
                    if reference_id != message["referenced_message"]["id"]:
                        break

                # check if matches Midjourney's format
                pattern = "\*\*(?P<prompt>.+)\*\*\s-\s(?P<description>.*)<@(?P<userid>\d+)>(\s\(fast\))*"
                match_obj = re.match(pattern, message['content'])
                if match_obj != None:
                    logging.debug(f"{prompt} [{match_obj.group('prompt') == prompt}] {match_obj.group('prompt')}")
                    found_tag = False
                    # c) check prompt
                    if match_obj.group('prompt') == prompt:
                        if custom_id != None:
                            # d) further check operation
                            if OPERATION in match_obj.group('description'):
                                found_tag = True
                                description = match_obj.group('description')
                        else:
                            found_tag = True
                            description = match_obj.group('description')

                    if found_tag:
                        target_message = message
                        break

        if target_message == None:
            # wait for 10 sec to proceed
            time.sleep(10)
            count += 1

    if target_message != None:
        logging.info(f"Found target messages: {target_message['id']}")
    return target_message, description



def parse_component_list(components, image_type, thread=False, user_id=None, messageId=None, prompt=None):
    
    PARSED_CUSTOM_DICT = {}

    # get label names
    BTN_LABELS = []
    if image_type == "upscale":
        BTN_LABELS = ["Vary (Subtle)", "Vary (Strong)"]
    else: # origin, vary, ...
        BTN_LABELS = ["U1", "U2", "U3", "U4"]

    # use event for synchronization and prevent duplicate message push
    event = Event()
    
    # parse components to retrieve variation's custom id
    for row_obj in components:
        if row_obj["type"] == 1:
            for btn in row_obj["components"]:
                if btn["type"] == 2:
                    if 'custom_id' in list(btn.keys()) and 'label' in list(btn.keys()):
                        
                        if btn["label"] in BTN_LABELS:

                            customId = btn["custom_id"]
                            PARSED_CUSTOM_DICT[btn["label"]] = btn["custom_id"]

                            if thread: 
                                # (all types except 'upscale' will proceed)
                                # parameters need to be specified: user_id, prompt, reference_id
                                DERIVED_TYPE_MAPPING = {'origin' : 'upscale', 'upscale' : 'vary', 'vary' : 'upscale'}
                                next_image_type = DERIVED_TYPE_MAPPING[image_type]

                                # create new image record
                                doc_id = create_image(user_id, next_image_type, prompt, custom_id=customId, reference_id=messageId)

                                # send request to discord to collect detailed info
                                if send_option_request(messageId, customId):

                                    # generate thread to wait for discord's response
                                    waittask_thread = threading.Thread(target=asynchronously_handle_message, args=(doc_id, user_id, prompt,), kwargs={'image_type': next_image_type, 'custom_id' : customId, 'reference_id' : messageId, 'event' : event})
                                    waittask_thread.start()
    
    return PARSED_CUSTOM_DICT

