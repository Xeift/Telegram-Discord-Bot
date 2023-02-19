import requests
from bs4 import BeautifulSoup
import json
import re
import time
from discord import Webhook, SyncWebhook, Embed

_webhookURL = str(input('enter webhook url: '))
_tgAnnouncementChannel = str(input('enter announcement channel slug: '))
_embedColor = int(str(input('enter embed color (hex): ')), 16)
_embedHyperlinkSetting = int(input('title hyperlink off/on, enter 1 or 2: '))

# I N P U T    E X A M P L E
# _webhookURL = 'https://discord.com/api/webhooks/1068038947608997939/erTyDBPBGmVHME4FsduQ-CURNcd10-cjQQMC6FQq0baP3TmHqrctM409SS4sTNzC1Be-'
# _tgAnnouncementChannel = 'dsafdsfa3243'
# _embedColor = int(('0xe8006f'), 16)
# _embedHyperlinkSetting = 2

print('setup complete!')


'''                                  F U N C T I O N S                                    '''
def scrapeTelegramMessageBox():
    tg_html = requests.get(f'https://t.me/s/{_tgAnnouncementChannel}') # telegram public channel preview page
    tg_soup = BeautifulSoup(tg_html.text, 'html.parser')# bs4
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
    webhook = SyncWebhook.from_url(_webhookURL)

    if msg_text != None and msg_image != None:
        if _embedHyperlinkSetting == 1:
            embed = Embed(title='Forward From Telegram', description=msg_text, color=_embedColor)
        elif _embedHyperlinkSetting == 2:
            embed = Embed(title='Original Telegram Link', description=msg_text, url=msg_link, color=_embedColor)
        embed.set_image(url=msg_image)

    elif msg_text == None and msg_image != None:
        if _embedHyperlinkSetting == 1:
            embed = Embed(title='Forward From Telegram', color=_embedColor)
        elif _embedHyperlinkSetting == 2:
            embed = Embed(title='Original Telegram Link', url=msg_link, color=_embedColor)
        embed.set_image(url=msg_image)

    elif msg_text != None and msg_image == None:
        if _embedHyperlinkSetting == 1:
            embed = Embed(title='Forward From Telegram', description=msg_text, color=_embedColor)
        elif _embedHyperlinkSetting == 2:
            embed = Embed(title='Original Telegram Link', description=msg_text, url=msg_link, color=_embedColor)

    else:
        return

    if msg_log != []:
        print(f'send {msg_link}')
        webhook.send(embed=embed)
'''                                  F U N C T I O N S                                    '''


msg_log = []
while 1:
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
    time.sleep(20)
    print('bot working')