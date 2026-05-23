from __future__ import annotations

import datetime
import os
import re
import threading
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Callable

import requests
from bs4 import BeautifulSoup
from discord import Embed, SyncWebhook
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, RichLog, Static

load_dotenv()


class CustomError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class TranslationSchema(BaseModel):
    translated_content: str


@dataclass(frozen=True)
class FieldDefinition:
    key: str
    env_name: str
    label: str
    placeholder: str = ""
    password: bool = False


FIELDS = (
    FieldDefinition(
        "dc_webhook_url",
        "DC_WEBHOOK_URL",
        "Discord webhook",
        "https://discord.com/api/webhooks/...",
        True,
    ),
    FieldDefinition(
        "tg_announcement_channel",
        "TG_ANNOUNCEMENT_CHANNEL",
        "Telegram channel",
        "https://t.me/example_channel",
    ),
    FieldDefinition("embed_color", "EMBED_COLOR", "Embed color", "0xe8006f"),
    FieldDefinition(
        "embed_title_setting",
        "EMBED_TITLE_SETTING",
        "Title mode",
        "1 none, 2 title, 3 link",
    ),
    FieldDefinition(
        "keyword_filter_option",
        "KEYWORD_FILTER_OPTION",
        "Keyword mode",
        "blank all, 1 include, 2 exclude",
    ),
    FieldDefinition(
        "keyword_filter_bank",
        "KEYWORD_FILTER_BANK",
        "Keywords",
        "ant,bear,cat",
    ),
    FieldDefinition(
        "forward_image",
        "FORWARD_IMAGE",
        "Images",
        "1 forward, 2 skip",
    ),
    FieldDefinition(
        "only_plaintext",
        "ONLY_PLAINTEXT",
        "Plaintext only",
        "blank off, 1 on",
    ),
    FieldDefinition(
        "gemini_api_key",
        "GEMINI_API_KEY",
        "Gemini key",
        "",
        True,
    ),
    FieldDefinition("model", "MODEL", "Gemini model", "gemini-2.5-flash-lite"),
    FieldDefinition(
        "translation_prompt",
        "TRANSLATION_PROMPT",
        "Prompt",
        "Please translate it naturally into English (en-US)",
    ),
    FieldDefinition(
        "check_message_every_n_sec",
        "CHECK_MESSAGE_EVERY_N_SEC",
        "Poll interval",
        "20",
    ),
    FieldDefinition(
        "content_text",
        "CONTENT_TEXT",
        "Content prefix",
        "",
    ),
)

SECTION_BEFORE_FIELD = {
    "dc_webhook_url": "Connection",
    "embed_color": "Message",
    "keyword_filter_option": "Filters",
    "gemini_api_key": "Translation",
    "check_message_every_n_sec": "Runtime",
}


@dataclass(frozen=True)
class BotConfig:
    dc_webhook_url: str
    tg_announcement_channel: str
    embed_color: int
    embed_title_setting: str
    keyword_filter_option: str
    keyword_filter_bank: tuple[str, ...]
    forward_image: str
    only_plaintext: str
    gemini_api_key: str
    model: str
    translation_prompt: str
    check_interval_seconds: float
    content_text: str

    @classmethod
    def from_values(cls, values: dict[str, str]) -> "BotConfig":
        dc_webhook_url = require_value(values["dc_webhook_url"], "DC_WEBHOOK_URL")
        if not dc_webhook_url.startswith("https://discord.com/api/webhooks/"):
            raise CustomError(
                '[DC_WEBHOOK_URL] A valid webhook url should start with "https://discord.com/api/webhooks/".'
            )

        tg_link = require_value(
            values["tg_announcement_channel"], "TG_ANNOUNCEMENT_CHANNEL"
        )
        if not tg_link.startswith("https://t.me/"):
            raise CustomError(
                '[TG_ANNOUNCEMENT_CHANNEL] A valid channel link should start with "https://t.me/".'
            )
        tg_announcement_channel = tg_link[len("https://t.me/") :].strip("/")
        if not tg_announcement_channel:
            raise CustomError("[TG_ANNOUNCEMENT_CHANNEL] Missing channel name.")

        embed_color_raw = require_value(values["embed_color"], "EMBED_COLOR")
        if not embed_color_raw.startswith("0x"):
            raise CustomError(
                '[EMBED_COLOR] A valid embed color should start with "0x".'
            )
        try:
            embed_color = int(embed_color_raw, 16)
        except ValueError as error:
            raise CustomError("[EMBED_COLOR] Invalid hex color.") from error

        embed_title_setting = values["embed_title_setting"].strip()
        if embed_title_setting not in {"1", "2", "3"}:
            raise CustomError(
                "[EMBED_TITLE_SETTING] A valid title setting should be 1, 2 or 3."
            )

        keyword_filter_option = values["keyword_filter_option"].strip()
        if keyword_filter_option not in {"", "1", "2"}:
            raise CustomError(
                "[KEYWORD_FILTER_OPTION] You should input 1, 2 or leave it blank."
            )

        keyword_filter_bank = tuple(
            keyword.strip()
            for keyword in values["keyword_filter_bank"].split(",")
            if keyword.strip()
        )
        if keyword_filter_option in {"1", "2"} and not keyword_filter_bank:
            raise CustomError(
                "[KEYWORD_FILTER_BANK] Keywords are required when keyword filter is enabled."
            )
        if keyword_filter_option == "" and keyword_filter_bank:
            raise CustomError(
                "[KEYWORD_FILTER_OPTION] Choose 1 or 2 when KEYWORD_FILTER_BANK is set."
            )

        forward_image = values["forward_image"].strip()
        if forward_image not in {"1", "2"}:
            raise CustomError("[FORWARD_IMAGE] You should input 1 or 2.")

        only_plaintext = values["only_plaintext"].strip()
        if only_plaintext not in {"", "1"}:
            raise CustomError("[ONLY_PLAINTEXT] You should input 1 or leave it blank.")

        gemini_api_key = values["gemini_api_key"].strip()
        model = values["model"].strip()
        translation_prompt = values["translation_prompt"].strip()
        if gemini_api_key and not model:
            raise CustomError(
                "[MODEL] Missing MODEL. Leave GEMINI_API_KEY blank to disable translation."
            )
        if gemini_api_key and not translation_prompt:
            raise CustomError(
                "[TRANSLATION_PROMPT] Missing TRANSLATION_PROMPT. Leave GEMINI_API_KEY blank to disable translation."
            )

        check_interval_raw = require_value(
            values["check_message_every_n_sec"], "CHECK_MESSAGE_EVERY_N_SEC"
        )
        try:
            check_interval_seconds = float(check_interval_raw)
        except ValueError as error:
            raise CustomError(
                "[CHECK_MESSAGE_EVERY_N_SEC] Check interval should be a number."
            ) from error
        if check_interval_seconds <= 0:
            raise CustomError(
                "[CHECK_MESSAGE_EVERY_N_SEC] Check interval should be greater than 0."
            )

        return cls(
            dc_webhook_url=dc_webhook_url,
            tg_announcement_channel=tg_announcement_channel,
            embed_color=embed_color,
            embed_title_setting=embed_title_setting,
            keyword_filter_option=keyword_filter_option,
            keyword_filter_bank=keyword_filter_bank,
            forward_image=forward_image,
            only_plaintext=only_plaintext,
            gemini_api_key=gemini_api_key,
            model=model,
            translation_prompt=translation_prompt,
            check_interval_seconds=check_interval_seconds,
            content_text=values["content_text"],
        )


def require_value(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise CustomError(f"[{field_name}] Missing value.")
    return normalized_value


class TelegramDiscordBot:
    def __init__(self, config: BotConfig, log: Callable[[str], None]):
        self.config = config
        self.log = log
        self.msg_log: list[str] = []
        self.initialized = False
        self.script_start_time = datetime.datetime.now()

    def scrape_telegram_message_box(self):
        tg_html = requests.get(
            f"https://t.me/s/{self.config.tg_announcement_channel}",
            timeout=20,
        )
        tg_html.raise_for_status()
        tg_soup = BeautifulSoup(tg_html.text, "html.parser")
        return tg_soup.find_all(
            "div", {"class": "tgme_widget_message_wrap js-widget_message_wrap"}
        )

    def get_link(self, tg_box) -> str:
        return tg_box.find_all("a", {"class": "tgme_widget_message_date"}, href=True)[
            0
        ]["href"]

    def get_text(self, tg_box) -> str | None:
        msg_text = tg_box.find_all(
            "div", {"class": "tgme_widget_message_text js-message_text"}
        )
        converted_text = ""
        if msg_text == []:
            return None

        msg_text = msg_text[0]
        for child in msg_text.children:
            if child.name is None:
                converted_text += str(child)

            elif child.name == "a":
                href = child.get("href", "")
                if child.text == href:
                    converted_text += href
                else:
                    converted_text += f"[{child.text}]({re.sub('amp;', '', href)})"

            elif child.name == "code":
                converted_text += f"`{child.text}`"

            elif child.name == "b":
                converted_text += f"**{child.text}**"

            elif child.name == "tg-spoiler":
                converted_text += f"||{child.text}||"

            elif child.name == "i":
                converted_text += f"*{child.text}*"

            elif child.name == "u":
                converted_text += f"__{child.text}__"

            elif child.name == "s":
                converted_text += f"~~{child.text}~~"

            elif child.name == "br":
                converted_text += "\n"

        return converted_text

    def get_image(self, tg_box) -> str | None:
        msg_image = tg_box.find(
            "a", {"class": "tgme_widget_message_photo_wrap"}, href=True
        )
        if msg_image is None:
            return None

        start_index = msg_image["style"].find("background-image:url('") + 22
        end_index = msg_image["style"].find(".jpg')") + 4
        return msg_image["style"][start_index:end_index]

    def keyword_filter(self, msg_text: str | None) -> bool:
        if msg_text in {None, ""}:
            return False

        if self.config.keyword_filter_option == "":
            return False

        if self.config.keyword_filter_option == "1":
            return not any(
                keyword in msg_text for keyword in self.config.keyword_filter_bank
            )

        if self.config.keyword_filter_option == "2":
            return any(
                keyword in msg_text for keyword in self.config.keyword_filter_bank
            )

        return True

    def translate(self, original_text: str) -> str:
        client = genai.Client(api_key=self.config.gemini_api_key)
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=original_text),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TranslationSchema,
            system_instruction=[
                types.Part.from_text(text=self.config.translation_prompt),
            ],
        )

        response = client.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=generate_content_config,
        )
        if response.parsed is None:
            raise CustomError(
                "[GEMINI_API_KEY] Gemini returned an empty parsed response."
            )

        return response.parsed.translated_content

    def send_message(
        self,
        msg_link: str,
        msg_text: str | None,
        msg_image: str | None,
    ):
        if self.keyword_filter(msg_text):
            self.log(f"Skipped by keyword filter: {msg_link}")
            return

        if msg_image is not None and self.config.forward_image == "2":
            self.log(f"Skipped image message: {msg_link}")
            return

        webhook = SyncWebhook.from_url(self.config.dc_webhook_url)
        embed = Embed(title="", color=self.config.embed_color)

        if msg_text is not None:
            if self.config.gemini_api_key:
                msg_text = self.translate(msg_text)
            embed.description = msg_text

        if msg_image is not None and self.config.only_plaintext != "1":
            embed.set_image(url=msg_image)

        if self.config.embed_title_setting == "2":
            embed.title = "Forward From Telegram"
        if self.config.embed_title_setting == "3":
            embed.title = "Original Telegram Link"
            embed.url = msg_link

        if self.config.content_text:
            webhook.send(content=self.config.content_text, embed=embed)
        else:
            webhook.send(embed=embed)

        self.log(f"Forwarded to Discord: {msg_link}")

    def poll_once(self):
        msg_temp: list[str] = []
        new_messages: list[tuple[str, str | None, str | None]] = []

        for tg_box in self.scrape_telegram_message_box():
            msg_link = self.get_link(tg_box)
            msg_text = self.get_text(tg_box)
            msg_image = self.get_image(tg_box)

            msg_temp.append(msg_link)
            if msg_link not in self.msg_log:
                new_messages.append((msg_link, msg_text, msg_image))

        if self.initialized:
            for msg_link, msg_text, msg_image in new_messages:
                self.send_message(msg_link, msg_text, msg_image)
        elif msg_temp:
            self.log(f"Loaded {len(msg_temp)} existing Telegram messages.")
        else:
            self.log("No existing Telegram messages found.")

        self.msg_log = msg_temp
        self.initialized = True

    def run(self, stop_event: threading.Event):
        self.script_start_time = datetime.datetime.now()
        self.log("Bot started.")

        while not stop_event.is_set():
            try:
                self.poll_once()
                time_passed = datetime.datetime.now() - self.script_start_time
                self.log(f"Bot working. time passed: {time_passed}")
            except Exception as error:
                self.log(f"[   E R R O R   ] {error}")

            stop_event.wait(self.config.check_interval_seconds)

        self.log("Bot stopped.")


BOT_THREAD_STOPPED = object()


class TelegramDiscordTUI(App):
    TITLE = "Telegram Discord Bot"
    CSS = """
    Screen {
        layout: vertical;
        background: #090b10;
        color: #d7dde7;
    }

    #topbar {
        height: 3;
        padding: 0 2;
        background: #0d1118;
    }

    #brand {
        width: 1fr;
        content-align: left middle;
        color: #f4f7fb;
        text-style: bold;
    }

    #hint {
        width: auto;
        content-align: right middle;
        color: #6f7a8c;
    }

    #main {
        height: 1fr;
        padding: 1 2 1 2;
        background: #090b10;
    }

    #config-panel {
        width: 54;
        min-width: 46;
        padding: 0 2 1 0;
        background: #090b10;
        border: none;
        scrollbar-background: #090b10;
        scrollbar-color: #252d3b;
        scrollbar-color-hover: #343f51;
    }

    #runtime-panel {
        width: 1fr;
        padding: 0 0 1 2;
        background: #090b10;
    }

    .panel-title {
        text-style: bold;
        color: #f4f7fb;
        margin: 0 0 1 0;
    }

    .section-title {
        margin: 1 0 0 0;
        color: #2dd4bf;
        text-style: bold;
    }

    .field-label {
        margin-top: 0;
        color: #788395;
    }

    Input {
        height: 3;
        margin-bottom: 1;
        padding: 0 1;
        background: #111722;
        color: #d7dde7;
        border: tall #111722;
    }

    Input:focus {
        background: #151d2a;
        border: tall #2dd4bf;
    }

    Input:disabled {
        background: #0f141d;
        color: #5c6676;
        border: tall #0f141d;
    }

    #actions {
        height: 3;
        margin-top: 0;
    }

    Button {
        min-width: 12;
        height: 3;
        margin-right: 1;
        text-style: bold;
        border: tall #171d28;
    }

    #start {
        background: #2dd4bf;
        color: #06100e;
        border: tall #2dd4bf;
    }

    #start:hover {
        background: #5eead4;
        border: tall #5eead4;
    }

    #stop {
        background: #25131a;
        color: #fda4af;
        border: tall #3a1b26;
    }

    #stop:hover {
        background: #3b1825;
        border: tall #7f1d35;
    }

    Button:disabled {
        background: #111722;
        color: #4d5868;
        border: tall #111722;
    }

    #status {
        height: 3;
        margin-bottom: 1;
        padding: 1;
        background: #111722;
        color: #cbd5e1;
        border: tall #111722;
    }

    #log {
        height: 1fr;
        padding: 1;
        background: #0d1118;
        color: #b8c2d2;
        border: tall #111722;
    }
    """
    BINDINGS = [("q", "quit_app", "Quit")]

    def __init__(self):
        super().__init__()
        self.log_queue: Queue[object] = Queue()
        self.stop_event: threading.Event | None = None
        self.bot_thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static("Telegram Discord Bot", id="brand")
            yield Static("q quit", id="hint")
        with Horizontal(id="main"):
            with VerticalScroll(id="config-panel"):
                yield Static("Settings", classes="panel-title")
                for field in FIELDS:
                    if field.key in SECTION_BEFORE_FIELD:
                        yield Static(
                            SECTION_BEFORE_FIELD[field.key],
                            classes="section-title",
                        )
                    yield Label(field.label, classes="field-label")
                    yield Input(
                        value=os.getenv(field.env_name, ""),
                        placeholder=field.placeholder,
                        password=field.password,
                        id=field.key,
                    )
                with Horizontal(id="actions"):
                    yield Button("Start", variant="success", id="start")
                    stop_button = Button("Stop", variant="error", id="stop")
                    stop_button.disabled = True
                    yield stop_button
            with Vertical(id="runtime-panel"):
                yield Static("Status: stopped", id="status")
                yield RichLog(id="log", wrap=True, highlight=True)

    def on_mount(self):
        self.set_interval(0.25, self.drain_log_queue)
        self.write_log("Ready. Review the configuration and press Start.")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "start":
            self.start_bot()
        elif event.button.id == "stop":
            self.stop_bot()

    def action_quit_app(self):
        self.stop_bot()
        self.exit()

    def start_bot(self):
        if self.bot_thread is not None and self.bot_thread.is_alive():
            return

        try:
            config = BotConfig.from_values(self.collect_values())
        except CustomError as error:
            self.set_status(f"Config error: {error}")
            self.write_log(str(error))
            return

        self.stop_event = threading.Event()
        bot = TelegramDiscordBot(config, self.log_from_thread)
        self.bot_thread = threading.Thread(
            target=self.run_bot_thread,
            args=(bot, self.stop_event),
            daemon=True,
        )
        self.bot_thread.start()
        self.set_form_enabled(False)
        self.set_status(
            "Running: "
            f"t.me/{config.tg_announcement_channel} "
            f"every {config.check_interval_seconds:g}s"
        )

    def stop_bot(self):
        if self.stop_event is None:
            return

        self.stop_event.set()
        self.set_status("Stopping...")
        self.query_one("#stop", Button).disabled = True

    def run_bot_thread(self, bot: TelegramDiscordBot, stop_event: threading.Event):
        try:
            bot.run(stop_event)
        finally:
            self.log_queue.put(BOT_THREAD_STOPPED)

    def collect_values(self) -> dict[str, str]:
        return {
            field.key: self.query_one(f"#{field.key}", Input).value
            for field in FIELDS
        }

    def log_from_thread(self, message: str):
        self.log_queue.put(message)

    def drain_log_queue(self):
        while True:
            try:
                item = self.log_queue.get_nowait()
            except Empty:
                break

            if item is BOT_THREAD_STOPPED:
                self.bot_thread = None
                self.stop_event = None
                self.set_form_enabled(True)
                self.set_status("Stopped")
            else:
                self.write_log(str(item))

    def set_form_enabled(self, enabled: bool):
        for field in FIELDS:
            self.query_one(f"#{field.key}", Input).disabled = not enabled
        self.query_one("#start", Button).disabled = not enabled
        self.query_one("#stop", Button).disabled = enabled

    def set_status(self, message: str):
        self.query_one("#status", Static).update(message)

    def write_log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.query_one("#log", RichLog).write(f"[{timestamp}] {message}")


if __name__ == "__main__":
    TelegramDiscordTUI().run()
