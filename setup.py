
import toml, os
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.types import AuthScope
from twitchAPI.pubsub import PubSub

event_happened = False
rew_id = ""
rew_name = ""

def main():
    os.makedirs("devices", exist_ok=True)
    setup_config()
    print("Adding Devices")
    setupDevices()

def setupDevice():
    config = dict()
    name = input("Name (only used for filenaming): ")
    config["host"] = input("Hostname or IP: ")
    config["temperature"] = int(input("Temperature: "))
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

def setup_config():
    config = dict()
    try:
        config = toml.load("config.toml")
    except:
        pass
    print("Write \"skip\" to use current value in config")
    username = input("Twitch Username: ")
    client_id = input("Client ID: ")
    client_secret = input("Client Secret: ")

    if username != "skip":
        config["username"] = username
    if client_id != "skip":
        config["client_id"] = client_id
    if client_secret != "skip":
        config["client_secret"] = client_secret

    refresh_token = ""

    if input("Auto-detect reward name and id (y/n): ") == "y":
        twitch = Twitch(config.get("client_id"), config.get("client_secret"))
        scope = [AuthScope.CHANNEL_READ_REDEMPTIONS]

        if not config.get("refresh_token"):
            auth = UserAuthenticator(twitch, scope, force_verify=False)
            token, refresh_token = auth.authenticate()
        else:
            token, refresh_token = refresh_access_token(config.get("refresh_token"), client_id, client_secret)
        
        # Save new token
        config.update({"refresh_token":refresh_token})
        
        # Apply Token to twitchAPI
        twitch.set_user_authentication(token, scope, refresh_token)
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
                    break
                else:
                    event_happened = False
        reward_id = rew_id
        reward_name = rew_name

    else:
        reward_name = input("Reward Name: ")
        reward_id = input("Reward ID: ")

    if reward_name != "skip":
        config["reward_name"] = reward_name
    if reward_id != "skip":
        config["reward_id"] = reward_id
    if refresh_token != "skip":
        config["refresh_token"] = refresh_token

    config.update(config)

    toml.dump(config, open("config.toml", "w"))

if __name__ == "__main__":
    main()