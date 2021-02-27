import asyncio
import hashlib
import inspect
import math
import os
import logging
from collections import defaultdict
from typing import (AsyncGenerator, Awaitable, BinaryIO, DefaultDict, List,
                    Optional, Tuple, Union)

from telethon import TelegramClient, helpers, utils
from telethon.crypto import AuthKey
from telethon.network import MTProtoSender
from telethon.tl.functions.auth import (ExportAuthorizationRequest,
                                        ImportAuthorizationRequest)
from telethon.tl.functions.upload import (GetFileRequest,
                                          SaveBigFilePartRequest,
                                          SaveFilePartRequest)
from telethon.tl.types import (Document, InputDocumentFileLocation, InputFile,
                               InputFileBig, InputFileLocation,
                               InputPeerPhotoFileLocation,
                               InputPhotoFileLocation, TypeInputFile)

TypeLocation = Union[Document, InputDocumentFileLocation, InputPeerPhotoFileLocation,
                     InputFileLocation, InputPhotoFileLocation]

logger = logging.getLogger(__name__)

def stream_file(file_to_stream: BinaryIO, chunk_size=1024):
    while True:
        data_read = file_to_stream.read(chunk_size)
        if not data_read:
            break
        yield data_read


class DownloadSender:
    sender: MTProtoSender
    request: GetFileRequest
    remaining: int
    stride: int

    def __init__(self, sender: MTProtoSender, file: TypeLocation, offset: int, limit: int,
                 stride: int, count: int) -> None:
        self.sender = sender
        self.request = GetFileRequest(file, offset=offset, limit=limit)
        self.stride = stride
        self.remaining = count

    async def next(self) -> Optional[bytes]:
        if not self.remaining:
            return None
        result = await self.sender.send(self.request)
        self.remaining -= 1
        self.request.offset += self.stride
        return result.bytes

    def disconnect(self) -> Awaitable[None]:
        return self.sender.disconnect()


class UploadSender:
    sender: MTProtoSender
    request: Union[SaveFilePartRequest, SaveBigFilePartRequest]
    part_count: int
    stride: int
    previous: Optional[asyncio.Task]
    loop: asyncio.AbstractEventLoop

    def __init__(self, sender: MTProtoSender, file_id: int, part_count: int, big: bool, index: int,
                 stride: int, loop: asyncio.AbstractEventLoop) -> None:
        self.sender = sender
        self.part_count = part_count
        if big:
            self.request = SaveBigFilePartRequest(file_id, index, part_count, b"")
        else:
            self.request = SaveFilePartRequest(file_id, index, b"")
        self.stride = stride
        self.previous = None
        self.loop = loop

    async def next(self, data: bytes) -> None:
        if self.previous:
            await self.previous
        self.previous = self.loop.create_task(self._next(data))

    async def _next(self, data: bytes) -> None:
        self.request.bytes = data
        logger.debug(f"Sending file part {self.request.file_part}/{self.part_count}"
                     f" with {len(data)} bytes")
        await self.sender.send(self.request)
        self.request.file_part += self.stride

    async def disconnect(self) -> None:
        if self.previous:
            await self.previous
        return await self.sender.disconnect()


class ParallelTransferrer:
    client: TelegramClient
    loop: asyncio.AbstractEventLoop
    dc_id: int
    senders: Optional[List[Union[DownloadSender, UploadSender]]]
    auth_key: AuthKey
    upload_ticker: int

    def __init__(self, client: TelegramClient, dc_id: Optional[int] = None) -> None:
        self.client = client
        self.loop = self.client.loop
        self.dc_id = dc_id or self.client.session.dc_id
        self.auth_key = (None if dc_id and self.client.session.dc_id != dc_id
                         else self.client.session.auth_key)
        self.senders = None
        self.upload_ticker = 0

    async def _cleanup(self) -> None:
        await asyncio.gather(*[sender.disconnect() for sender in self.senders])
        self.senders = None

    @staticmethod
    def _get_connection_count(file_size: int, max_count: int = 20,
                              full_size: int = 100 * 1024 * 1024) -> int:
        if file_size > full_size:
            return max_count
        return math.ceil((file_size / full_size) * max_count)

    async def _init_download(self, connections: int, file: TypeLocation, part_count: int,
                             part_size: int) -> None:
        minimum, remainder = divmod(part_count, connections)

        def get_part_count() -> int:
            nonlocal remainder
            if remainder > 0:
                remainder -= 1
                return minimum + 1
            return minimum

        # The first cross-DC sender will export+import the authorization, so we always create it
        # before creating any other senders.
        self.senders = [
            await self._create_download_sender(file, 0, part_size, connections * part_size,
                                               get_part_count()),
            *await asyncio.gather(
                *[self._create_download_sender(file, i, part_size, connections * part_size,
                                               get_part_count())
                  for i in range(1, connections)])
        ]

    async def _create_download_sender(self, file: TypeLocation, index: int, part_size: int,
                                      stride: int,
                                      part_count: int) -> DownloadSender:
        return DownloadSender(await self._create_sender(), file, index * part_size, part_size,
                              stride, part_count)

    async def _init_upload(self, connections: int, file_id: int, part_count: int, big: bool
                           ) -> None:
        self.senders = [
            await self._create_upload_sender(file_id, part_count, big, 0, connections),
            *await asyncio.gather(
                *[self._create_upload_sender(file_id, part_count, big, i, connections)
                  for i in range(1, connections)])
        ]

    async def _create_upload_sender(self, file_id: int, part_count: int, big: bool, index: int,
                                    stride: int) -> UploadSender:
        return UploadSender(await self._create_sender(), file_id, part_count, big, index, stride,
                            loop=self.loop)

    async def _create_sender(self) -> MTProtoSender:
        dc = await self.client._get_dc(self.dc_id)
        sender = MTProtoSender(self.auth_key, loggers=self.client._log)
        await sender.connect(self.client._connection(dc.ip_address, dc.port, dc.id,
                                                     loggers=self.client._log,
                                                     proxy=self.client._proxy))
        if not self.auth_key:
            logger.debug(f"Exporting auth to DC {self.dc_id}")
            auth = await self.client(ExportAuthorizationRequest(self.dc_id))
            req = self.client._init_with(ImportAuthorizationRequest(
                id=auth.id, bytes=auth.bytes
            ))
            await sender.send(req)
            self.auth_key = sender.auth_key
        return sender

    async def init_upload(self, file_id: int, file_size: int, part_size_kb: Optional[float] = None,
                          connection_count: Optional[int] = None) -> Tuple[int, int, bool]:
        connection_count = connection_count or self._get_connection_count(file_size)
        logger.debug(f"init_upload count is {connection_count}")
        part_size = (part_size_kb or utils.get_appropriated_part_size(file_size)) * 1024
        part_count = (file_size + part_size - 1) // part_size
        is_large = file_size > 10 * 1024 * 1024
        await self._init_upload(connection_count, file_id, part_count, is_large)
        return part_size, part_count, is_large

    async def upload(self, part: bytes) -> None:
        await self.senders[self.upload_ticker].next(part)
        self.upload_ticker = (self.upload_ticker + 1) % len(self.senders)

    async def finish_upload(self) -> None:
        await self._cleanup()

    async def download(self, file: TypeLocation, file_size: int,
                       part_size_kb: Optional[float] = None,
                       connection_count: Optional[int] = None) -> AsyncGenerator[bytes, None]:
        connection_count = connection_count or self._get_connection_count(file_size)

        part_size = (part_size_kb or utils.get_appropriated_part_size(file_size)) * 1024
        part_count = math.ceil(file_size / part_size)
        logger.debug("Starting parallel download: "
                     f"{connection_count} {part_size} {part_count} {file!s}")
        await self._init_download(connection_count, file, part_count, part_size)

        part = 0
        while part < part_count:
            tasks = []
            for sender in self.senders:
                tasks.append(self.loop.create_task(sender.next()))
            for task in tasks:
                data = await task
                if not data:
                    break
                yield data
                part += 1
                logger.debug(f"Part {part} downloaded")

        logger.debug("Parallel download finished, cleaning up connections")
        await self._cleanup()


parallel_transfer_locks: DefaultDict[int, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())


async def _internal_transfer_to_telegram(client: TelegramClient,
                                         response: BinaryIO,
                                         progress_callback: callable,
                                         file_name: str
                                         ) -> Tuple[TypeInputFile, int]:
    file_id = helpers.generate_random_long()
    file_size = os.path.getsize(response.name)

    hash_md5 = hashlib.md5()
    uploader = ParallelTransferrer(client)
    part_size, part_count, is_large = await uploader.init_upload(file_id, file_size)
    buffer = bytearray()
    for data in stream_file(response):
        if progress_callback:
            r = progress_callback(response.tell(), file_size)
            if inspect.isawaitable(r):
                await r
        if not is_large:
            hash_md5.update(data)
        if len(buffer) == 0 and len(data) == part_size:
            await uploader.upload(data)
            continue
        new_len = len(buffer) + len(data)
        if new_len >= part_size:
            cutoff = part_size - len(buffer)
            buffer.extend(data[:cutoff])
            await uploader.upload(bytes(buffer))
            buffer.clear()
            buffer.extend(data[cutoff:])
        else:
            buffer.extend(data)
    if len(buffer) > 0:
        await uploader.upload(bytes(buffer))
    await uploader.finish_upload()
    if is_large:
        return InputFileBig(file_id, part_count, file_name), file_size
    else:
        return InputFile(file_id, part_count, file_name, hash_md5.hexdigest()), file_size


async def download_file(client: TelegramClient,
                        location: TypeLocation,
                        out: BinaryIO,
                        progress_callback: callable = None
                        ) -> BinaryIO:
    size = location.size
    dc_id, location = utils.get_input_location(location)
    # We lock the transfers because telegram has connection count limits
    downloader = ParallelTransferrer(client, dc_id)
    downloaded = downloader.download(location, size)
    async for x in downloaded:
        out.write(x)
        if progress_callback:
            r = progress_callback(out.tell(), size)
            if inspect.isawaitable(r):
                await r

    return out


async def upload_file(client: TelegramClient,
                      file: BinaryIO,
                      file_name: str,
                      progress_callback: callable = None) -> TypeInputFile:
    res = (await _internal_transfer_to_telegram(client, file, progress_callback, file_name))[0]
    return res

from Luna import tbot as borg
from Luna import TEMP_DOWNLOAD_DIRECTORY as TMP_DOWNLOAD_DIRECTORY
from telethon import events
import json
import math
import os
import re
import shlex
import subprocess
import time
from os.path import basename
from typing import List, Optional, Tuple
import webbrowser
from bs4 import BeautifulSoup
from bs4 import BeautifulSoup as bs
import re
from telethon.tl.types import InputMessagesFilterDocument
import telethon
from telethon import Button, custom, events, functions
from telethon.tl.types import MessageMediaPhoto
from typing import Union
import zipfile
import os
import aiohttp
import requests
from bs4 import BeautifulSoup
import asyncio
import random
import requests
import string
from bs4 import BeautifulSoup
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
import hachoir
import asyncio
import os
from pathlib import Path
from selenium import webdriver
import time
import requests
import shutil
import os
import argparse
from Luna import logging
sedpath = TMP_DOWNLOAD_DIRECTORY
session = aiohttp.ClientSession()
if not os.path.isdir(sedpath):
    os.makedirs(sedpath)

async def fetch_json(link):
    async with session.get(link) as resp:
        return await resp.json()
client = borg
def get_readable_file_size(size_in_bytes: Union[int, float]) -> str:
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f"{round(size_in_bytes, 2)}{SIZE_UNITS[index]}"
    except IndexError:
        return "File too large"


def get_readable_time(secs: float) -> str:
    result = ""
    (days, remainder) = divmod(secs, 86400)
    days = int(days)
    if days != 0:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f"{minutes}m"
    seconds = int(seconds)
    result += f"{seconds}s"
    return result

def time_formatter(milliseconds: int) -> str:
    """Inputs time in milliseconds, to get beautified time,
    as string"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
            ((str(days) + " day(s), ") if days else "")
            + ((str(hours) + " hour(s), ") if hours else "")
            + ((str(minutes) + " minute(s), ") if minutes else "")
            + ((str(seconds) + " second(s), ") if seconds else "")
            + ((str(milliseconds) + " millisecond(s), ") if milliseconds else "")
    )
    return tmp[:-2]

async def runcmd(cmd: str) -> Tuple[str, str, int, int]:
    """ run command in terminal """
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode("utf-8", "replace").strip(),
        stderr.decode("utf-8", "replace").strip(),
        process.returncode,
        process.pid,
    )

def humanbytes(size):
    """Input size in bytes,
    outputs in a human readable format"""
    # https://stackoverflow.com/a/49361727/4723940
    if not size:
        return ""
    # 2 ** 10 = 1024
    power = 2 ** 10
    raised_to_pow = 0
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"


async def progress(current, total, event, start, type_of_ps, file_name=None):
    """Generic progress_callback for uploads and downloads."""
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        if elapsed_time == 0:
            return
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion
        progress_str = "{0}{1} {2}%\n".format(
            "".join(["▰" for i in range(math.floor(percentage / 10))]),
            "".join(["▱" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2),
        )
        tmp = progress_str + "{0} of {1}\nETA: {2}".format(
            humanbytes(current), humanbytes(total), time_formatter(estimated_total_time)
        )
        if file_name:
            try:
                await event.reply(
                    "{}\n**File Name:** `{}`\n{}".format(type_of_ps, file_name, tmp)
                    
                )
            except:
                pass
        else:
            try:
                await event.reply("{}\n{}".format(type_of_ps, tmp))
            except:
                pass


async def convert_to_image(event, borg):
    lmao = await event.get_reply_message()
    if not (
            lmao.gif
            or lmao.audio
            or lmao.voice
            or lmao.video
            or lmao.video_note
            or lmao.photo
            or lmao.sticker
            or lmao.media
    ):
        await event.edit("`Format Not Supported.`")
        return
    else:
        try:
            c_time = time.time()
            downloaded_file_name = await borg.download_media(
                lmao.media,
                sedpath,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, event, c_time, "`Downloading...`")
                ),
            )
        except Exception as e:  # pylint:disable=C0103,W0703
            await event.edit(str(e))
        else:
            j = await event.edit(
                "Downloaded to `{}` successfully.".format(downloaded_file_name)
            )
    if not os.path.exists(downloaded_file_name):
        await event.reply("Download Unsucessfull :(")
        return
    if lmao and lmao.photo:
        lmao_final = downloaded_file_name
    elif lmao.sticker and lmao.sticker.mime_type == "application/x-tgsticker":
        rpath = downloaded_file_name
        image_name20 = os.path.join(sedpath, "SED.png")
        cmd = f"lottie_convert.py --frame 0 -if lottie -of png {downloaded_file_name} {image_name20}"
        stdout, stderr = (await runcmd(cmd))[:2]
        os.remove(rpath)
        lmao_final = image_name20
    elif lmao.sticker and lmao.sticker.mime_type == "image/webp":
        pathofsticker2 = downloaded_file_name
        image_new_path = sedpath + "image.png"
        os.rename(pathofsticker2, image_new_path)
        if not os.path.exists(image_new_path):
            await event.edit("`Wasn't Able To Fetch Shot.`")
            return
        lmao_final = image_new_path
    elif lmao.audio:
        sed_p = downloaded_file_name
        hmmyes = sedpath + "stark.mp3"
        imgpath = sedpath + "starky.jpg"
        os.rename(sed_p, hmmyes)
        await runcmd(f"ffmpeg -i {hmmyes} -filter:v scale=500:500 -an {imgpath}")
        os.remove(sed_p)
        if not os.path.exists(imgpath):
            await event.edit("`Wasn't Able To Fetch Shot.`")
            return
        lmao_final = imgpath
    elif lmao.gif or lmao.video or lmao.video_note:
        sed_p2 = downloaded_file_name
        jpg_file = os.path.join(sedpath, "image.jpg")
        await take_screen_shot(sed_p2, 0, jpg_file)
        os.remove(sed_p2)
        if not os.path.exists(jpg_file):
            await event.edit("`Couldn't Fetch. SS`")
            return
        lmao_final = jpg_file
    await event.edit("`Almost Completed.`")
    await j.delete()
    return lmao_final
