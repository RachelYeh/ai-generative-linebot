import copy, logging
from settings import db


# ============================

USER_DICT = {
        "userId" : None,
        "dialog_count" : 0,
        "current_dialog" : 0,
        "current_mode" : None, # 'chat' or 'imagine'
        "followTime" : None
}

# ============================


def create_user_doc(user_id, timestamp):
    user_dict = copy.deepcopy(USER_DICT)
    user_dict["userId"] = user_id
    user_dict["followTime"] = timestamp
    
    db["User"].insert_one(user_dict)
    logging.info(f"Create user: {user_id}")


def check_user_existence(user_id):
    user_doc = db["User"].find_one({'userId': user_id})
    if type(user_doc) != dict:
        logging.info("Stranger user send message, stop handling.")
        return False
    return True


def get_user_dialog_count(user_id):
    user_doc = db["User"].find_one({"userId" : user_id})
    if user_doc != None:
        return user_doc["dialog_count"]
    return None


def get_user_mode(user_id):
    user_doc = db["User"].find_one({"userId" : user_id})
    return user_doc["current_mode"]


def set_user_mode(user_id, mode):
    user_doc = db["User"].find_one({"userId" : user_id})
    db["User"].update_one({"_id" : user_doc["_id"]}, {"$set" : {"current_mode": mode}})
    logging.info(f"Update mode for user: {mode}")


def delete_user_doc(user_id):
    # remove user doc
    result = db["User"].delete_one({'userId': user_id})
    logging.info("Received 'unfollow' event, remove user info.")

    if result.deleted_count != 1:
        # fail to delete
        logging.error("Fail to delete user document!")
        return False

    # delete related resources as well
    # ...
    return True

