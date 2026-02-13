import os
import time
import asyncio
import logging
from mega import Mega
import gdown
from pyrogram import Client, enums
from config import Config
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes

logger = logging.getLogger(__name__)

async def process_mega_link(bot, update, url):
    msg = await update.reply_text("Processing MEGA link...", quote=True)
    try:
        mega = Mega()
        m = mega.login() # Anonymous login

        save_dir = os.path.join(Config.DOWNLOAD_LOCATION, str(update.from_user.id))
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        if "folder" in url or "#F!" in url:
            await msg.edit("Downloading MEGA folder...")
            # For folders, mega.py usually requires iterating nodes.
            # This is complex to implement correctly without proper API usage.
            # We will try to use m.download_url if it supports it, otherwise fail gracefully.
            # Actually, for folders, we need to parse the folder structure.
            # Given the constraints, we might limit to single files or use a library that handles it.
            # But let's try to just download it.
            # If this fails, we will inform the user.
            try:
                loop = asyncio.get_event_loop()
                # mega.py's download_url might not support folder URLs directly.
                # Use a specific folder downloader if available or catch error.
                # A common workaround for MEGA folders in python is using the API to list and download.
                # But for now, let's assume specific handling is needed.
                await msg.edit("MEGA folder download is experimentally supported.")

                # We need to use m.find() or similar?
                # Without complex logic, let's try standard download.
                # If it fails, we abort.
                await msg.edit("MEGA folders are not currently supported due to library limitations. Please use direct file links.")
                return
            except Exception as e:
                logger.error(f"MEGA Folder Error: {e}")
                await msg.edit(f"MEGA Folder Error: {str(e)}")
                return

        await msg.edit("Downloading from MEGA...")

        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, lambda: m.download_url(url, save_dir))

        if not file_path or not os.path.exists(file_path):
            await msg.edit("Download failed.")
            return

        await msg.edit("Uploading to Telegram...")
        await upload_file(bot, update, file_path, msg)

    except Exception as e:
        logger.error(f"MEGA Error: {e}")
        await msg.edit(f"MEGA Error: {str(e)}")

async def process_gdrive_link(bot, update, url):
    msg = await update.reply_text("Processing Google Drive link...", quote=True)
    try:
        save_dir = os.path.join(Config.DOWNLOAD_LOCATION, str(update.from_user.id))
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        await msg.edit("Downloading from Google Drive...")

        loop = asyncio.get_event_loop()

        if "drive.google.com/drive/folders" in url or "drive.google.com/folderview" in url:
             # Download folder
             # gdown.download_folder returns list of files
             output = await loop.run_in_executor(None, lambda: gdown.download_folder(url, output=save_dir, quiet=True, use_cookies=False))

             if not output:
                 await msg.edit("No files found or download failed.")
                 return

             await msg.edit(f"Downloaded {len(output)} files. Uploading...")

             for file_path in output:
                 await upload_file(bot, update, file_path, msg)

             await msg.edit("Folder upload complete.")

        else:
            # Single file
            current_cwd = os.getcwd()
            os.chdir(save_dir)
            try:
                filename = await loop.run_in_executor(None, lambda: gdown.download(url, quiet=True, fuzzy=True))
            finally:
                os.chdir(current_cwd)

            if not filename:
                 await msg.edit("Download failed.")
                 return

            file_path = os.path.join(save_dir, filename)
            await upload_file(bot, update, file_path, msg)

    except Exception as e:
        logger.error(f"Google Drive Error: {e}")
        await msg.edit(f"Google Drive Error: {str(e)}")

async def upload_file(bot, update, file_path, msg):
    try:
        start_time = time.time()
        file_size = os.path.getsize(file_path)
        if file_size > Config.TG_MAX_FILE_SIZE:
             await msg.reply_text(f"File {os.path.basename(file_path)} too large ({humanbytes(file_size)}). Skipping.")
             os.remove(file_path)
             return

        await bot.send_document(
            chat_id=update.chat.id,
            document=file_path,
            caption=os.path.basename(file_path),
            reply_to_message_id=update.id,
            progress=progress_for_pyrogram,
            progress_args=(
                f"Uploading {os.path.basename(file_path)}...",
                msg,
                start_time,
            ),
        )
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        await msg.reply_text(f"Upload Error for {os.path.basename(file_path)}: {str(e)}")
