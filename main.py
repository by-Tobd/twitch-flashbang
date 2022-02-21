from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.types import AuthScope
from twitchAPI.pubsub import PubSub
from elgato import Elgato, State
import os, toml, asyncio

# Turn Light to specified settings and reset after duration
async def flashbang(file):
    config = toml.load(file)
    async with Elgato(config.get("host")) as elgato:
        before_state: State = await elgato.state()
        await elgato.light(brightness=config.get("brightness"), on=True, temperature=((10**6)/config.get("temperature")))
        await asyncio.sleep(config.get("duration"))
        await elgato.light(brightness=before_state.brightness, on=before_state.on, temperature=before_state.temperature)

# flashbang all keylights
async def start_flashbang():
    devices = getDevices()
    for device in devices:
        asyncio.create_task(flashbang(device))
    await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})

# get info about all keylights and show
async def show_info():
    devices = getDevices()    
    for device in devices:
        asyncio.create_task(get_info(device))
    infos = await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})
    for info in infos:
        print(f"Name: {info[0]}\nHost: {info[1]}\nInfo: {info[2]}\nState: {info[3]}\n\n")

# Get info about Keylight
async def get_info(file):
    config = toml.load(file)
    result = list()
    result.append(os.path.basename(file).split(".")[0])
    result.append(config.get("host"))
    async with Elgato(config.get("host")) as elgato:
        result.append(await elgato.info())
        result.append(await elgato.state())
    return result
    
# get config files for keylights in "devices"
def getDevices():
    folder = os.path.abspath("devices")
    contains = os.listdir(folder)
    devices = list()
    for file in contains:
        path = os.path.join(folder, file)
        if os.path.isfile(path):
            devices.append(path)
    return devices


# Callback function for Redeem Event
def on_event(uuid, data):
    # Check if event is the Flashbang
    if data["type"] == "reward-redeemed":
        id = data["data"]["redemption"]["reward"]["id"]
        name = data["data"]["redemption"]["reward"]["title"]
        config = toml.load("config.toml")
        if config.get("reward_name") == name or config.get("reward_id") == id:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(start_flashbang())


if __name__ == "__main__":
    if os.path.isfile("config.toml"):
        config = toml.load("config.toml")
        #Create TwitchAPI object
        twitch = Twitch(config.get("client_id"), config.get("client_secret"))
        scope = [AuthScope.CHANNEL_READ_REDEMPTIONS]
        
        # Read User Token from Config or promt user to generate one
        if not config.get("refresh_token"):
            auth = UserAuthenticator(twitch, scope, force_verify=False)
            token, refresh_token = auth.authenticate()
        else:
            token, refresh_token = refresh_access_token(config.get("refresh_token"), config.get("client_id"), config.get("client_secret"))
        
        # Save new token
        config.update({"refresh_token":refresh_token})
        toml.dump(config, open("config.toml", "w"))
        
        # Apply Token to twitchAPI
        twitch.set_user_authentication(token, scope, refresh_token)
        # Get UserID from name, used to identify channel
        user_id = twitch.get_users(logins=config.get("username"))["data"][0]["id"]
        
        # Connect to pubsub and setup Callback for Reward redeem
        pubsub = PubSub(twitch)
        pubsub.start()
        uuid = pubsub.listen_channel_points(user_id, on_event)
        loop = asyncio.new_event_loop()
        try:
            # Keep Script alive and enable test cmds
            while True:
                msg = input("exit to close, info to show elgato info, test to flashbang ...")
                if msg == "exit":
                    break
                elif msg == "info":
                    loop.run_until_complete(show_info())
                elif msg == "test":
                    loop.run_until_complete(start_flashbang())
        finally:
            pubsub.stop()
