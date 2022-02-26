# Twitch Flashbang
A python script to trigger a Elgato Key Light flashbang when a user redeems a custom reward. It sets the settings of the Keylight to specified values and resets them afterwards. 
# Setup
## Installation
1. Install [Python](https://www.python.org/downloads/) (I used 3.10.0, don't know which is needed at the minimum)
2. Clone repository or download and unzip
3. Open Terminal in folder and create venv `python3 -m venv venv` or `python -m venv venv`
4. Activate enviroment Powershell: `& .\venv\Scripts\Activate.ps1` Cmd: `.\venv\Scripts\activate.bat` Bash: `source venv/bin/activate`
5. Install Requirements `pip install -r requirements.txt`
## Configuration
### Manual Config
Fill all fields in config.toml
- Username: Your Twitch name
- Client ID and secret
  1. Goto [Twitch Dev](https://dev.twitch.tv) and login
  2. Goto [Applications](https://dev.twitch.tv/console/apps) and register a new app
    - Choose a name
    - Enter `http://localhost:17563` as the OAuth Redirect URL
    - Choose a Category
  3. Click Manage on your create App
  4. Create a new Secret and copy both the ID and the Secret into their fields in the config.toml
- Refresh Token: Doesn't have to be entered, it will be generated automatically
- Reward id and name: The name and id of the custom reward that should trigger the flashbang. Only one of the fields needs to be filled. I don't know how to find them as I don't have access to custom rewards
After you filled the config, you can create as many keylight configs as you want. These have to be in the "devices" folder and have the same structure as the "example.toml"
- Host: The hostname or IP of the Elgato Keylight used
- Temperature, Brightness and Duration: These are used to configure the Flashbang
### Using setup.py
1. Run setup.py (`python setup.py`)
2. Enter values as promted (Explanations for the fields are above)

To use the reward auto-detection you follow the script until you select auto-detect. Afterwards wait until it shows `Listening to Rewards in Channel: <USERNAME> (id: <USER_ID>)` and then redeem the reward that you want to trigger the flashbang. It will show the name and id of the reward that was redeemed which you will have to confirm. 

If you create a new reward using the setup.py an are unsure about a field, they are further explained in the [twitch docs](https://dev.twitch.tv/docs/api/reference#create-custom-rewards).
# Run
1. Open Terminal in folder and activate Environment (See Installation, Step 4)
2. Run `python main.py`
3. You can type `info` and press enter to check if the connection to the Keylight works (it should show information about the light)
4. Typing `test` will trigger the flashbang as if a reward has been redeemed
