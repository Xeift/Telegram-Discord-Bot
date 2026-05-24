from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
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
        "Check new messages every",
        "20",
        default="20",
    ),
    FieldDefinition(
        "content_text",
        "Message above embed",
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
HEADLESS_PID_FILE_NAME = "telegram-discord-bot.pid"
HEADLESS_LOG_FILE_NAME = "telegram-discord-bot.log"
HEADLESS_STOP_TIMEOUT_SECONDS = 30


def wrap_dashboard_url(url: str, chunk_size: int = 90) -> str:
    return "\n".join(
        url[index : index + chunk_size] for index in range(0, len(url), chunk_size)
    )


def field_groups() -> list[tuple[str, list[FieldDefinition]]]:
    groups: list[tuple[str, list[FieldDefinition]]] = []

    for field in FIELDS:
        section = SECTION_BEFORE_FIELD.get(field.key)
        if section is not None:
            groups.append((section, []))

        groups[-1][1].append(field)

    return groups


def field_by_key(fields: list[FieldDefinition], key: str) -> FieldDefinition:
    for field in fields:
        if field.key == key:
            return field

    raise CustomError(f"[{key}] Missing field definition.")


def field_pairs(fields: list[FieldDefinition]) -> list[list[FieldDefinition]]:
    return [fields[index : index + 2] for index in range(0, len(fields), 2)]


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def get_config_path() -> Path:
    return get_app_dir() / CONFIG_FILE_NAME


def get_headless_pid_path() -> Path:
    return get_app_dir() / HEADLESS_PID_FILE_NAME


def get_headless_log_path() -> Path:
    return get_app_dir() / HEADLESS_LOG_FILE_NAME


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
                    if section == "Connection":
                        with Horizontal(classes="connection-flow"):
                            yield from self.compose_field(
                                field_by_key(fields, "tg_announcement_channel"),
                                classes="connection-node",
                            )
                            yield Static("->", classes="connection-arrow")
                            yield from self.compose_field(
                                field_by_key(fields, "dc_webhook_url"),
                                classes="connection-node",
                            )
                    else:
                        for pair in field_pairs(fields):
                            with Horizontal(classes="field-row"):
                                for field in pair:
                                    yield from self.compose_field(
                                        field,
                                        classes="field-cell",
                                    )
            with Vertical(id="setup-aside"):
                yield Static("Config", classes="panel-title")
                yield Static(str(get_config_path()), id="config-path")
                message_classes = "" if self.message else "hidden"
                yield Static(self.message, id="setup-message", classes=message_classes)
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

    def compose_field(self, field: FieldDefinition, classes: str):
        with Vertical(classes=classes):
            yield Label(field.label, classes="field-label")
            if field.options:
                with Horizontal(classes="option-row"):
                    for index, option in enumerate(field.options):
                        label, value = option
                        option_id = f"{field.key}_{index}"
                        self.option_lookup[option_id] = (
                            field.key,
                            value,
                        )
                        option_classes = "option-button"
                        if self.values[field.key] == value:
                            option_classes += " selected"
                        yield Button(
                            label,
                            id=option_id,
                            classes=option_classes,
                        )
            else:
                yield Input(
                    value=self.values[field.key],
                    placeholder=field.placeholder,
                    password=field.password,
                    id=field.key,
                )

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
            setup_message = self.query_one("#setup-message", Static)
            setup_message.update(str(error))
            setup_message.remove_class("hidden")
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
        with Vertical(id="main"):
            with Horizontal(id="dashboard"):
                with Vertical(id="forwarding-panel"):
                    yield Static("Forwarding", classes="panel-title")
                    with Vertical(id="forwarding-surface"):
                        with Horizontal(id="flow-row"):
                            with Vertical(id="telegram-node", classes="flow-node"):
                                yield Static("Telegram channel", classes="flow-label")
                                yield Static("", id="telegram-url", classes="flow-url")
                            yield Static("->", id="flow-arrow")
                            with Vertical(id="discord-node", classes="flow-node"):
                                yield Static("Discord webhook", classes="flow-label")
                                yield Static("", id="discord-url", classes="flow-url")
                        yield Static("", id="runtime-summary")
                with Vertical(id="controls-panel"):
                    yield Static("Controls", classes="panel-title")
                    with Vertical(id="controls-surface"):
                        yield Static("", id="status", classes="hidden")
                        with Horizontal(id="actions"):
                            yield Button(
                                "Start",
                                id="run-toggle",
                                classes="control-button run-button",
                            )
                            yield Button(
                                "Settings",
                                id="settings",
                                classes="control-button",
                            )
                            yield Button("Exit", id="exit", classes="control-button")
            with Vertical(id="log-panel"):
                yield Static("Runtime log", classes="panel-title")
                yield RichLog(id="log", wrap=True, highlight=True)

    def on_mount(self):
        self.refresh_config()
        self.refresh_runtime_state()
        self.write_log("Ready. Press Start to begin forwarding.")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "run-toggle":
            if self.app.is_bot_running():
                self.app.stop_bot()
            else:
                self.app.start_bot()
        elif event.button.id == "settings":
            self.app.open_settings()
        elif event.button.id == "exit":
            self.app.action_quit_app()

    def refresh_config(self):
        config = self.app.bot_config
        if config is None:
            self.query_one("#telegram-url", Static).update("")
            self.query_one("#discord-url", Static).update("")
            self.query_one("#runtime-summary", Static).update("No saved config.")
            return

        filter_mode = {
            "": "off",
            "1": "include keywords",
            "2": "exclude keywords",
        }[config.keyword_filter_option]
        image_mode = "forward" if config.forward_image == "1" else "skip"
        plaintext_mode = "on" if config.only_plaintext == "1" else "off"
        translation_mode = "on" if config.gemini_api_key else "off"
        content_mode = "on" if config.content_text else "off"
        runtime_summary = (
            f"Every {config.check_interval_seconds:g}s | "
            f"images {image_mode} | plaintext {plaintext_mode} | "
            f"filter {filter_mode} | translation {translation_mode} | "
            f"message above embed {content_mode}"
        )
        self.query_one("#telegram-url", Static).update(
            wrap_dashboard_url(f"https://t.me/{config.tg_announcement_channel}", 30)
        )
        self.query_one("#discord-url", Static).update(
            wrap_dashboard_url(config.dc_webhook_url, 76)
        )
        self.query_one("#runtime-summary", Static).update(runtime_summary)

    def refresh_runtime_state(self):
        is_running = self.app.is_bot_running()
        is_stopping = self.app.stop_event is not None and self.app.stop_event.is_set()
        run_button = self.query_one("#run-toggle", Button)
        if is_stopping:
            run_button.label = "Stopping"
        elif is_running:
            run_button.label = "Stop"
        else:
            run_button.label = "Start"

        run_button.disabled = is_stopping
        run_button.set_class(is_running, "running")
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

    #main {
        layout: vertical;
    }

    #dashboard {
        height: 10;
        margin-bottom: 1;
        background: #090b10;
    }

    #forwarding-panel {
        width: 1fr;
        padding-right: 2;
    }

    #controls-panel {
        width: 46;
    }

    #controls-surface {
        height: 8;
        padding: 2 1 0 1;
        background: #111722;
        border: tall #151d2a;
    }

    #log-panel {
        height: 1fr;
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

    .connection-flow {
        height: 5;
        margin-bottom: 1;
    }

    .connection-node {
        width: 1fr;
        height: 5;
    }

    .connection-arrow {
        width: 6;
        height: 5;
        content-align: center middle;
        color: #2dd4bf;
        text-style: bold;
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

    #forwarding-surface {
        height: 8;
        padding: 0 1;
        background: #111722;
        color: #b8c2d2;
        border: tall #151d2a;
    }

    #flow-row {
        height: 6;
    }

    .flow-node {
        height: 6;
        padding: 0 1;
        background: #0d1118;
        border: tall #1d2735;
    }

    #telegram-node {
        width: 34;
    }

    #discord-node {
        width: 1fr;
    }

    .flow-label {
        height: 1;
        color: #2dd4bf;
        text-style: bold;
    }

    .flow-url {
        height: auto;
        color: #cbd5e1;
    }

    #flow-arrow {
        width: 6;
        height: 6;
        color: #2dd4bf;
        text-style: bold;
        content-align: center middle;
    }

    #runtime-summary {
        height: 1;
        color: #8b96a8;
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

    .hidden {
        display: none;
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
        min-width: 10;
        height: 3;
        margin-right: 1;
        text-style: bold;
        background: #111722;
        color: #d7dde7;
        border: tall #171d28;
    }

    .control-button {
        width: 1fr;
        min-width: 10;
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
    #run-toggle {
        background: #111722;
        color: #5eead4;
        border: tall #2dd4bf;
    }

    #save:hover,
    #run-toggle:hover {
        background: #123b38;
        color: #e6fffb;
        border: tall #5eead4;
    }

    #run-toggle.running {
        color: #fb7185;
        border: tall #7f1d35;
    }

    #run-toggle.running:hover {
        background: #24151d;
        color: #fb7185;
        border: tall #7f1d35;
    }

    #exit {
        background: #111722;
        color: #cbd5e1;
        border: tall #171d28;
    }

    #exit:hover {
        background: #24151d;
        color: #fb7185;
        border: tall #7f1d35;
    }

    Button:focus {
        border: tall #2dd4bf;
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
        height: 1;
        margin-bottom: 0;
        padding: 0;
        background: #111722;
        color: #cbd5e1;
        content-align: left middle;
    }

    #log {
        height: 1fr;
        padding: 1;
        background: #0d1118;
        color: #b8c2d2;
        border: tall #151d2a;
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
            self.set_main_status("Running\nStop forwarding before editing settings.")
            return

        self.push_screen(SetupScreen(self.config_values, can_go_back=True))

    def start_bot(self):
        if self.bot_thread is not None and self.bot_thread.is_alive():
            return

        if self.bot_config is None:
            self.set_main_status("Missing config\nOpen Settings and save config.json.")
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
            "Running\n"
            f"t.me/{self.bot_config.tg_announcement_channel}\n"
            f"Every {self.bot_config.check_interval_seconds:g}s"
        )
        self.refresh_main_screen()

    def stop_bot(self):
        if self.stop_event is None:
            return

        self.stop_event.set()
        self.set_main_status("Stopping...")
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
                self.set_main_status("Stopped")
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


def print_headless_log(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def get_headless_run_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve()), "--headless", "run"]

    return [sys.executable, str(Path(__file__).resolve()), "--headless", "run"]


def read_headless_pid() -> int | None:
    pid_path = get_headless_pid_path()
    if not pid_path.exists():
        return None

    try:
        pid_text = pid_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise CustomError(f"[{pid_path.name}] Cannot read pid file: {error}") from error

    try:
        return int(pid_text)
    except ValueError as error:
        raise CustomError(f"[{pid_path.name}] Invalid pid file.") from error


def remove_headless_pid():
    pid_path = get_headless_pid_path()
    try:
        pid_path.unlink()
    except FileNotFoundError:
        return


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    return True


def validate_headless_config() -> None:
    config_values = load_config_values()
    BotConfig.from_values(config_values)


def run_headless_foreground() -> int:
    try:
        config_values = load_config_values()
        bot_config = BotConfig.from_values(config_values)
    except CustomError as error:
        print(str(error), file=sys.stderr)
        return 1

    stop_event = threading.Event()

    def stop_from_signal(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, stop_from_signal)
    signal.signal(signal.SIGTERM, stop_from_signal)

    bot = TelegramDiscordBot(bot_config, print_headless_log)
    bot.run(stop_event)
    return 0


def start_headless() -> int:
    try:
        existing_pid = read_headless_pid()
    except CustomError as error:
        print(str(error), file=sys.stderr)
        return 1

    if existing_pid is not None:
        if is_process_running(existing_pid):
            print(f"Headless bot is already running. PID: {existing_pid}")
            return 0
        remove_headless_pid()

    try:
        validate_headless_config()
    except CustomError as error:
        print(str(error), file=sys.stderr)
        return 1

    log_path = get_headless_log_path()
    try:
        with log_path.open("ab") as log_file:
            process = subprocess.Popen(
                get_headless_run_command(),
                cwd=str(get_app_dir()),
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                close_fds=True,
                start_new_session=True,
            )
    except OSError as error:
        print(
            f"[headless] Cannot start background process: {error}",
            file=sys.stderr,
        )
        return 1

    pid_path = get_headless_pid_path()
    try:
        pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    except OSError as error:
        os.kill(process.pid, signal.SIGTERM)
        print(f"[headless] Cannot write {pid_path}: {error}", file=sys.stderr)
        return 1

    print(f"Started headless bot. PID: {process.pid}")
    print(f"Log: {log_path}")
    return 0


def stop_headless() -> int:
    try:
        pid = read_headless_pid()
    except CustomError as error:
        print(str(error), file=sys.stderr)
        return 1

    if pid is None:
        print("Headless bot is not running.")
        return 0

    if not is_process_running(pid):
        remove_headless_pid()
        print("Headless bot is not running. Removed stale pid file.")
        return 0

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as error:
        print(f"[headless] Cannot stop PID {pid}: {error}", file=sys.stderr)
        return 1

    deadline = time.monotonic() + HEADLESS_STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not is_process_running(pid):
            remove_headless_pid()
            print(f"Stopped headless bot. PID: {pid}")
            return 0
        time.sleep(0.2)

    print(f"Stop signal sent to PID {pid}, but the process is still running.")
    return 1


def show_headless_status() -> int:
    try:
        pid = read_headless_pid()
    except CustomError as error:
        print(str(error), file=sys.stderr)
        return 1

    if pid is None:
        print("Headless bot is not running.")
        return 0

    if is_process_running(pid):
        print(f"Headless bot is running. PID: {pid}")
        print(f"Log: {get_headless_log_path()}")
        return 0

    print(
        "Headless bot is not running, "
        f"but pid file exists: {get_headless_pid_path()}"
    )
    return 1


def run_headless_command(command: str) -> int:
    if command == "start":
        return start_headless()
    if command == "stop":
        return stop_headless()
    if command == "status":
        return show_headless_status()
    if command == "run":
        return run_headless_foreground()

    raise CustomError(f"[headless] Unknown command: {command}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telegram Discord Bot")
    parser.add_argument(
        "--headless",
        nargs="?",
        choices=("start", "stop", "status", "run"),
        const="start",
        help="Manage the headless background bot. Defaults to start.",
    )
    args = parser.parse_args(argv)

    if args.headless is not None:
        return run_headless_command(args.headless)

    TelegramDiscordTUI().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
