from template.discord_template import DISCORD_IMAGINE_URL, DISCORD_AUTH_HEADER
from template.discord_template import form_imagine_message, form_option_message
from template.line_template import push_generated_images

import copy, logging
import json, requests, time, pathlib
from os.path import join
from datetime import datetime
from time_helper import generate_current_timestamp, datetime_to_timestamp, print_readable_datetime

from settings import db, STATIC_ROOT


# ============================

IMAGE_DICT_4V = {
    "messageId" : None,
    "attachmentId" : None,
    "customId" : None, # need to specify when type is 'vary' 
    "userId" : None,
    "type" : None, # 'origin' or 'vary'
    "reference" : None,
    "sent_timestamp" : None,
    "isFinished" : False,
    "finished_timestamp" : None,
    "prompt" : None,
    "description" : None,
    "filename" : None,
    "imageUrl" : None,
    "imageId" : None,
    "components" : "[]",
    "U1" : None,
    "U2" : None,
    "U3" : None,
    "U4" : None
}

IMAGE_DICT_1U = {
    "messageId" : None,
    "attachmentId" : None,
    "customId" : None,
    "userId" : None,
    "type" : None, # 'upscale'
    "reference" : None,
    "sent_timestamp" : None,
    "isFinished" : False,
    "finished_timestamp" : None,
    "prompt" : None,
    "description" : None,
    "filename" : None,
    "imageUrl" : None,
    "imageId" : None,
    "components" : "[]",
    "vary_strong_id" : None,
    "vary_subtle_id" : None
}

# ============================


def get_image_info_by_custom_id(custom_id, column_name):
    image_doc = db["Image"].find_one({column_name: custom_id})
    return image_doc['messageId'], image_doc['prompt']#, image_doc['reference']



def create_image(user_id, image_type, prompt, custom_id=None, reference_id=None):
    
    # --choose image base
    image_dict = None
    if image_type == "upscale":
        image_dict = copy.deepcopy(IMAGE_DICT_1U)
    else: # origin, vary, ...
        image_dict = copy.deepcopy(IMAGE_DICT_4V)

    # -- set info
    image_dict["userId"] = user_id
    image_dict["type"] = image_type
    image_dict["prompt"] = prompt

    # -- set timestamp
    target_timestamp = generate_current_timestamp()
    image_dict["sent_timestamp"] = target_timestamp
    print_readable_datetime(target_timestamp)

    # -- if it is a custom operation (all types except 'origin')
    if custom_id != None and reference_id != None:
        image_dict["customId"] = custom_id
        image_dict["reference"] = reference_id

    # -- set prompt (only for 'origin')
    #if prompt != None:
    #    image_dict["prompt"] = prompt
    

    # create image document
    result = db["Image"].insert_one(image_dict)
    return result.inserted_id    


def send_origin_request(prompt):
    template = form_imagine_message(prompt)
    logging.debug(f"template: {template}")
    r = requests.post(DISCORD_IMAGINE_URL, json=template, headers = DISCORD_AUTH_HEADER)
    logging.debug(r.status_code)
    logging.debug(r.content)  
    if r.status_code != 204:
    	return False
    return True

def send_option_request(message_id, custom_id):
    template = form_option_message(message_id, custom_id)
    r = requests.post(DISCORD_IMAGINE_URL, json=template, headers=DISCORD_AUTH_HEADER)
    logging.debug(r.status_code)
    logging.debug(r.content)
    if r.status_code != 204:
    	return False
    return True


def patch_image(doc_id, message, description=None, parsed_dict={}, push_event=None):

    # patch additional info
    update_dict = {}
    update_dict["isFinished"] = True
    # transform original iso datetime to timestamp
    original_dt_obj = datetime.fromisoformat(message["timestamp"])
    target_timestamp = datetime_to_timestamp(original_dt_obj)
    update_dict["finished_timestamp"] = target_timestamp
    print_readable_datetime(target_timestamp)
    
    update_dict["messageId"] = message["id"]
    update_dict["attachmentId"] = message["attachments"][0]["id"]
    update_dict["filename"] = message["attachments"][0]["filename"]
    update_dict["imageUrl"] = message["attachments"][0]["url"]
    update_dict["components"] = json.dumps(message["components"])


    # -- get imageId from filename
    # authenticitypursuer_Alien_species_living_inside_the_earth_a3d6b383-e34d-43e4-822e-8d01762748b8.png
    filename_without_extension = message["attachments"][0]["filename"].split('.')[0] # [1] should be 'png'
    imageId = filename_without_extension.split('_')[-1]
    logging.debug(f"imageId : {imageId}")
    update_dict["imageId"] = imageId
    
    
    # -- set description for custom operation
    column = None
    if description != None:
        update_dict["description"] = description

        # get corresponding column name
        if "Image #" in description:
            logging.debug(f"description: {description}")
            column = "U" + description.split("#")[1].replace(" ", "")

    # update image doc
    result = db["Image"].update_one({"_id" : doc_id}, {"$set" : update_dict})
    

    # ------------------------
    # only 'upscale' image need following settings

    if column != None:

        # 1. save parsed dict for current record
        if len(list(parsed_dict.keys())) > 0:
            COLUMN_MAPPING = { "Vary (Subtle)" : "vary_subtle_id", "Vary (Strong)" : "vary_strong_id" }

            update_custom_dict = {}
            for key in list(parsed_dict.keys()):
                if key in list(COLUMN_MAPPING.keys()):
                    update_custom_dict[COLUMN_MAPPING[key]] = parsed_dict[key]

            db["Image"].update_one({"_id" : doc_id}, {"$set" : update_custom_dict })


        # 2. if reference exist, trace back and fill messageId info
        reference_id = db["Image"].find_one({'_id': doc_id})["reference"]
        if reference_id != None:
            # find corresponding doc id
            try_count = 0
            while db['Image'].find_one({'messageId': reference_id}) == None and try_count < 10:
                try_count += 1
                time.sleep(1)

            reference_doc_id = db["Image"].find_one({'messageId': reference_id})['_id']
            logging.debug(f"reference_doc_id : {reference_doc_id}")
            
            # update
            column_dict = {column : message["id"]}
            logging.debug(f"column_dict : {column_dict}")
            db["Image"].update_one({"_id" : reference_doc_id}, {"$set" : column_dict })
            
            
            # 3. download image by url
            # - create folder by reference_id
            pathlib.Path(join(STATIC_ROOT, "images", reference_id)).mkdir(parents=False, exist_ok=True)
            
            # - save image by imageId
            resp = requests.get(update_dict["imageUrl"])
            if resp.status_code == 200:
                save_filename = imageId + "." + resp.headers.get('content-type').split('/')[1]
                save_image_path = join(STATIC_ROOT, "images", reference_id, save_filename)
    
                with open(save_image_path, 'wb') as f:
                    f.write(resp.content)

            # ===============================
            # check if ready to push message to Line user
            # ===============================

            # confirm if all upscaled images are filled
            all_setted_tag = True
            reference_dict = db["Image"].find_one({'_id': reference_doc_id})
            for key in ["U1", "U2", "U3", "U4"]:
                if reference_dict[key] == None:
                    all_setted_tag = False
                    
            if all_setted_tag and push_event.isSet() == False:
                push_event.set()
                push_generated_images(reference_dict)



