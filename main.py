from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.types import AuthScope
from twitchAPI.pubsub import PubSub
from elgato import Elgato, State
import os, toml, asyncio

# Turn Light to specified settings and reset after duration
async def flashbang():
    config = toml.load("config.toml")
    async with Elgato(config.get("keylight")) as elgato:
        before_state: State = await elgato.state()
        await elgato.light(brightness=config.get("brightness"), on=True, temperature=((10**6)/config.get("temperature")))
        await asyncio.sleep(config.get("duration"))
        await elgato.light(brightness=before_state.brightness, on=before_state.on, temperature=before_state.temperature)

# Get info about Keylight and show to user
async def show_info():
    config = toml.load("config.toml")
    print(config.get("keylight"))
    async with Elgato(config.get("keylight")) as elgato:
        print(await elgato.info())
        print(await elgato.state())

# Callback function for Redeem Event
def on_event(uuid, data):
    # Check if event is the Flashbang
    if data["type"] == "reward-redeemed":
        id = data["data"]["redemption"]["reward"]["id"]
        name = data["data"]["redemption"]["reward"]["title"]
        config = toml.load("config.toml")
        if config.get("reward_name") == name or config.get("reward_id") == id:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(flashbang())


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
        try:
            # Keep Script alive and enable test cmds
            while True:
                msg = input("exit to close, info to show elgato info, test to flashbang ...")
                if msg == "exit":
                    break
                elif msg == "info":
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(show_info())
                elif msg == "test":
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(flashbang())
        finally:
            pubsub.stop()
