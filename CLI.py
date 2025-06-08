import datetime
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from discord import Embed, SyncWebhook
from dotenv import load_dotenv

load_dotenv()


class CustomError(Exception):
    def __init__(self, message):
        super().__init__(message)


try:
    DC_WEBHOOK_URL = os.getenv('DC_WEBHOOK_URL') or str(input('[DC_WEBHOOK_URL] Enter Discord webhook url: '))
    if 'https://discord.com/api/webhooks/' not in DC_WEBHOOK_URL: raise CustomError('[DC_WEBHOOK_URL] A valid webhook url should contain "https://discord.com/api/webhooks/".')
    if len(DC_WEBHOOK_URL) != 121: raise CustomError('[DC_WEBHOOK_URL] A valid webhook url should be 121 character long.')

    TG_ANNOUNCEMENT_CHANNEL = os.getenv('TG_ANNOUNCEMENT_CHANNEL') or str(input('[TG_ANNOUNCEMENT_CHANNEL] Enter Telegram public announcement channel link: '))
    if 'https://t.me/' not in TG_ANNOUNCEMENT_CHANNEL: raise CustomError('[TG_ANNOUNCEMENT_CHANNEL] A valid channel link should contain "https://t.me/".')
    else: TG_ANNOUNCEMENT_CHANNEL = TG_ANNOUNCEMENT_CHANNEL[13:]

    EMBED_COLOR = os.getenv('EMBED_COLOR') or input('[EMBED_COLOR] Enter embed color (hex): ')
    if '0x' not in EMBED_COLOR: raise CustomError('[EMBED_COLOR] A valid embed color should contain "0x".') 
    else: EMBED_COLOR = int(EMBED_COLOR, 16)

    EMBED_TITLE_SETTING = os.getenv('EMBED_TITLE_SETTING') or str(input('[EMBED_TITLE_SETTING] Embed title setting. No title(1), title hyperlink off(2), title hyperlink on(3), enter 1, 2 or 3: '))
    if EMBED_TITLE_SETTING != '1' and EMBED_TITLE_SETTING != '2' and EMBED_TITLE_SETTING != '3': raise CustomError('[EMBED_TITLE_SETTING] A valid title hyperlink setting should be 1, 2 or 3.')

    KEYWORD_FILTER_OPTION = os.getenv('KEYWORD_FILTER_OPTION') if os.getenv('KEYWORD_FILTER_OPTION') is not None else str(input("[KEYWORD_FILTER_OPTION] Only forward message contains(1) / not cointains(2) certain keyword, enter 1 or 2 (leave blank if you want to forward all message): "))
    KEYWORD_FILTER_BANK = []
    if KEYWORD_FILTER_OPTION == '':
        pass
    elif KEYWORD_FILTER_OPTION != '1' and KEYWORD_FILTER_OPTION != '2':
        raise CustomError('[KEYWORD_FILTER_OPTION] You should input 1 or 2 or leave it blank')
    else:
        KEYWORD_FILTER_BANK = str(input('[KEYWORD_FILTER_BANK] Enter your keywords, separate by comma if you have multiple keywords (e.g. ant,bear,cat): ')).split(',')
        KEYWORD_FILTER_BANK = [s.strip() for s in KEYWORD_FILTER_BANK]

    FORWARD_IMAGE = os.getenv('FORWARD_IMAGE') or str(input("[FORWARD_IMAGE] Forward message with image(1), don't forward message image(2), enter 1 or 2: "))
    if FORWARD_IMAGE != '1' and FORWARD_IMAGE != '2': raise CustomError('[FORWARD_IMAGE] You should input 1 or 2.')

    ONLY_PLAINTEXT = os.getenv('ONLY_PLAINTEXT') if os.getenv('ONLY_PLAINTEXT') is not None else str(input("[ONLY_PLAINTEXT] Remove any other multimedia, only forward plaintext, enter 1 if want only plaintext (leave blank if you want to forward normal multimedia): "))
    if ONLY_PLAINTEXT != '1' and ONLY_PLAINTEXT != '': raise CustomError('[ONLY_PLAINTEXT] You should input 1 or leave it blank.')

    CHECK_MESSAGE_EVERY_N_SEC = int(os.getenv('CHECK_MESSAGE_EVERY_N_SEC')) or int(input('[CHECK_MESSAGE_EVERY_N_SEC] How many seconds you want the script to check new message (recommend 20, if you set it to 0.05 your IP may temporarily banned by Telegram): '))

    CONTENT_TEXT = os.getenv('CONTENT_TEXT') if os.getenv('CONTENT_TEXT') is not None else str(input('[CONTENT_TEXT] Add content text above the embed (leave blank if you don\'t want to add additional text): '))

    SCRIPT_START_TIME = datetime.datetime.now()

except CustomError as e:
    print('----------------------------------------------------------------')
    print(f'[   E R R O R   ]\n{e}')
    print('Press Enter key to exit. Consider restart CLI.exe')
    print('If you need any help, feel free to send a DM to:\nDiscord @xeift\nTelegram @Xeift')
    print('----------------------------------------------------------------')
    input()


print('----------------------------------------------------------------')
if os.getenv('DC_WEBHOOK_URL') is not None: print('Use the .env file as primary config source.')
print('Setup Complete! Your Config:')
print(f'DC_WEBHOOK_URL: {DC_WEBHOOK_URL}')
print(f'TG_ANNOUNCEMENT_CHANNEL: {TG_ANNOUNCEMENT_CHANNEL}')
print(f'EMBED_COLOR: {EMBED_COLOR}')
print(f'EMBED_HYPERLINK_SETTING: {EMBED_TITLE_SETTING}')
print(f'KEYWORD_FILTER_OPTION: {KEYWORD_FILTER_OPTION}')
print(f'KEYWORD_FILTER_BANK: {KEYWORD_FILTER_BANK}')
print(f'CHECK_MESSAGE_EVERY_N_SEC: {CHECK_MESSAGE_EVERY_N_SEC}')
print(f'CONTENT_TEXT: {CONTENT_TEXT}')
print('----------------------------------------------------------------')


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
    converted_text = ''
    if msg_text == []:
        converted_text = None
    else:
        msg_text = msg_text[0]
        for child in msg_text.children:
            if child.name is None: # plain text -> without change
                converted_text += child

            elif child.name == 'a':
                if child.text == child['href']: # normal link -> without change
                    converted_text += child['href']
                else: # tg markdown link -> dc markdown link
                    href = re.sub( # deal with extra 'amp;' in href
                        'amp;',
                        '',
                        child['href']
                    )
                    converted_text += f"[{child.text}]({href})"

            elif child.name == 'code':
                converted_text += f"`{child.text}`" # tg markdown monotext -> dc markdown codeblock

            elif child.name == 'b':
                converted_text += f"**{child.text}**" # tg markdown bold -> dc markdown bold

            elif child.name == 'tg-spoiler':
                converted_text += f"||{child.text}||" # tg markdown unseen -> dc markdown spoiler

            elif child.name == 'i':
                converted_text += f"*{child.text}*" # tg markdown italic -> dc markdown italic

            elif child.name == 'u':
                converted_text += f"__{child.text}__" # tg markdown underline -> dc markdown underline
                
            elif child.name == 's':
                converted_text += f"~~{child.text}~~" # tg markdown strikethrough -> dc markdown strikethrough

            elif child.name == 'br': # tg linebreak -> dc linebreak
                converted_text += '\n'
            
    return converted_text


def getImage(tg_box):
    msg_image = tg_box.find('a',{'class': 'tgme_widget_message_photo_wrap'},href=True) # get each img
    if msg_image != None:
        startIndex = msg_image['style'].find("background-image:url(\'") + 22 # parse image url
        endIndex = msg_image['style'].find(".jpg')") + 4
        msg_image = msg_image['style'][startIndex:endIndex]

    return msg_image


def keywordFilter(msg_text):
    if msg_text == None or msg_text == '': return False

    if KEYWORD_FILTER_OPTION == '': # no filter, forward all message
        return False
    
    if KEYWORD_FILTER_OPTION == '1': # only forward message contains certain keyword
        for KEYWORD in KEYWORD_FILTER_BANK:
            if KEYWORD in msg_text:
                return False
        return True
    if KEYWORD_FILTER_OPTION == '2': # only forward message not contains certain keyword
        contain_keyword = False
        for KEYWORD in KEYWORD_FILTER_BANK:
            if KEYWORD in msg_text:
                contain_keyword = True
        return contain_keyword

    return True
    

def sendMessage(msg_link, msg_text, msg_image):
    webhook = SyncWebhook.from_url(DC_WEBHOOK_URL)
    skip_this_msg = keywordFilter(msg_text)
    if skip_this_msg == True: return
    if msg_image != None and FORWARD_IMAGE == '2': return

    embed = Embed(title='', color=EMBED_COLOR)

    if msg_text != None: embed.description = msg_text
    if msg_image != None and ONLY_PLAINTEXT != '1': embed.set_image(url=msg_image)
    if EMBED_TITLE_SETTING == '2': embed.title = 'Forward From Telegram'
    if EMBED_TITLE_SETTING == '3': embed.title = 'Original Telegram Link'; embed.url = msg_link

    if msg_log != []:
        print('----------------------------------------------------------------')
        print(f'New message found!\nLink: {msg_link}\nForward message to Discord')
        if (CONTENT_TEXT == False): webhook.send(embed=embed)
        else: webhook.send(content=CONTENT_TEXT, embed=embed)
        print('----------------------------------------------------------------')

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
        
        current_time = datetime.datetime.now()
        time_passed = current_time - SCRIPT_START_TIME
        print(f'bot working. time passed: {time_passed}')
    except Exception as e:
        print(f'[   E R R O R   ]\n{e}\nScript ignored the error and keep running.')
    
    time.sleep(CHECK_MESSAGE_EVERY_N_SEC)
