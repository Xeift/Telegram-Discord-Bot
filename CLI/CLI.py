import re
import time
import requests
from bs4 import BeautifulSoup
from discord import SyncWebhook, Embed

class CustomError(Exception):
    def __init__(self, message):
        super().__init__(message)

WEBHOOK_URL = str(input('enter webhook url: '))
if 'https://discord.com/api/webhooks/' not in WEBHOOK_URL: raise CustomError('A valid webhook url should contain "https://discord.com/api/webhooks/".')
if len(WEBHOOK_URL) != 121: raise CustomError('A valid webhook url should be 121 character long.')

TG_ANNOUNCEMENT_CHANNEL = str(input('enter announcement channel link: '))
if 'https://t.me/' not in TG_ANNOUNCEMENT_CHANNEL: raise CustomError('A valid channel link should contain "https://t.me/".')
else: TG_ANNOUNCEMENT_CHANNEL = TG_ANNOUNCEMENT_CHANNEL[13:]

EMBED_COLOR = input('enter embed color (hex): ')
if '0x' not in EMBED_COLOR: raise CustomError('A valid embed color should contain "0x".') 
else: EMBED_COLOR = int(EMBED_COLOR, 16)

EMBED_HYPERLINK_SETTING = int(input('title hyperlink off/on, enter 1 or 2: '))
if EMBED_HYPERLINK_SETTING != 1 and EMBED_HYPERLINK_SETTING != 2: raise CustomError('A valid title hyperlink setting should be 1 or 2.')


print('setup complete!')


'''                                  F U N C T I O N S                                    '''
def scrapeTelegramMessageBox():
    tg_html = requests.get(f'https://t.me/s/{TG_ANNOUNCEMENT_CHANNEL}') # telegram public channel preview page
    tg_soup = BeautifulSoup(tg_html.text, 'html.parser') # bs4
    tg_box = tg_soup.find_all('div',{'class': 'tgme_widget_message_wrap js-widget_message_wrap'}) # get each message
    return tg_box


def getLink(tg_box):
    msg_link = tg_box.find_all('a', {'class':'tgme_widget_message_date'}, href=True)[0]['href'] # get msg link

    return msg_link


def getText(tg_box):
    msg_text = tg_box.find_all('div',{'class': 'tgme_widget_message_text js-message_text'}) # get each text
    if msg_text == []:
        msg_text = None
    else:
        msg_text = re.sub( # deal with linebreak
            '<br/>',
            '\n',
            str(msg_text[0])
        )
        msg_text = BeautifulSoup(msg_text, 'html.parser').get_text()
    
    return msg_text


def getImage(tg_box):
    msg_image = tg_box.find('a',{'class': 'tgme_widget_message_photo_wrap'},href=True)# get each img
    if msg_image != None:
        startIndex = msg_image['style'].find("background-image:url(\'") + 22 # parse image url
        endIndex = msg_image['style'].find(".jpg')") + 4
        msg_image = msg_image['style'][startIndex:endIndex]

    return msg_image


def sendMessage(msg_link, msg_text, msg_image):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)

    if msg_text != None and msg_image != None:
        if EMBED_HYPERLINK_SETTING == 1:
            embed = Embed(title='Forward From Telegram', description=msg_text, color=EMBED_COLOR)
        elif EMBED_HYPERLINK_SETTING == 2:
            embed = Embed(title='Original Telegram Link', description=msg_text, url=msg_link, color=EMBED_COLOR)
        embed.set_image(url=msg_image)

    elif msg_text == None and msg_image != None:
        if EMBED_HYPERLINK_SETTING == 1:
            embed = Embed(title='Forward From Telegram', color=EMBED_COLOR)
        elif EMBED_HYPERLINK_SETTING == 2:
            embed = Embed(title='Original Telegram Link', url=msg_link, color=EMBED_COLOR)
        embed.set_image(url=msg_image)

    elif msg_text != None and msg_image == None:
        if EMBED_HYPERLINK_SETTING == 1:
            embed = Embed(title='Forward From Telegram', description=msg_text, color=EMBED_COLOR)
        elif EMBED_HYPERLINK_SETTING == 2:
            embed = Embed(title='Original Telegram Link', description=msg_text, url=msg_link, color=EMBED_COLOR)

    else:
        return

    if msg_log != []:
        print(f'send {msg_link}')
        webhook.send(embed=embed)
'''                                  F U N C T I O N S                                    '''


msg_log = []
while 1:
    try:
        msg_temp = []

        for tg_box in scrapeTelegramMessageBox():
            msg_link = getLink(tg_box)
            msg_text = getText(tg_box)
            msg_image = getImage(tg_box)

            if msg_link not in msg_log:
                msg_temp.append(msg_link)
                sendMessage(msg_link, msg_text, msg_image)

            msg_temp.append(msg_link)

        msg_log = msg_temp
        print('bot working')
        time.sleep(20)
    except Exception as e:
        print(f'[   E R R O R   ]\n{e}\nScript ignored the error and keep running.')
        time.sleep(20)
