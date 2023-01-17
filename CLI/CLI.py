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

# I N P U T    E X A M P L E
# _webhookURL = 'https://discord.com/api/webhooks/1064748597985423440/Iiyb5EeosAY7K1ZrPwIhdNWIeHNntPv6LBhcOtZ8RVIUTcNX3ujjvS95YydHVK3D4psH'
# _tgAnnouncementChannel = 'dsafdsfa3243'
# _embedColor = int(('0xe8006f'), 16)
# _embedHyperlinkSetting = 2
# announcementLog = []

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
            announcementText = a.find_all('div',{'class': 'tgme_widget_message_text js-message_text'})# get each text

            announcementImg = a.find('a',{'class': 'tgme_widget_message_photo_wrap'},href=True)# get each img
            if announcementImg != None:
                startIndex = announcementImg['style'].find("background-image:url(\'") + 22
                endIndex = announcementImg['style'].find(".jpg')") + 4
                announcementImg = announcementImg['style'][startIndex:endIndex]
            else:
                announcementImg = None

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
                    
                    if announcementText == None:
                        if _embedHyperlinkSetting == 1:
                            embed = Embed(title='Forward From Telegram', color=_embedColor)
                        elif _embedHyperlinkSetting == 2:
                            embed = Embed(title='Original Telegram Link', url=f'{announcementLink}', color=_embedColor)
                    else:
                        if _embedHyperlinkSetting == 1:
                            embed = Embed(title='Forward From Telegram', description=announcementText, color=_embedColor)
                        elif _embedHyperlinkSetting == 2:
                            embed = Embed(title='Original Telegram Link', description=announcementText, url=f'{announcementLink}', color=_embedColor)
                    
                    if announcementImg != None:
                        embed.set_image(url=announcementImg)

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