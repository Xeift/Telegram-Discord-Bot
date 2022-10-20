# Kizmeow-Telegram-Discord-Bot
A bot that forwards Telegram messages to Discord via webhook. Kizmeow does not require any Discord or Telegram permissions, nor does it require adding any bots to Telegram group, the only thing required is the Discord webhook url.

The bot is under development, it only forward text messages currently. 

What's the difference between Kizmeow and other existing bots?
-----------------

|                                                                   | Kizmeow | Other Bots |
|-------------------------------------------------------------------|:-------:|:----------:|
|Not required to add Discord Bot to your server                     |   ✔    |     ❌     |
|Not required to add Telegram Bot to your server                    |   ✔    |     ❌     |
|Discord webhook not required                                       |   ❌   |    ✔❌    |
|Forward message from public Telegram channel which you don't own it|   ✔    |     ❌     |
|Forward message from private Telegram channel                      |   ❌   |     ✔     |
|GUI and CLI supported                                              |   ✔    |    ✔❌    |


Usage
-----------------

Click [here](https://github.com/Xeift/Kizmeow-Telegram-Discord-Bot/archive/refs/heads/main.zip) to download zip first.

If you don't want to download any file on your precious computer, you can run CLI on cloud first.

[Click me](https://replit.com/@xeiftc/Kizmeow-Telegram-Discord-Bot#main.py) to run CLI on Replit.

There are two interface, GUI and CLI.

You can choose one you desire. If you're not familiar with Python, I suggest you use GUI.

The window on the left side is CLI, the right one is GUI.

![image](https://user-images.githubusercontent.com/80938768/196021293-f8741207-a46c-4902-b4aa-b3f03fe467e5.png)

Whether you choose GUI or CLI, we need to obtain below data first:

|                 | example |
|-----------------|---------|
| DC Webhook URL  | https://discord.com/api/webhooks/953518959309783100/nv0byOn-xwMmRfHV6lasGbkhmNX0DvQyUAMJcoRbZJeHrpIpVKdB9bjJk962BddJRq8C |
| TG Channel Slug | ~~https://t.me/~~ binance_cn |
| Embed Color     | 0xe8006f |

#### *DC Webhook URL*

Right click on the Discord server you want to forward message to.

Select `Server Settings` → `Intergrations`

![image](https://user-images.githubusercontent.com/80938768/196020310-9080efb6-cf40-4480-9286-9423b8d02482.png)

Click `New Webhhok` to create a new webhook.

Click `Copy Webhook URL` and paste the URL on notepad, Google Docs or any text editor, we will need it later.

![image](https://user-images.githubusercontent.com/80938768/196020693-faa13f8c-7c24-46dc-936f-e0dadb8b046a.png)

#### *TG Channel Slug*

Click the title of the announcement channel, copy the slug after `https://t.me/`.

![image](https://user-images.githubusercontent.com/80938768/196020250-03ab9c6c-38b8-420c-98ff-7f34fd58cd58.png)

#### *Embed Color*

Google "color picker" and choose the color you like, copy its HEX value and change "#" to "0x".

![image](https://user-images.githubusercontent.com/80938768/196021711-9626ec37-e4da-4dd9-9485-7d6dfefe2ef9.png)

Finally, we got all data we need.

#### *GUI*

1. Open `GUI` folder
2. Run GUI.exe
3. Enter data, click start bot

Video Tutorial: https://www.youtube.com/watch?v=YuWAM28t8nc

#### *CLI*

1. Open `CLI` folder
2. Install python and packages in requirements.txt
3. Run CLI
4. Enter data, it will start automatically

Note
-----------------

TTK theme I use for GUI: [Azure theme for ttk](https://github.com/rdbende/Azure-ttk-theme)

A nice tool I use for convert .py to .exe : [Auto PY to EXE](https://github.com/brentvollebregt/auto-py-to-exe)

Code by Xeift#1230

Kizmeow icon illustrate by [Kiyue](https://instagram.com/sweetdays_gun_gun?igshid=YmMyMTA2M2Y=)
![image](https://user-images.githubusercontent.com/80938768/196019602-f4ac2896-cdaa-4028-acdb-53b8a0a60d43.png)
