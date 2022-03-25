import setup
from twitchAPI.types import AuthScope
from twitchAPI.pubsub import PubSub
from elgato import Elgato, State
import os, toml, asyncio

debug = False

# Turn Light to specified settings and reset after duration
async def flashbang(file):
    config = toml.load(file)
    async with Elgato(config.get("host")) as elgato:
        before_state: State = await elgato.state()
        temp = before_state.temperature
        if config.get("temperature"):
            temp = (10**6)/config.get("temperature")
        await elgato.light(brightness=config.get("brightness"), on=True, temperature=temp)
        await asyncio.sleep(config.get("duration"))
        await elgato.light(brightness=before_state.brightness, on=before_state.on, temperature=before_state.temperature)

# flashbang all keylights
async def start_flashbang():
    debug_log("Start Flashbang")
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
    debug_log(f"Event happened: {data}")
    if data["type"] == "reward-redeemed":
        id = data["data"]["redemption"]["reward"]["id"]
        name = data["data"]["redemption"]["reward"]["title"]
        config = toml.load("config.toml")

        debug_log(f"Reward redeemed (Name: {name}, ID: {id})")
        if config.get("reward_name") == name or config.get("reward_id") == id:
            run(start_flashbang())

def run(awaitable):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        tsk = loop.create_task(awaitable)
    else:
        asyncio.run(awaitable)

def debug_log(msg):
    if debug:
        print(msg)

if __name__ == "__main__":
    if os.path.isfile("config.toml"):
        config = toml.load("config.toml")

        #Create TwitchAPI object
        twitch = setup.authenticated_twitch([AuthScope.CHANNEL_READ_REDEMPTIONS, AuthScope.CHANNEL_MANAGE_REDEMPTIONS])

        # Get UserID from name, used to identify channel
        user_id = twitch.get_users(logins=config.get("username"))["data"][0]["id"]
        
        # Connect to pubsub and setup Callback for Reward redeem
        pubsub = PubSub(twitch)
        pubsub.start()

        uuid = pubsub.listen_channel_points(user_id, on_event)
        try:
            # Keep Script alive and enable test cmds
            while True:
                msg = input("exit to close, info to show elgato info, test to flashbang, debug to toggle debug messages ...")
                if msg == "exit":
                    break
                elif msg == "info":
                    run(show_info())
                elif msg == "test":
                    run(start_flashbang())
                elif msg == "debug":
                    debug = not debug
                    print(f"Debug: {debug}")
        finally:
            pubsub.stop()
