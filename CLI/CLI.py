import re
import time
import datetime
import requests
from bs4 import BeautifulSoup
from discord import SyncWebhook, Embed


class CustomError(Exception):
    def __init__(self, message):
        super().__init__(message)

WEBHOOK_URL = str(input('Enter Discord webhook url: '))
if 'https://discord.com/api/webhooks/' not in WEBHOOK_URL: raise CustomError('A valid webhook url should contain "https://discord.com/api/webhooks/".')
if len(WEBHOOK_URL) != 121: raise CustomError('A valid webhook url should be 121 character long.')

TG_ANNOUNCEMENT_CHANNEL = str(input('Enter Telegram public announcement channel link: '))
if 'https://t.me/' not in TG_ANNOUNCEMENT_CHANNEL: raise CustomError('A valid channel link should contain "https://t.me/".')
else: TG_ANNOUNCEMENT_CHANNEL = TG_ANNOUNCEMENT_CHANNEL[13:]

EMBED_COLOR = input('Enter embed color (hex): ')
if '0x' not in EMBED_COLOR: raise CustomError('A valid embed color should contain "0x".') 
else: EMBED_COLOR = int(EMBED_COLOR, 16)

EMBED_HYPERLINK_SETTING = int(input('Title hyperlink off/on, enter 1 or 2: '))
if EMBED_HYPERLINK_SETTING != 1 and EMBED_HYPERLINK_SETTING != 2: raise CustomError('A valid title hyperlink setting should be 1 or 2.')

KEYWORD_FILTER_OPTION = str(input("Only forward message contains / not cointains certain keyword, enter 1 or 2 (leave blank if you want to forward all message): "))
KEYWORD_FILTER_BANK = []
if KEYWORD_FILTER_OPTION == '':
    pass
elif KEYWORD_FILTER_OPTION != '1' and KEYWORD_FILTER_OPTION != '2':
    raise CustomError('You should input 1 or 2 or leave it blank')
else:
    KEYWORD_FILTER_BANK = str(input('Enter your keyword, separate by comma if you have multiple keyword (e.g. ant, bear, cat): ')).split(',')

CHECK_MESSAGE_EVERY_N_SEC = int(input('How many seconds you want the script to check new message (recommend 20, if you set it to 0.05 your IP may temporarily banned by Telegram): '))

SCRIPT_START_TIME = datetime.datetime.now()

print('----------------------------------------------------------------')
print('Setup Complete! Your Config:')
print(f'WEBHOOK_URL👉 {WEBHOOK_URL}')
print(f'TG_ANNOUNCEMENT_CHANNEL👉 {TG_ANNOUNCEMENT_CHANNEL}')
print(f'EMBED_COLOR👉 {EMBED_COLOR}')
print(f'EMBED_HYPERLINK_SETTING👉 {EMBED_HYPERLINK_SETTING}')
print(f'KEYWORD_FILTER_OPTION👉 {KEYWORD_FILTER_OPTION}')
print(f'CHECK_MESSAGE_EVERY_N_SEC👉 {CHECK_MESSAGE_EVERY_N_SEC}')
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
                    converted_text += f"[{child.text}]({child['href']})"

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
            
            print(f'c {converted_text}\n')
    
    return converted_text


def getImage(tg_box):
    msg_image = tg_box.find('a',{'class': 'tgme_widget_message_photo_wrap'},href=True) # get each img
    if msg_image != None:
        startIndex = msg_image['style'].find("background-image:url(\'") + 22 # parse image url
        endIndex = msg_image['style'].find(".jpg')") + 4
        msg_image = msg_image['style'][startIndex:endIndex]

    return msg_image


def keywordFilter(msg_text):
    if KEYWORD_FILTER_OPTION == '1': # only forward message contains certain keyword
        for KEYWORD in KEYWORD_FILTER_BANK:
            if KEYWORD in msg_text:
                return True
    if KEYWORD_FILTER_OPTION == '2': # only forward message not contains certain keyword
        contain_keyword = False
        for KEYWORD in KEYWORD_FILTER_BANK:
            if KEYWORD in msg_text:
                contain_keyword = True
        if contain_keyword == False:
            return True
        
    return False
    

def sendMessage(msg_link, msg_text, msg_image):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    if keywordFilter(msg_text) == True: return

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
        print('----------------------------------------------------------------')
        print(f'New message found!\nLink: {msg_link}\nForward message to Discord')
        webhook.send(embed=embed)
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
