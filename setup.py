import toml, os
from twitchAPI.twitch import Twitch
from twitchAPI import oauth
from twitchAPI.types import AuthScope
from twitchAPI import types
from twitchAPI.pubsub import PubSub
import time

event_happened = False
rew_id = ""
rew_name = ""

def authenticated_twitch(scopes:list[AuthScope]) -> Twitch:
    config = toml.load("config.toml")
    twitch = Twitch(config.get("client_id"), config.get("client_secret"))
    
    generateNewToken = False
    # Read User Token from Config or promt user to generate one
    try:
        token, refresh_token = oauth.refresh_access_token(config.get("refresh_token"), config.get("client_id"), config.get("client_secret"))
    except types.InvalidRefreshTokenException:
        generateNewToken = True
    

    if not generateNewToken:
        validation = oauth.validate_token(token)
        if not all(i in validation.get("scopes") for i in scopes):
            oauth.revoke_token(config.get("client_id"), refresh_token)
            generateNewToken = True
        
    if generateNewToken:
        auth = oauth.UserAuthenticator(twitch, scopes, force_verify=False)
        token, refresh_token = auth.authenticate()

    # Save new token
    config.update({"refresh_token":refresh_token})
    toml.dump(config, open("config.toml", "w"))
    
    # Apply Token to twitchAPI
    twitch.set_user_authentication(token, scopes, refresh_token)

    return twitch

def main():
    os.makedirs("devices", exist_ok=True)
    setup_config()
    print("Adding Devices")
    setupDevices()

def setupDevice():
    config = dict()
    name = input("Name (only used for filenaming): ")
    config["host"] = input("Hostname or IP: ")
    temp = input("Temperature (leave empty to not change value): ")
    if temp:
        config["temperature"] = int(temp)
    config["brightness"] = int(input("Brightness: "))
    config["duration"] = float(input("Duration: "))
    toml.dump(config, open(f"devices/{name}.toml", "w"))
    


def setupDevices():
    setupDevice()
    while True:
        if input("Do you want to add another Keylight (y/n): ") == "n":
            break
        setupDevice()


def on_event(uuid, data):
    # Check if event is the Flashbang
    if data["type"] == "reward-redeemed":
        global rew_id, rew_name, event_happened
        rew_id = data["data"]["redemption"]["reward"]["id"]
        rew_name = data["data"]["redemption"]["reward"]["title"]
        event_happened = True

def detectReward(username):
    global event_happened, rew_id, rew_name
    twitch = authenticated_twitch([AuthScope.CHANNEL_MANAGE_REDEMPTIONS, AuthScope.CHANNEL_READ_REDEMPTIONS])

    # Get UserID from name, used to identify channel
    user_id = twitch.get_users(logins=username)["data"][0]["id"]
    
    # Connect to pubsub and setup Callback for Reward redeem
    pubsub = PubSub(twitch)
    pubsub.start()
    uuid = pubsub.listen_channel_points(user_id, on_event)
    print(f"Listening to Rewards in Channel: {username} (id: {user_id})")
    while True:
        if event_happened:
            print(f"Reward Name: {rew_name}, Reward ID: {rew_id}")
            if input("Are these right (y/n): ") == "y":
                return rew_id, rew_name
            else:
                event_happened = False
        else:
            time.sleep(1)

                
def createReward(config:dict):
    twitch = authenticated_twitch([AuthScope.CHANNEL_MANAGE_REDEMPTIONS, AuthScope.CHANNEL_READ_REDEMPTIONS])
    user_id = twitch.get_users(logins=config.get("username"))["data"][0]["id"]
    print("Creating Reward")

    title = input("Title: ")
    prompt = input("Description: ")
    cost = int(input("Cost: "))
    is_enabled = input("Is enabled (y/n) [y]: ") != "n"

    background_color = input("Background color (Hex color) [None]: ")
    background_color = None if background_color == "" else background_color

    is_user_input_required = input("Is user input required (y/n) [n]: ") == "y"

    max_per_stream = input("Maximum per Stream [Unlimited]: ")
    is_max_per_stream_enabled = False
    if max_per_stream.isdigit():
        is_max_per_stream_enabled = True
        max_per_stream = int(max_per_stream)
    else:
        max_per_stream=None
    

    max_per_user_per_stream = input("Maximum per User per Stream [Unlimited]: ")
    is_max_per_user_per_stream_enabled = False
    if max_per_user_per_stream.isdigit():
        is_max_per_user_per_stream_enabled = True
        max_per_user_per_stream = int(max_per_user_per_stream)
    else:
        max_per_user_per_stream = None

    global_cooldown_seconds = input("Cooldown (in seconds) [None]: ")
    is_global_cooldown_enabled = False
    if global_cooldown_seconds.isdigit():
        is_global_cooldown_enabled = True
        global_cooldown_seconds = int(global_cooldown_seconds)
    else:
        global_cooldown_seconds = None

    should_redemptions_skip_request_queue = input("Skip request queue (y/n) [n]: ") == "y"

    reward = twitch.create_custom_reward(user_id,
        title,
        cost,
        prompt,
        is_enabled=is_enabled,
        background_color=background_color,
        is_user_input_required=is_user_input_required,
        is_max_per_stream_enabled=is_max_per_stream_enabled,
        max_per_stream=max_per_stream,
        is_max_per_user_per_stream_enabled=is_max_per_user_per_stream_enabled,
        max_per_user_per_stream=max_per_user_per_stream,
        is_global_cooldown_enabled=is_global_cooldown_enabled,
        global_cooldown_seconds=global_cooldown_seconds, 
        should_redemptions_skip_request_queue=should_redemptions_skip_request_queue
    )
    
    reward_id   = reward["data"][0]["id"]
    reward_name = reward["data"][0]["title"]
    return reward_id, reward_name


def setup_config():
    config = dict()
    try:
        config = toml.load("config.toml")
    except:
        pass
    print("Leave any field empty to use default. Default value in [], mandatory if none given")
    username = input("Twitch Username [in config]: ")
    client_id = input("Client ID [in config]: ")
    client_secret = input("Client Secret [in config]: ")

    if username != "":
        config["username"] = username
    if client_id != "":
        config["client_id"] = client_id
    if client_secret != "":
        config["client_secret"] = client_secret

    toml.dump(config, open("config.toml", "w"))

    rewardPromt = input("Auto-detect (a), create (c) or manually (m) add Reward [m]: ")
    if rewardPromt == "a":
        reward_id, reward_name = detectReward(config["username"])
    elif rewardPromt == "c":
        reward_id, reward_name = createReward(config)
    else:
        reward_name = input("Reward Name [in config]: ")
        reward_id = input("Reward ID [in config]: ")

    if reward_name != "":
        config["reward_name"] = reward_name
    if reward_id != "":
        config["reward_id"] = reward_id


    toml.dump(config, open("config.toml", "w"))

if __name__ == "__main__":
    main()
