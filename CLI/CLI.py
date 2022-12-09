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
announcementLog = []


print('setup complete!')

announcementLog = []
while 1:
    try:
        announcementTemp = []
        announcementHtml = requests.get(f'https://t.me/s/{_tgAnnouncementChannel}')# tg public channel preview page
        announcementSoup = BeautifulSoup(announcementHtml.text, 'html.parser')# bs4
        announcementBox = announcementSoup.find_all('div',{'class': 'tgme_widget_message_wrap js-widget_message_wrap'})# get each msg
        
        for a in announcementBox:
            announcementLink = a.find_all('a',{'class':'tgme_widget_message_date'},href=True)[0]# get msg link
            announcementLink = announcementLink['href']
            announcementText = a.find_all('div',{'class': 'tgme_widget_message_text js-message_text'})# get each msg
            try:
                announcementText = re.sub(# deal with linebreak
                    '<br/>',
                    '\n',
                    str(announcementText[0])
                )
                announcementText = BeautifulSoup(announcementText, 'html.parser').get_text()# convert to bs4 object

                if announcementLink not in announcementLog:
                    announcementTemp.append(announcementLink)
                    webhook = SyncWebhook.from_url(_webhookURL)
                    if _embedHyperlinkSetting == 1:
                        embed = Embed(title='Forward From Telegram', description=announcementText, color=_embedColor)
                    elif _embedHyperlinkSetting == 2:
                        embed = Embed(title='Original Telegram Link', description=announcementText, url=f'{announcementLink}', color=_embedColor)
                    if announcementLog != []:
                        print(f'send {announcementLink}')
                        webhook.send(embed=embed)
            except:
                pass

            announcementTemp.append(announcementLink)

        announcementLog = announcementTemp
        time.sleep(20)
        print('bot working')
    except:
        pass
