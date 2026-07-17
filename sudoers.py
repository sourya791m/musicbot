from pyrogram import filters, types

from Elevenyts import app, db, lang
from Elevenyts.helpers import utils


@app.on_message(filters.command(["addsudo", "delsudo", "rmsudo"]) & app.sudo_filter)
@lang.language()
async def _sudo(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    user = await utils.extract_user(m)
    if not user:
        return await m.reply_text(m.lang["user_not_found"])

    if m.command[0] == "addsudo":
        if user.id in app.sudoers:
            return await m.reply_text(m.lang["sudo_already"].format(user.mention))

        app.sudoers.add(user.id)
        app.sudo_filter.update([user.id])
        await db.add_sudo(user.id)
        await m.reply_text(m.lang["sudo_added"].format(user.mention))
    else:
        if user.id not in app.sudoers:
            return await m.reply_text(m.lang["sudo_not"].format(user.mention))

        app.sudoers.discard(user.id)
        app.sudo_filter.update([])  # Reset filter
        app.sudo_filter.update(app.sudoers)  # Rebuild with remaining users
        await db.del_sudo(user.id)
        await m.reply_text(m.lang["sudo_removed"].format(user.mention))


o_mention = None


@app.on_message(filters.command(["listsudo", "sudolist"]) & app.sudo_filter)
@lang.language()
async def _listsudo(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text(m.lang["sudo_fetching"])

    # Always fetch fresh owner info with ID
    owner_user = await app.get_users(app.owner)
    o_mention = f"{owner_user.mention} ({app.owner})"
    
    txt = m.lang["sudo_owner"].format(o_mention)
    sudoers = await db.get_sudoers()
    
    if sudoers:
        sudo_list = ""
        for user_id in sudoers:
            try:
                user = await app.get_users(user_id)
                sudo_list += f"\n- {user.mention} ({user_id})"
            except:
                # Deleted account or inaccessible user
                sudo_list += f"\n- Deleted Account ({user_id})"
                continue
        
        if sudo_list:
            txt += f"<blockquote><u><b>ꜱᴜᴅᴏ ᴜꜱᴇʀꜱ:</b></u>{sudo_list}\n\n</blockquote>"

    await sent.edit_text(txt)



# ==========================================
# DATABASE-BACKED DYNAMIC API COMMAND
# ==========================================
from Elevenyts import config

@app.on_message(filters.command("setapi") & app.sudo_filter)
async def set_dynamic_api(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if len(m.command) < 2:
        return await m.reply_text("❌ **Usage:** `/setapi https://your-serveo-link.serveousercontent.com`")
    
    new_url = m.command[1].strip().rstrip("/")
    
    try:
        # Save securely into your MongoDB configuration collection
        await db.db.config.update_one(
            {"_id": "youtube_api"}, 
            {"$set": {"url": new_url}}, 
            upsert=True
        )
        
        # Update local memory immediately
        config.YOUTUBE_API_URL = new_url
        
        await m.reply_text(
            f"✅ **API Saved to Database!**\n\n"
            f"**New Endpoint:** `{config.YOUTUBE_API_URL}`\n"
            f"_(Persistent across all bot operations)_"
        )
    except Exception as e:
        await m.reply_text(f"❌ **Database Error:** `{e}`")


# Hook into the boot process to load the URL from MongoDB when the bot spins up
async def load_api_from_db():
    try:
        data = await db.db.config.find_one({"_id": "youtube_api"})
        if data and data.get("url"):
            config.YOUTUBE_API_URL = data["url"]
            print(f"🚀 Loaded dynamic YouTube API URL from Database: {data['url']}")
    except Exception as e:
        print(f"⚠️ Failed to load API URL from database on startup: {e}")

# Run the loader immediately when this module gets imported by the app
import asyncio
try:
    loop = asyncio.get_running_loop()
    loop.create_task(load_api_from_db())
except RuntimeError:
    pass
