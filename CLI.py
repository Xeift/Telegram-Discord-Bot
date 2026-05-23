from __future__ import annotations

import datetime
import json
import re
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import Callable

import requests
from bs4 import BeautifulSoup
from discord import Embed, SyncWebhook
from google import genai
from google.genai import types
from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RichLog, Static


class CustomError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ConfigFileError(CustomError):
    pass


class ConfigMissingError(ConfigFileError):
    pass


class TranslationSchema(BaseModel):
    translated_content: str


@dataclass(frozen=True)
class FieldDefinition:
    key: str
    label: str
    placeholder: str = ""
    password: bool = False
    default: str = ""
    options: tuple[tuple[str, str], ...] = ()


FIELDS = (
    FieldDefinition(
        "dc_webhook_url",
        "Discord webhook",
        "https://discord.com/api/webhooks/...",
        True,
    ),
    FieldDefinition(
        "tg_announcement_channel",
        "Telegram channel",
        "https://t.me/example_channel",
    ),
    FieldDefinition(
        "embed_color",
        "Embed color",
        "0xe8006f",
        default="0xe8006f",
    ),
    FieldDefinition(
        "embed_title_setting",
        "Title mode",
        default="3",
        options=(
            ("None", "1"),
            ("Title", "2"),
            ("Link", "3"),
        ),
    ),
    FieldDefinition(
        "keyword_filter_option",
        "Keyword mode",
        default="",
        options=(
            ("All", ""),
            ("Include", "1"),
            ("Exclude", "2"),
        ),
    ),
    FieldDefinition(
        "keyword_filter_bank",
        "Keywords",
        "ant,bear,cat",
    ),
    FieldDefinition(
        "forward_image",
        "Images",
        default="1",
        options=(
            ("Forward", "1"),
            ("Skip", "2"),
        ),
    ),
    FieldDefinition(
        "only_plaintext",
        "Plaintext only",
        default="",
        options=(
            ("Off", ""),
            ("On", "1"),
        ),
    ),
    FieldDefinition(
        "gemini_api_key",
        "Gemini key",
        "",
        True,
    ),
    FieldDefinition(
        "model",
        "Gemini model",
        "gemini-2.5-flash-lite",
        default="gemini-2.5-flash-lite",
    ),
    FieldDefinition(
        "translation_prompt",
        "Prompt",
        "Please translate it naturally into English (en-US)",
        default="Please translate it naturally into English (en-US)",
    ),
    FieldDefinition(
        "check_message_every_n_sec",
        "Poll interval",
        "20",
        default="20",
    ),
    FieldDefinition(
        "content_text",
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

CONFIG_FILE_NAME = "config.json"
CONFIG_VERSION = 1


def field_groups() -> list[tuple[str, list[FieldDefinition]]]:
    groups: list[tuple[str, list[FieldDefinition]]] = []

    for field in FIELDS:
        section = SECTION_BEFORE_FIELD.get(field.key)
        if section is not None:
            groups.append((section, []))

        groups[-1][1].append(field)

    return groups


def field_pairs(fields: list[FieldDefinition]) -> list[list[FieldDefinition]]:
    return [fields[index : index + 2] for index in range(0, len(fields), 2)]


def get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
    else:
        app_dir = Path(__file__).resolve().parent

    return app_dir / CONFIG_FILE_NAME


def default_values() -> dict[str, str]:
    return {field.key: field.default for field in FIELDS}


def require_config_value_map(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ConfigFileError("[config.json] Config should be a JSON object.")

    version = data.get("version")
    if version != CONFIG_VERSION:
        raise ConfigFileError(
            f"[config.json] Expected version {CONFIG_VERSION}, got {version!r}."
        )

    values: dict[str, str] = {}
    for field in FIELDS:
        if field.key not in data:
            raise ConfigFileError(f"[config.json] Missing {field.key}.")

        value = data[field.key]
        if not isinstance(value, str):
            raise ConfigFileError(f"[config.json] {field.key} should be a string.")
        values[field.key] = value

    return values


def load_config_values() -> dict[str, str]:
    config_path = get_config_path()
    if not config_path.exists():
        raise ConfigMissingError(f"[config.json] Missing {config_path}.")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ConfigFileError(f"[config.json] Invalid JSON: {error}") from error
    except OSError as error:
        raise ConfigFileError(
            f"[config.json] Cannot read {config_path}: {error}"
        ) from error

    values = require_config_value_map(data)
    BotConfig.from_values(values)
    return values


def save_config_values(values: dict[str, str]):
    BotConfig.from_values(values)
    payload = {"version": CONFIG_VERSION}
    payload.update({field.key: values[field.key] for field in FIELDS})

    config_path = get_config_path()
    try:
        config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise ConfigFileError(
            f"[config.json] Cannot write {config_path}: {error}"
        ) from error


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


class SetupScreen(Screen):
    def __init__(
        self,
        values: dict[str, str],
        can_go_back: bool,
        message: str = "",
    ):
        super().__init__()
        self.values = dict(values)
        self.can_go_back = can_go_back
        self.message = message
        self.option_lookup: dict[str, tuple[str, str]] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="setup-main"):
            with VerticalScroll(id="setup-panel"):
                yield Static("Settings", classes="panel-title")
                for section, fields in field_groups():
                    yield Static(section, classes="section-title")
                    for pair in field_pairs(fields):
                        with Horizontal(classes="field-row"):
                            for field in pair:
                                with Vertical(classes="field-cell"):
                                    yield Label(field.label, classes="field-label")
                                    if field.options:
                                        with Horizontal(classes="option-row"):
                                            for index, option in enumerate(
                                                field.options
                                            ):
                                                label, value = option
                                                option_id = f"{field.key}_{index}"
                                                self.option_lookup[option_id] = (
                                                    field.key,
                                                    value,
                                                )
                                                classes = "option-button"
                                                if self.values[field.key] == value:
                                                    classes += " selected"
                                                yield Button(
                                                    label,
                                                    id=option_id,
                                                    classes=classes,
                                                )
                                    else:
                                        yield Input(
                                            value=self.values[field.key],
                                            placeholder=field.placeholder,
                                            password=field.password,
                                            id=field.key,
                                        )
            with Vertical(id="setup-aside"):
                yield Static("Config", classes="panel-title")
                yield Static(str(get_config_path()), id="config-path")
                yield Static(self.message, id="setup-message")
                with Horizontal(id="actions"):
                    yield Button("Save", id="save")
                    yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            self.save()
        elif event.button.id == "back":
            self.back()
        elif event.button.id in self.option_lookup:
            self.select_option(event.button.id)

    def collect_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for field in FIELDS:
            if field.options:
                values[field.key] = self.values[field.key]
            else:
                widget = self.query_one(f"#{field.key}", Input)
                values[field.key] = widget.value

        return values

    def select_option(self, option_id: str):
        field_key, selected_value = self.option_lookup[option_id]
        self.values[field_key] = selected_value

        for button_id, option in self.option_lookup.items():
            option_field_key, _ = option
            if option_field_key != field_key:
                continue

            button = self.query_one(f"#{button_id}", Button)
            if button_id == option_id:
                button.add_class("selected")
            else:
                button.remove_class("selected")

    def save(self):
        values = self.collect_values()
        try:
            config = BotConfig.from_values(values)
            save_config_values(values)
        except CustomError as error:
            self.query_one("#setup-message", Static).update(str(error))
            return

        app = self.app
        app.config_values = values
        app.bot_config = config
        if self.can_go_back:
            app.pop_screen()
            app.refresh_main_screen()
        else:
            app.switch_screen(MainScreen())

    def back(self):
        if self.can_go_back:
            self.app.pop_screen()
        else:
            self.app.exit()


class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="overview-panel"):
                yield Static("Overview", classes="panel-title")
                yield Static("", id="summary")
                with Horizontal(id="actions"):
                    yield Button("Start", id="start")
                    stop_button = Button("Stop", id="stop")
                    stop_button.disabled = True
                    yield stop_button
                with Horizontal(id="actions-secondary"):
                    yield Button("Settings", id="settings")
                    yield Button("Exit", id="exit")
            with Vertical(id="runtime-panel"):
                yield Static("Status: stopped", id="status")
                yield RichLog(id="log", wrap=True, highlight=True)

    def on_mount(self):
        self.refresh_config()
        self.refresh_runtime_state()
        self.write_log("Ready. Press Start to begin forwarding.")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "start":
            self.app.start_bot()
        elif event.button.id == "stop":
            self.app.stop_bot()
        elif event.button.id == "settings":
            self.app.open_settings()
        elif event.button.id == "exit":
            self.app.action_quit_app()

    def refresh_config(self):
        config = self.app.bot_config
        if config is None:
            self.query_one("#summary", Static).update("No saved config.")
            return

        filter_mode = {
            "": "off",
            "1": "include keywords",
            "2": "exclude keywords",
        }[config.keyword_filter_option]
        image_mode = "forward" if config.forward_image == "1" else "skip"
        plaintext_mode = "on" if config.only_plaintext == "1" else "off"
        translation_mode = "on" if config.gemini_api_key else "off"
        summary = "\n".join(
            [
                f"Channel       t.me/{config.tg_announcement_channel}",
                f"Interval      {config.check_interval_seconds:g}s",
                f"Images        {image_mode}",
                f"Plaintext     {plaintext_mode}",
                f"Filter        {filter_mode}",
                f"Translation   {translation_mode}",
                f"Config        {get_config_path()}",
            ]
        )
        self.query_one("#summary", Static).update(summary)

    def refresh_runtime_state(self):
        is_running = self.app.is_bot_running()
        self.query_one("#start", Button).disabled = is_running
        self.query_one("#stop", Button).disabled = not is_running
        self.query_one("#settings", Button).disabled = is_running

    def set_status(self, message: str):
        self.query_one("#status", Static).update(message)

    def write_log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.query_one("#log", RichLog).write(f"[{timestamp}] {message}")


class TelegramDiscordTUI(App):
    TITLE = "Telegram Discord Bot"
    CSS = """
    Screen {
        layout: vertical;
        background: #090b10;
        color: #d7dde7;
    }

    #main,
    #setup-main {
        height: 1fr;
        padding: 1 2 1 2;
        background: #090b10;
    }

    #setup-panel {
        width: 1fr;
        padding: 0 2 1 0;
        background: #090b10;
        border: none;
        scrollbar-background: #090b10;
        scrollbar-color: #252d3b;
        scrollbar-color-hover: #343f51;
    }

    #setup-aside {
        width: 44;
        min-width: 36;
        padding: 0 0 1 2;
        background: #090b10;
    }

    #overview-panel {
        width: 40;
        min-width: 36;
        padding: 0 2 1 0;
        background: #090b10;
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

    .meta-line {
        color: #5f6b7d;
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

    .field-row {
        height: 5;
        margin-bottom: 1;
    }

    .field-cell {
        width: 1fr;
        height: 5;
        margin-right: 1;
    }

    Input {
        height: 3;
        padding: 0 1;
        background: #111722;
        color: #d7dde7;
        border: tall #111722;
    }

    Input:focus {
        background: #151d2a;
        border: tall #2dd4bf;
    }

    .option-row {
        height: 3;
    }

    #summary {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: #0d1118;
        color: #b8c2d2;
        border: tall #111722;
    }

    #config-path {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: #0d1118;
        color: #8b96a8;
        border: tall #111722;
    }

    #setup-message {
        min-height: 3;
        margin-bottom: 1;
        padding: 1;
        background: #25131a;
        color: #fda4af;
        border: tall #3a1b26;
    }

    #actions,
    #actions-secondary {
        height: 3;
        margin-top: 0;
    }

    #actions-secondary {
        margin-top: 1;
    }

    Button {
        min-width: 12;
        height: 3;
        margin-right: 1;
        text-style: bold;
        background: #111722;
        color: #d7dde7;
        border: tall #171d28;
    }

    .option-button {
        width: 1fr;
        min-width: 8;
        margin-right: 1;
        background: #111722;
        color: #8b96a8;
        border: tall #111722;
    }

    .option-button:hover {
        background: #151d2a;
        color: #d7dde7;
        border: tall #2d3748;
    }

    .option-button:focus {
        border: tall #2dd4bf;
    }

    .option-button.selected {
        background: #123b38;
        color: #e6fffb;
        border: tall #2dd4bf;
    }

    #save,
    #start {
        background: #2dd4bf;
        color: #06100e;
        border: tall #2dd4bf;
    }

    #save:hover,
    #start:hover {
        background: #5eead4;
        border: tall #5eead4;
    }

    #stop,
    #exit {
        background: #25131a;
        color: #fda4af;
        border: tall #3a1b26;
    }

    #stop:hover,
    #exit:hover {
        background: #3b1825;
        border: tall #7f1d35;
    }

    #back:hover,
    #settings:hover {
        background: #151d2a;
        border: tall #2d3748;
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
        self.config_values = default_values()
        self.bot_config: BotConfig | None = None
        self.log_queue: Queue[object] = Queue()
        self.stop_event: threading.Event | None = None
        self.bot_thread: threading.Thread | None = None

    def on_mount(self):
        self.set_interval(0.25, self.drain_log_queue)
        try:
            self.config_values = load_config_values()
            self.bot_config = BotConfig.from_values(self.config_values)
        except ConfigMissingError:
            self.push_screen(
                SetupScreen(
                    self.config_values,
                    can_go_back=False,
                    message="No config.json found. Save settings to create it.",
                )
            )
        except CustomError as error:
            self.push_screen(
                SetupScreen(
                    self.config_values,
                    can_go_back=False,
                    message=str(error),
                )
            )
        else:
            self.push_screen(MainScreen())

    def action_quit_app(self):
        self.stop_bot()
        self.exit()

    def open_settings(self):
        if self.is_bot_running():
            self.set_main_status("Status: stop the bot before editing settings")
            return

        self.push_screen(SetupScreen(self.config_values, can_go_back=True))

    def start_bot(self):
        if self.bot_thread is not None and self.bot_thread.is_alive():
            return

        if self.bot_config is None:
            self.set_main_status("Status: missing config")
            return

        self.stop_event = threading.Event()
        bot = TelegramDiscordBot(self.bot_config, self.log_from_thread)
        self.bot_thread = threading.Thread(
            target=self.run_bot_thread,
            args=(bot, self.stop_event),
            daemon=True,
        )
        self.bot_thread.start()
        self.set_main_status(
            "Status: running "
            f"t.me/{self.bot_config.tg_announcement_channel} "
            f"every {self.bot_config.check_interval_seconds:g}s"
        )
        self.refresh_main_screen()

    def stop_bot(self):
        if self.stop_event is None:
            return

        self.stop_event.set()
        self.set_main_status("Status: stopping")
        self.refresh_main_screen()

    def run_bot_thread(self, bot: TelegramDiscordBot, stop_event: threading.Event):
        try:
            bot.run(stop_event)
        finally:
            self.log_queue.put(BOT_THREAD_STOPPED)

    def is_bot_running(self) -> bool:
        return self.bot_thread is not None and self.bot_thread.is_alive()

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
                self.set_main_status("Status: stopped")
                self.refresh_main_screen()
            else:
                self.write_log(str(item))

    def refresh_main_screen(self):
        if isinstance(self.screen, MainScreen):
            self.screen.refresh_config()
            self.screen.refresh_runtime_state()

    def set_main_status(self, message: str):
        if isinstance(self.screen, MainScreen):
            self.screen.set_status(message)

    def write_log(self, message: str):
        if isinstance(self.screen, MainScreen):
            self.screen.write_log(message)


if __name__ == "__main__":
    TelegramDiscordTUI().run()
