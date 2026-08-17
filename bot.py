import os
import re
from collections import defaultdict

from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

# تخزين التحذيرات مؤقتًا
warnings = defaultdict(int)

# الجروبات التي تم تفعيل منع الروابط فيها
antilink_enabled = set()

# قوانين افتراضية
rules_text = "📌 ممنوع السبام والروابط المزعجة والإساءة داخل المجموعة."


def is_admin(update: Update) -> bool:
    member = update.effective_chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")


async def admin_only(update: Update) -> bool:
    if not await is_admin(update):
        await update.message.reply_text("❌ الأمر ده للمشرفين فقط.")
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ أهلاً بيك في بوت الحماية!\n\n"
        "اكتبي /help لمعرفة الأوامر."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ أوامر بوت الحماية:\n\n"
        "/ban — حظر عضو\n"
        "/unban — فك الحظر\n"
        "/mute — كتم عضو\n"
        "/unmute — فك الكتم\n"
        "/kick — طرد عضو\n"
        "/warn — تحذير عضو\n"
        "/warnings — معرفة التحذيرات\n"
        "/antilink — تشغيل/إيقاف منع الروابط\n"
        "/rules — عرض القوانين\n"
        "/id — معرفة الـ ID\n"
    )


def get_target(update: Update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    if context_args := update.message.text.split()[1:]:
        return None

    return None


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ اعملي Reply على رسالة العضو واكتبي /ban")
        return

    user = update.message.reply_to_message.from_user

    await update.effective_chat.ban_member(user.id)

    await update.message.reply_text(
        f"🚫 تم حظر {user.mention_html()}",
        parse_mode="HTML"
    )


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if not context.args:
        await update.message.reply_text(
            "استخدمي:\n/unban USER_ID"
        )
        return

    try:
        user_id = int(context.args[0])
        await update.effective_chat.unban_member(user_id)
        await update.message.reply_text("✅ تم فك الحظر.")
    except Exception:
        await update.message.reply_text("❌ حصل خطأ في فك الحظر.")


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ اعملي Reply على رسالة العضو واكتبي /mute")
        return

    user = update.message.reply_to_message.from_user

    permissions = ChatPermissions(can_send_messages=False)

    await update.effective_chat.restrict_member(
        user.id,
        permissions=permissions
    )

    await update.message.reply_text(
        f"🔇 تم كتم {user.mention_html()}",
        parse_mode="HTML"
    )


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ اعملي Reply على رسالة العضو واكتبي /unmute")
        return

    user = update.message.reply_to_message.from_user

    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )

    await update.effective_chat.restrict_member(
        user.id,
        permissions=permissions
    )

    await update.message.reply_text(
        f"🔊 تم فك الكتم عن {user.mention_html()}",
        parse_mode="HTML"
    )


async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ اعملي Reply على رسالة العضو واكتبي /kick")
        return

    user = update.message.reply_to_message.from_user

    await update.effective_chat.ban_member(user.id)
    await update.effective_chat.unban_member(user.id)

    await update.message.reply_text("👢 تم طرد العضو.")


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ اعملي Reply على رسالة العضو واكتبي /warn")
        return

    user = update.message.reply_to_message.from_user
    key = (update.effective_chat.id, user.id)

    warnings[key] += 1
    count = warnings[key]

    if count >= 3:
        await update.effective_chat.ban_member(user.id)
        warnings[key] = 0

        await update.message.reply_text(
            f"🚫 العضو وصل لـ 3 تحذيرات وتم حظره."
        )
    else:
        await update.message.reply_text(
            f"⚠️ تم تحذير {user.first_name}\n"
            f"عدد التحذيرات: {count}/3"
        )


async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "↩️ اعملي Reply على رسالة العضو واكتبي /warnings"
        )
        return

    user = update.message.reply_to_message.from_user
    key = (update.effective_chat.id, user.id)

    await update.message.reply_text(
        f"⚠️ تحذيرات {user.first_name}: {warnings[key]}/3"
    )


async def antilink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    chat_id = update.effective_chat.id

    if context.args and context.args[0].lower() == "off":
        antilink_enabled.discard(chat_id)
        await update.message.reply_text("🔓 تم إيقاف منع الروابط.")
    else:
        antilink_enabled.add(chat_id)
        await update.message.reply_text("🔒 تم تشغيل منع الروابط.")


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📜 قوانين المجموعة:\n\n{rules_text}"
    )


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        await update.message.reply_text(
            f"🆔 ID: {user.id}"
        )
    else:
        await update.message.reply_text(
            f"🆔 ID بتاعك: {update.effective_user.id}"
        )


async def link_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id

    if chat_id not in antilink_enabled:
        return

    if re.search(r"(https?://|www\.|t\.me/)", update.message.text.lower()):
        user = update.message.from_user

        # المشرفين مسموح لهم بالروابط
        member = await update.effective_chat.get_member(user.id)

        if member.status in ("administrator", "creator"):
            return

        try:
            await update.message.delete()
        except Exception:
            pass


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warnings", warnings_command))
    app.add_handler(CommandHandler("antilink", antilink))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("id", user_id))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            link_protection
        )
    )

    print("🛡️ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()