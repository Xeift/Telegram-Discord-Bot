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

3. Review the configuration form and press `Start`. Values from `.env` are loaded into the form automatically. Press `Stop` to stop forwarding, or press `q` to quit the TUI.

For Docker, run the container with an interactive terminal:

```bash
docker build -t telegram-discord-bot .
docker run --rm -it --env-file .env telegram-discord-bot
```

Below are the configuration fields:

| Name | Description | Required | Example |
|------|-------------|----------|---------|
| DC_WEBHOOK_URL | The Discord webhook you got in Discord channel | Yes | https://discord.com/api/webhooks/1322806255961509930/Bhz0Q2mv6rz9gXclYAFSl7tvbqdhhbEr3no6WY6o-fWwa6rp5Mg8t_EbtvIjnuR6lb3u |
| TG_ANNOUNCEMENT_CHANNEL | The link of the public Telegram announcement channel. Public group, private group, private channel will not work | Yes | https://t.me/dsafdsfa3243 |
| EMBED_COLOR | The color of the forwarded Discord embed message | Yes | 0xe8006f |
| EMBED_TITLE_SETTING | The title style of the forwarded Discord embed message: 1 no title, 2 plain title, 3 title link | Yes | 3 |
| KEYWORD_FILTER_OPTION | Blank forwards all messages, 1 forwards messages containing keywords, 2 forwards messages not containing keywords | No | 2 |
| KEYWORD_FILTER_BANK | The words you want to filter, separated by comma. Required when KEYWORD_FILTER_OPTION is 1 or 2 | No | ant,bear,cat |
| FORWARD_IMAGE | Forward messages with image: 1 yes, 2 no | Yes | 1 |
| ONLY_PLAINTEXT | Remove multimedia and only forward plaintext: 1 yes, blank no | No | 1 |
| GEMINI_API_KEY | Google Gemini API key. Leave blank to disable translation | No | AIza... |
| MODEL | Gemini model. Required when GEMINI_API_KEY is set | No | gemini-2.5-flash-lite |
| TRANSLATION_PROMPT | Translation prompt. Required when GEMINI_API_KEY is set | No | Please translate it naturally into English (en-US) |
| CHECK_MESSAGE_EVERY_N_SEC | How many seconds the bot waits between checks | Yes | 20 |
| CONTENT_TEXT | Add custom content text above the embed | No | This message is forward from Telegram =w= |

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
<summary>I don't want to enter the cofig evertime I start the script. Does it support .env?</summary>
Yes. You can create a .env file and put the cofig in it. See [.env.example](https://github.com/Xeift/Telegram-Discord-Bot/blob/main/.env.example) for actual format and fields. 
</details>

Note
-----------------
Code by @xeft. If you have any question, feel free to DM me on Discord or open an issue.
