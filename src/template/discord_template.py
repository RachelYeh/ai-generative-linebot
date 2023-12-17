import uuid, copy

USER_ID = "..."
USER_NAME = "..."
GUILD_ID = "..."
CHANNEL_ID = "..."
DISCORD_MESSAGES_URL = "https://discord.com/api/v8/channels/" + CHANNEL_ID  + "/messages"

DISCORD_IMAGINE_URL = "https://discord.com/api/v9/interactions"
DISCORD_AUTH_HEADER = {'Authorization' : '...'}


# ------------------------------------------------
#  Use slash commands: Imagine
# ------------------------------------------------

# refer to : https://discord.com/developers/docs/interactions/application-commands#application-command-object
APP_CMD = {
        "id": "938956540159881230", # command id
        "application_id": "936929561302675456",
        "version":"1166847114203123795", # command version
        "default_member_permissions": None,
        "type": 1,
        "nsfw": False,
        "name":"imagine", # command name
        "description": "Create images with Midjourney", # command description
        "dm_permission": True,
        "contexts": [0, 1, 2],
        "integration_types": [0],
        "options": [
            {   "type": 3,
                "name": "prompt",
                "description": "The prompt to imagine",
                "required": True
            }
        ]
}

# refer to : https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-object-application-command-interaction-data-option-structure
IMAGINE_DATA = {
        "version": "1166847114203123795",
        "id": "938956540159881230",
        "name" :"imagine",
        "type": 1, # [Application Command Types] CHAT_INPUT : Slash commands
        "options":[
            {   "type": 3, # [Application Command Option Type] STRING
                "name": "prompt",
                "value": None
            }
        ],
        "application_command": APP_CMD
}

# refer to : https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-object-interaction-structure
IMAGINE_TEMPLATE = {
        "type": 2, # [Interaction Type] APPLICATION_COMMAND
        "application_id": "936929561302675456", # midjourney's bot
        "guild_id": GUILD_ID, # my private server 
        "channel_id": CHANNEL_ID, # general channel in server
        "session_id": None,
        "data": IMAGINE_DATA,
        "attachments": []
}

def get_random_session_id():
    session_id = str(uuid.uuid4()).replace('-', '')
    return session_id

def form_imagine_message(prompt):
    template = copy.deepcopy(IMAGINE_TEMPLATE)
    template['data']['options'][0]['value'] = prompt
    template['session_id'] = get_random_session_id()
    return template


# ------------------------------------------------
#  Message Options: Upscale, Vary
# ------------------------------------------------

# refer to : https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-object-message-component-data-structure
# refer to : https://discord.com/developers/docs/interactions/message-components#component-object-component-types
CHOOSE_OPTION_DATA = {
    "component_type": 2, #[Component Types] Button object
    "custom_id": None
}

OPTION_TEMPLATE = {
        "type": 3, # [Interaction Type] MESSAGE_COMPONENT
        "application_id": "936929561302675456", # midjourney's bot
        "guild_id": GUILD_ID, # my private server
        "channel_id": CHANNEL_ID, # general channel in server
        #"message_flags": 0,
        "message_id": None,
        "session_id": None,
        "data": CHOOSE_OPTION_DATA
}

def form_option_message(message_id, custom_id):
    template = copy.deepcopy(OPTION_TEMPLATE)
    template['data']['custom_id'] = custom_id
    template['session_id'] = get_random_session_id()

    # get messageId
    template['message_id'] = message_id

    return template


