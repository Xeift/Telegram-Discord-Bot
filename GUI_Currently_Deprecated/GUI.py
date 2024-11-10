"""
ttk theme source: https://github.com/rdbende/ttk-widget-factory
"""
import sys
import os
import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from discord import Webhook, SyncWebhook, Embed

class App(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self)

        self.embedHyperlinkSetting = tk.IntVar(value=2)
        self.setup_widgets()
        self.isStarted = ''
        self.announcementLog = []

    def setup_widgets(self):
        def onButtonClick():
            if self.isStarted == '':
                self.togglebutton.configure(text='Stop Bot')
                self.isStarted = True

            elif self.isStarted == True:
                self.togglebutton.configure(text='Start Bot')
                self.isStarted = False
                return
            elif self.isStarted == False:
                self.togglebutton.configure(text='Stop Bot')
                self.isStarted = True
            root.after(1, checkState)

        def checkState():
            if self.isStarted:
                _webhookURL = self.entry1.get()
                _tgAnnouncementChannel = self.entry2.get()
                _embedColor = int(str( self.entry3.get() ), 16)

            try:
                announcementTemp = []
                
                announcementHtml = requests.get(f'https://t.me/s/{_tgAnnouncementChannel}')# tg public channel preview page
                announcementSoup = BeautifulSoup(announcementHtml.text, 'html.parser')# bs4
                announcementBox = announcementSoup.find_all('div',{'class': 'tgme_widget_message_wrap js-widget_message_wrap'})# get each msg
                
                for a in announcementBox:
                    announcementLink = a.find_all('a',{'class':'tgme_widget_message_date'},href=True)[0]# get msg link
                    announcementLink = announcementLink['href']
                    
                    announcementText = a.find_all('div',{'class': 'tgme_widget_message_text js-message_text'})# get each msg
                    announcementText = re.sub(# deal with linebreak
                        '<br/>',
                        '\n',
                        str(announcementText[0])
                    )

                    announcementText = BeautifulSoup(announcementText, 'html.parser').get_text()# convert to bs4 object

                    if announcementLink not in self.announcementLog:
                        announcementTemp.append(announcementLink)
                        webhook = SyncWebhook.from_url(_webhookURL)
                        if self.embedHyperlinkSetting.get() == 1:
                            embed = Embed(title='Forward From Telegram', description=announcementText, color=_embedColor)
                        elif self.embedHyperlinkSetting.get() == 2:
                            embed = Embed(title='Original Telegram Link', description=announcementText, url=f'{announcementLink}', color=_embedColor)
                        if self.announcementLog != []:
                            webhook.send(embed=embed)

                    announcementTemp.append(announcementLink)

                self.announcementLog = announcementTemp
                print('bot working')
                root.after(20000, checkState)

            except:
                pass

        self.radio_frame = ttk.LabelFrame(self, text='Title Hyperlink', padding=(20, 10))
        self.radio_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky='nsew')

        self.radio_1 = ttk.Radiobutton(
            self.radio_frame, text='Hide', variable=self.embedHyperlinkSetting, value=1
        )
        self.radio_1.grid(row=2, column=0, padx=5, pady=10, sticky='nsew')

        self.radio_2 = ttk.Radiobutton(
            self.radio_frame, text='Show', variable=self.embedHyperlinkSetting, value=2
        )
        self.radio_2.grid(row=3, column=0, padx=5, pady=10, sticky='nsew')

        self.widgets_frame = ttk.Frame(self, padding=(0, 0, 0, 10))
        self.widgets_frame.grid(
            row=0, column=1, padx=10, pady=(30, 10), sticky='nsew', rowspan=3
        )
        self.widgets_frame.columnconfigure(index=0, weight=1)

        self.entry1 = ttk.Entry(self.widgets_frame)
        self.entry1.insert(0, 'DC Webhook URL')
        self.entry1.grid(row=0, column=0, padx=5, pady=(0, 10), sticky='ew')

        self.widgets_frame.columnconfigure(index=0, weight=1)
        self.entry2 = ttk.Entry(self.widgets_frame)
        self.entry2.insert(0, 'TG Channel Slug')
        self.entry2.grid(row=1, column=0, padx=5, pady=(0, 10), sticky='ew')

        self.widgets_frame.columnconfigure(index=0, weight=1)
        self.entry3 = ttk.Entry(self.widgets_frame)
        self.entry3.insert(0, 'Embed Color')
        self.entry3.grid(row=2, column=0, padx=5, pady=(0, 10), sticky='ew')

        self.togglebutton = ttk.Checkbutton(
            self.widgets_frame, text='Start Bot', style='Toggle.TButton', command=onButtonClick
        )
        self.togglebutton.grid(row=3, column=0, padx=5, pady=10, sticky='nsew')

if __name__ == '__main__':
    def resource_path(relative_path):
        """ Get the absolute path to the resource, works for dev and for PyInstaller """

        base_path = os.path.dirname(os.path.realpath(__file__))
        print(os.listdir(base_path))

        return os.path.join(base_path, relative_path)
        
    root = tk.Tk()
    root.title('Kizmeow Telegram Discord Bot')
    root.resizable(width=False, height=False)

    root.tk.call('source', resource_path('azure.tcl'))
    root.tk.call('set_theme', 'dark')
    root.iconbitmap(resource_path('kizmeow.ico'))

    app = App(root)
    app.pack(fill='both', expand=True)

    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())
    x_cordinate = int((root.winfo_screenwidth() / 2) - (root.winfo_width() / 2))
    y_cordinate = int((root.winfo_screenheight() / 2) - (root.winfo_height() / 2))
    root.geometry('+{}+{}'.format(x_cordinate, y_cordinate-20))

    root.mainloop()