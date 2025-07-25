from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import asyncio
from datetime import datetime
import logging

# ========== KONFIGURASI ==========
BOT_TOKEN = ''
CHANNEL_ID = 0
GROUP_LINK = ''
ADMIN_IDS = set{}

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE SEDERHANA ==========
user_data = {}
message_to_user = {}
admin_replies = {}

# ========== FUNGSI UTAMA ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler perintah /start"""
    user = update.effective_user
    try:
        await update.message.reply_text(
            f"Hai ASTers! {user.full_name} 👋\n\n"
            "Selamat datang di AST | SPMB Banten 2025\n\n"
            "Silakan kirim bukti persyaratan kamu di sini untuk dapat join di Grup Telegram kami, yang berupa:\n"
            "✅ Screenshot follow Instagram @anaksmatangerang\n"
            "✅ Screenshot membagikan link postingan alur join grup Telegram SPMB ke:\n"
            "- 2 grup kelas atau 2 grup wali murid. Jika tidak ada grup boleh kirim JAPRI ke 6 orang di WA/IG\n"
            "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB\n\n"
            "Berikut adalah link postingan yang perlu kamu sebarkan, lau beri komentar disertakan mention 5 teman di kolom komentar (sesuai ketentuan di atas): https://www.instagram.com/p/DJ4FC7DSKm4/?igsh=MWduN2VmY3B2eGpvOA==\n\n"
            "Kirimkan bukti dalam bentuk foto atau PDF di chat ini. Terima kasih 😊"
        )

        example_message = (
            "Silakan cek panduan lengkap mengenai persyaratan di bawah ini:\n"
            "👉 https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTM1MTE5MTIwMDE2Mjg0?story_media_id=3642957998978679121_2999424744&igsh=MXU5dzBpM20ybGo3Zw=="
        )

        await update.message.reply_text(example_message)

    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan. Silakan coba lagi.")

async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima kiriman peserta"""
    user = update.effective_user
    msg = update.message

    if not msg:
        return

    # Format pesan untuk admin
    admin_msg = (
        f"Peserta Baru\n"
        f"User ID: {user.id}\n"
        f"Display name: {user.full_name}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n\n"
        f"Pesan: {msg.text or msg.caption or '(tanpa teks)'}"
    )

    # Tombol verifikasi
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Lengkap", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("Belum Lengkap", callback_data=f"reject_{user.id}"),
            InlineKeyboardButton("Reply", callback_data=f"reply_{user.id}")
        ]
    ])

    try:
        if msg.media_group_id:
            await handle_media_group(update, context, admin_msg, keyboard)
        elif msg.photo:
            sent = await context.bot.send_photo(
                CHANNEL_ID,
                photo=msg.photo[-1].file_id,
                caption=admin_msg,
                reply_markup=keyboard
            )
            save_mapping(user.id, msg.chat_id, sent.message_id)
        elif msg.document:
            sent = await context.bot.send_document(
                CHANNEL_ID,
                document=msg.document.file_id,
                caption=admin_msg,
                reply_markup=keyboard
            )
            save_mapping(user.id, msg.chat_id, sent.message_id)
        else:
            sent = await context.bot.send_message(
                CHANNEL_ID,
                text=admin_msg,
                reply_markup=keyboard
            )
            save_mapping(user.id, msg.chat_id, sent.message_id)

        await msg.reply_text("Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!")

    except Exception as e:
        logger.error(f"Error in handle_submission: {e}")
        await msg.reply_text("Maaf, terjadi error. Silakan kirim ulang.")

def save_mapping(user_id, chat_id, group_msg_id):
    """Menyimpan mapping pesan"""
    user_data[user_id] = {
        "chat_id": chat_id,
        "group_msg_id": group_msg_id,
        "status": "pending"
    }
    message_to_user[group_msg_id] = user_id

async def handle_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE, caption, keyboard):
    """Handle kiriman album media"""
    msg = update.message
    media_group_id = msg.media_group_id

    if 'media_groups' not in context.user_data:
        context.user_data['media_groups'] = {}

    if media_group_id not in context.user_data['media_groups']:
        context.user_data['media_groups'][media_group_id] = {
            "messages": [],
            "user_id": msg.from_user.id,
            "chat_id": msg.chat_id,
            "caption": caption,
            "keyboard": keyboard
        }
        asyncio.create_task(process_media_group(context, media_group_id))

    context.user_data['media_groups'][media_group_id]["messages"].append(msg)

async def process_media_group(context, media_group_id):
    """Proses album media setelah terkumpul"""
    await asyncio.sleep(3)

    if media_group_id not in context.user_data.get('media_groups', {}):
        return

    media_data = context.user_data['media_groups'].pop(media_group_id)
    media_list = sorted(media_data["messages"], key=lambda m: m.message_id)

    media = [
        InputMediaPhoto(media=m.photo[-1].file_id, caption=media_data["caption"] if i == 0 else "")
        for i, m in enumerate(media_list[:10])
    ]

    try:
        sent_messages = await context.bot.send_media_group(CHANNEL_ID, media=media)
        sent_msg = await context.bot.send_message(
            CHANNEL_ID,
            text=f"Album dari user {media_data['user_id']}",
            reply_markup=media_data["keyboard"]
        )
        save_mapping(media_data["user_id"], media_data["chat_id"], sent_msg.message_id)
    except Exception as e:
        logger.error(f"Error in process_media_group: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Meneruskan balasan admin ke user"""
    if update.effective_chat.id != CHANNEL_ID:
        return

    msg = update.message
    if not msg.reply_to_message:
        return

    replied_id = msg.reply_to_message.message_id
    if replied_id not in message_to_user:
        return

    user_id = message_to_user[replied_id]
    user_info = user_data.get(user_id)

    if not user_info:
        return

    admin_name = msg.from_user.full_name
    reply_content = msg.text or msg.caption or "(pesan media)"
    reply_text = (
        f"📩 Balasan dari Admin:\n\n"
        f"{reply_content}\n\n"
        f"Untuk membalas, kirim pesan baru ke bot di chat ini."
    )

    try:
        if msg.text:
            await context.bot.send_message(user_info["chat_id"], reply_text)
        elif msg.photo:
            await context.bot.send_photo(
                user_info["chat_id"],
                photo=msg.photo[-1].file_id,
                caption=reply_text
            )
        elif msg.document:
            await context.bot.send_document(
                user_info["chat_id"],
                document=msg.document.file_id,
                caption=reply_text
            )

        admin_replies[msg.message_id] = replied_id
    except Exception as e:
        logger.error(f"Gagal mengirim balasan: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tombol inline"""
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    if len(data) != 2:
        return

    action, user_id = data[0], int(data[1])
    user_info = user_data.get(user_id)

    if not user_info:
        return

    try:
        if action == "approve":
            user_info["status"] = "approved"
            await context.bot.send_message(
                user_info["chat_id"],
                f"Terima kasih ASTers! Persyaratan kamu sudah lengkap.\n\n"
                "Silakan klik link berikut untuk bergabung ke Grup Info SPMB Banten 2025:\n"
                f"👉 {GROUP_LINK}\n\n"
                "Sampai jumpa di grup!"
            )

        elif action == "reject":
            user_info["status"] = "rejected"
            await context.bot.send_message(
                user_info["chat_id"],
                "Oops! Sepertinya persyaratan kamu belum lengkap.\n\n"
                "Mohon pastikan kamu telah mengirim persyaratan dalam bentuk foto atau PDF, yang berupa:\n"
                "✅ Screenshot follow akun Instagram @anaksmatangerang\n"
                "✅ Screenshot membagikan link postingan alur join grup Telegram SPMB (lihat postingan yang dipin paling atas) ke:\n"
                "- 2 grup kelas atau 2 grup wali murid. Jika tidak ada grup boleh kirim JAPRI ke-6 orang di WA/IG\n"
                "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB (lihat di postingan yang dipin paling atas)\n\n"
                "Silakan kirim ulang bukti kamu jika ada yang terlewat ya. Terima kasih 😊"
            )

        elif action == "reply":
            await query.message.reply_text(
                f"Silakan reply pesan ini untuk mengirim pesan ke user {user_id}",
                reply_to_message_id=query.message.message_id
            )

    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    error = context.error
    logger.error(f"Error: {error}", exc_info=True)

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text("Terjadi kesalahan. Silakan coba lagi.")
        except:
            pass

# ========== JALANKAN BOT ==========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registrasi handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.ALL | filters.TEXT),
        handle_submission
    ))
    app.add_handler(MessageHandler(
        filters.Chat(CHANNEL_ID) & filters.REPLY,
        handle_admin_reply
    ))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot sedang berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
