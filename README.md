# Telegram-Discord-Bot
A TUI bot that forwards Telegram messages to Discord via webhook. It does not require any Discord or Telegram permissions, nor does it require adding any bots to Telegram group, the only thing required is the Discord webhook url.

The bot is under development, it only forward text messages and images currently. 

What's the difference between Kizmeow and other existing bots?
-----------------

|                                                                   | This Script | Other Bots |
|-------------------------------------------------------------------|:-----------:|:----------:|
|Not required to add Discord Bot to your Discord server             |   ✔        |     ❌     |
|Not required to add Telegram Bot to your Telegram group            |   ✔        |     ❌     |
|Discord webhook not required                                       |   ❌       |    ✔❌    |
|Forward message from public Telegram channel which you don't own it|   ✔        |     ❌     |
|Forward message from private Telegram channel                      |   ❌       |     ✔      |
|Forward message from private or public Telegram group              |   ❌       |     ✔❌   |
|Discord embed supported                                            |   ✔        |    ✔❌    |
|Keyword filter                                                     |   ✔        |    ✔❌    |

Usage
-----------------
1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Start the terminal UI:

```bash
python CLI.py
```

3. On the first launch, the app opens the settings page because `config.json` does not exist yet. Fill in the fields and press `Save`.

4. After a valid `config.json` exists, the app starts on the main page. Press `Start` to begin forwarding, `Stop` to stop forwarding, `Settings` to edit saved config, or `Exit` to quit.

The config file is saved next to the running app. When running from source, it is saved next to `CLI.py`. When running as a packaged binary on Windows, macOS, or Linux, it is saved next to that binary. If that folder is not writable, move the app to a writable folder before saving settings.

Below are the configuration fields:

| Name | Description | Required | Example |
|------|-------------|----------|---------|
| dc_webhook_url | The Discord webhook you got in Discord channel | Yes | https://discord.com/api/webhooks/1322806255961509930/Bhz0Q2mv6rz9gXclYAFSl7tvbqdhhbEr3no6WY6o-fWwa6rp5Mg8t_EbtvIjnuR6lb3u |
| tg_announcement_channel | The link of the public Telegram announcement channel. Public group, private group, private channel will not work | Yes | https://t.me/dsafdsfa3243 |
| embed_color | The color of the forwarded Discord embed message | Yes | 0xe8006f |
| embed_title_setting | The title style of the forwarded Discord embed message: 1 no title, 2 plain title, 3 title link | Yes | 3 |
| keyword_filter_option | Blank forwards all messages, 1 forwards messages containing keywords, 2 forwards messages not containing keywords | No | 2 |
| keyword_filter_bank | The words you want to filter, separated by comma. Required when keyword_filter_option is 1 or 2 | No | ant,bear,cat |
| forward_image | Forward messages with image: 1 yes, 2 no | Yes | 1 |
| only_plaintext | Remove multimedia and only forward plaintext: 1 yes, blank no | No | 1 |
| gemini_api_key | Google Gemini API key. Leave blank to disable translation | No | AIza... |
| model | Gemini model. Required when gemini_api_key is set | No | gemini-2.5-flash-lite |
| translation_prompt | Translation prompt. Required when gemini_api_key is set | No | Please translate it naturally into English (en-US) |
| check_message_every_n_sec | How many seconds the bot waits between checks | Yes | 20 |
| content_text | Add custom content text above the embed | No | This message is forward from Telegram =w= |

The table below shows the steps to get these parameters.

|               Parameter Name               |                                 How to get the parameter?                                 |
|--------------------------------------------|-------------------------------------------------------------------------------------------|
|             Discord webhook URL            | ![image](https://github.com/user-attachments/assets/9798b6ea-9be7-40b5-8169-87e3445d1c8d) |
|    Telegram public announcement channel    | ![image](https://github.com/user-attachments/assets/98f40aad-471c-42bf-b2c6-038fcc639e77) |
|                Embed color                 | ![image](https://github.com/user-attachments/assets/d072d6d9-22e1-412d-8278-7a6676e7feb0) |



FAQ
-----------------

<details>
<summary>Do I need to keep my computer on if I want to make this script running 7/24?</summary>
Yes.
</details>

<details>
<summary>Does this script only works on public channels?</summary>
Yes. This script does *not* works in group(private/public), channel(private). The purpose of this script is *forward message in a public Telegram channel which you don't own it to a Discord server which only requires manage webhook permission*. If you are the admin of both Telegram group and Discord channel, you can try [IFTTT](https://ifttt.com/explore), it's much more easier to set up.
</details>

<details>
<summary>I don't want to enter the config every time I start the script. Does it save settings?</summary>
Yes. The TUI saves settings to `config.json` next to the running app. This file contains your Discord webhook and Gemini API key in plaintext, so do not share it.
</details>

Note
-----------------
Code by @xeft. If you have any question, feel free to DM me on Discord or open an issue.
