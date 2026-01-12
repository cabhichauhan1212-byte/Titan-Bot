import asyncio
import os
import re
import json
import shutil
import time
import nest_asyncio
from pyrogram import Client, errors
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- ⚙️ USER DETAILS ---
API_ID = 33489674
API_HASH = "0950dc93523305a7d0044d45a4c501f2"
SESSION_STRING = "BQH_AwoAHhwDQGM2cGMDO5zn4Enp6Z5Jv5paWOe9E5ILV7S_ofepRsDJBgwGJ9K6qxhku-ucHHhUU2usN7W70c47LFZyUll3hxYeBZueztx83bW8kD2o2ltAuEiIuA4KuQiuMK1bte-DuZrWcvuRsSO8znwHRajySfbZ5jE66YsCJFasQZNI8oZDPAMxK_TcNQxj2ezIdlLdSGBqfFJNxoSvmvGqAn39qbmHUM2y0vEdzTOpHUwTOVamYgmcGhfmjIErZDcD_YixYB7ZOsuKv6cFCZ7rogJY12z1Qvrx0b4Fb9OLNFWR0VCK1ZyTTFJJo7x2zcNK5-8bgx1qk1CtOejWaOxvhAAAAAF-aFGyAA"
BOT_TOKEN = "8498829182:AAFOLglbMn797Q7sKHAsQlktN_aKhcIq0Tc"

# --- 📂 SETTINGS ---
STATE_FILE = "titan_state.json"
RAM_DIR = "downloads"

# Default State
state = {
    "running": False,
    "source": -1003173842375,
    "dest": -1003273347831,
    "current": 68973,
    "copied": 0,
    "status": "Idle"
}

# --- 🛠️ HELPER FUNCTIONS ---
def save_state():
    with open(STATE_FILE, "w") as f: json.dump(state, f)

def load_state():
    global state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                saved = json.load(f)
                state.update(saved)
        except: pass

def clean_caption(text):
    if not text: return None
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    BAD_PATTERNS = [r"(?i)extracted by\s?.*", r"(?i)leaked by\s?.*", r"(?i)Join\s?:.*", r"(?i)t\.me/[\w_]+", r"@\S+"]
    for p in BAD_PATTERNS: text = re.sub(p, "", text)
    return text.strip()

# --- ⚡ TITAN ENGINE ---
async def engine():
    global state
    
    if os.path.exists(RAM_DIR): shutil.rmtree(RAM_DIR)
    os.makedirs(RAM_DIR)

    client = Client("titan_bot_client", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)
    await client.start()
    
    # --- 🛡️ FIX: STARTUP SCANNER ---
    print("🔄 Refreshing Channel List...")
    found_source = False
    try:
        async for dialog in client.get_dialogs():
            if dialog.chat.id == state["source"]:
                print(f"✅ FOUND SOURCE: {dialog.chat.title}")
                found_source = True
                break
    except Exception as e:
        print(f"⚠️ Scanner Error: {e}")

    if not found_source:
        print(f"❌ WARNING: Source ID {state['source']} nahi mila! ID check karo.")
    else:
        print("✅ Titan Ready!")

    # --------------------------------

    while True:
        if not state["running"]:
            state["status"] = "Paused ⏸"
            await asyncio.sleep(2)
            continue

        state["status"] = f"Processing ID: {state['current']} 🔄"
        current_id = state["current"]

        try:
            try:
                msg = await client.get_messages(state["source"], current_id)
            except errors.PeerIdInvalid:
                print("⚠️ Peer Invalid. Retrying...")
                await asyncio.sleep(2)
                # Force refresh peer
                await client.resolve_peer(state["source"])
                msg = await client.get_messages(state["source"], current_id)

            if not msg or msg.empty or msg.service:
                print(f"⏩ Skipping {current_id}")
                state["current"] += 1
                save_state()
                continue

            caption = clean_caption(msg.caption or msg.text or "")

            if msg.text:
                await client.send_message(state["dest"], caption)
            else:
                try:
                    await msg.copy(state["dest"], caption=caption)
                except:
                    dl_path = os.path.join(RAM_DIR, str(current_id))
                    file = await client.download_media(msg, file_name=dl_path)
                    
                    if msg.video: await client.send_video(state["dest"], file, caption=caption, supports_streaming=True)
                    elif msg.document: await client.send_document(state["dest"], file, caption=caption)
                    elif msg.photo: await client.send_photo(state["dest"], file, caption=caption)
                    elif msg.audio: await client.send_audio(state["dest"], file, caption=caption)
                    
                    if os.path.exists(file): os.remove(file)

            state["copied"] += 1
            state["current"] += 1
            save_state()
            await asyncio.sleep(1)

        except errors.FloodWait as e:
            state["status"] = f"FloodWait: {e.value}s ⏳"
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"❌ Error ID {current_id}: {e}")
            await asyncio.sleep(2)

# --- 🎮 TELEGRAM BOT ---
async def start_command(update: Update, ctx):
    await update.message.reply_text("🤖 Titan Ready!\nUse: /run, /pause, /setid")

async def run_bot(update: Update, ctx):
    state["running"] = True
    save_state()
    await update.message.reply_text("🚀 Started!")

async def pause_bot(update: Update, ctx):
    state["running"] = False
    save_state()
    await update.message.reply_text("⏸ Paused.")

async def set_id(update: Update, ctx):
    try:
        state["current"] = int(ctx.args[0])
        save_state()
        await update.message.reply_text(f"🎯 ID Set: {state['current']}")
    except: await update.message.reply_text("❌ Use: /setid 100")

async def status_command(update: Update, ctx):
    await update.message.reply_text(f"📊 Status: {state['status']}\nID: {state['current']}")

if __name__ == "__main__":
    nest_asyncio.apply()
    load_state()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("run", run_bot))
    app.add_handler(CommandHandler("pause", pause_bot))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("setid", set_id))

    loop = asyncio.get_event_loop()
    loop.create_task(engine())

    print("🤖 Bot Started...")
    app.run_polling()
      
