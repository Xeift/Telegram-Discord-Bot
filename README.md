# Telegram-Discord-Bot
A bot that forwards Telegram messages to Discord via webhook. It does not require any Discord or Telegram permissions, nor does it require adding any bots to Telegram group, the only thing required is the Discord webhook url.

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
## For Windows User
1. Go to the [release page](https://github.com/Xeift/Telegram-Discord-Bot/releases) and download CLI.exe.

2. Double click to run CLI.exe. Below are the explanation of the params:

|       Name                           | Description | Required | Example |
|--------------------------------------|-------------|----------|---------|
| DC_WEBHOOK_URL                       | The Discord webhook you got in Discord channel                                                                   |    ✔    | https://discord.com/api/webhooks/1322806255961509930/Bhz0Q2mv6rz9gXclYAFSl7tvbqdhhbEr3no6WY6o-fWwa6rp5Mg8t_EbtvIjnuR6lb3u |
| TG_ANNOUNCEMENT_CHANNEL              | The link of the public Telegram announcement channel. Public group, private group, private channel will not work |    ✔    | https://t.me/dsafdsfa3243 |
| EMBED_COLOR                          | The color of the forwarded Discord embed message                                                                 |    ✔    | 0xe8006f |
| EMBED_TITLE_SETTING                  | The title style of the forwarded Discord embed message                                                           |    ❌   | 1 |
| KEYWORD_FILTER_OPTION                | Useful when you want to filter some message with/without specific keywords                                       |    ✔    | 2 |
| KEYWORD_FILTER_BANK                  | The words you want to filter                                                                                     |    (✔)  | ant,bear,cat |
| CHECK_MESSAGE_EVERY_N_SEC            | How many seconds you want the script to check new message                                                        |    ✔    | 20 |
| CONTENT_TEXT                         | Add custom content text above the embed                                                                          |    ❌   | This message is forward from Telegram =w= |
| FORWARD_IMAGE                        | Forward/don't message with image                                                                                 |    ❌   | 1 |
| ONLY_PLAINTEXT                       | Remove any other multimedia, only forward plaintext                                                              |    ❌   | 1 |

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
