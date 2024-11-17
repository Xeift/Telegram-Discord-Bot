# Kizmeow-Telegram-Discord-Bot
A bot that forwards Telegram messages to Discord via webhook. Kizmeow does not require any Discord or Telegram permissions, nor does it require adding any bots to Telegram group, the only thing required is the Discord webhook url.

The bot is under development, it only forward text messages and images currently. 

What's the difference between Kizmeow and other existing bots?
-----------------

|                                                                   | Kizmeow | Other Bots |
|-------------------------------------------------------------------|:-------:|:----------:|
|Not required to add Discord Bot to your Discord server             |   ✔    |     ❌     |
|Not required to add Telegram Bot to your Telegram group            |   ✔    |     ❌     |
|Discord webhook not required                                       |   ❌   |    ✔❌    |
|Forward message from public Telegram channel which you don't own it|   ✔    |     ❌     |
|Forward message from private Telegram channel                      |   ❌   |     ✔      |
|Forward message from private or public Telegram group              |   ❌   |     ✔❌   |
|Discord embed supported                                            |   ✔    |    ✔❌    |
|Keyword filter                                                     |   ✔    |    ✔❌    |

Usage
-----------------

1. Click [here](https://github.com/Xeift/Kizmeow-Telegram-Discord-Bot/archive/refs/heads/main.zip) to download zip first.

2. Unzip the file and run CLI.exe. If you are familiar with python, you can run CLI.py too.

3. Before we run CLI.py, we need to obtain below data first:

|       Name                           | Description | Required | Example |
|--------------------------------------|-------------|----------|---------|
| Discord webhook URL                  |The Discord webhook you got in Discord channel|    ✔    | https://discord.com/api/webhooks/953518959309783100/nv0byOn-![image](https://github.com/user-attachments/assets/70694575-c8e8-44c8-a37c-641803b80a49xwMmRfHV6lasGbkhmNX0DvQyUAMJcoRbZJeHrpIpVKdB9bjJk962BddJRq8C) |
| Telegram public announcement channel |The link of the public Telegram announcement channel. Public group, private group, private channel will not work|    ✔    | https://t.me/dsafdsfa3243 |
| Embed color                          |        |    ✔    | 0xe8006f |
| Embed hyperlink setting              |        |    ❌   | 1 |
| Keyword filter option                |        |    ✔    | 1 |
| Keyword filter bank                  |        |    (✔)  | hello |
| Check message every n sec            |        |    ✔    | 20 |
| Content text                         |        |    ❌   | This message is forward from Telegram |

The gif table below shows the steps to get these parameters.

|               Parameter Name               |                                 How to get the parameter?                                 |
|--------------------------------------------|-------------------------------------------------------------------------------------------|
|             Discord webhook URL            | ![image](https://github.com/user-attachments/assets/9798b6ea-9be7-40b5-8169-87e3445d1c8d) |
|    Telegram public announcement channel    | ![image](https://github.com/user-attachments/assets/98f40aad-471c-42bf-b2c6-038fcc639e77) |
|                Embed color                 | ![image](https://github.com/user-attachments/assets/d072d6d9-22e1-412d-8278-7a6676e7feb0) |


Note
-----------------

TTK theme I use for GUI: [Azure theme for ttk](https://github.com/rdbende/Azure-ttk-theme)

A nice tool I use for convert .py to .exe : [Auto PY to EXE](https://github.com/brentvollebregt/auto-py-to-exe)

Code by @xeft. If you have any question, feel free to DM me on Discord or open an issue.

Kizmeow icon illustrate by [Kiyue](https://instagram.com/sweetdays_gun_gun?igshid=YmMyMTA2M2Y=)
![image](https://user-images.githubusercontent.com/80938768/196019602-f4ac2896-cdaa-4028-acdb-53b8a0a60d43.png)

It's recommand to use CLI since I have no time to update GUI, functions of GUI are not up to date. 😶

FAQ
-----------------

<details>
<summary>Do I need to keep my computer on if I want to make this script running 7/24?</summary>
Yes.
</details>
