import json
import uuid
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "7749398970:AAEdLAkwzZKKZUREQrgPm5giQKq-xp4UJhk"
ADMIN_CHAT_ID = 5194160874
ARCHIVO_PEDIDOS = "pedidos.json"

TIPO, DETALLES, CONFIRMAR = range(3)

# ------------------ UTILIDADES ------------------

def cargar_pedidos():
    try:
        with open(ARCHIVO_PEDIDOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_pedidos(pedidos):
    with open(ARCHIVO_PEDIDOS, "w", encoding="utf-8") as f:
        json.dump(pedidos, f, indent=4, ensure_ascii=False)

# ------------------ FLUJO CLIENTE ------------------

async def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton("🖼 Imagen", callback_data="Imagen"),
            InlineKeyboardButton("🎬 Animación", callback_data="Animación")
        ]
    ]

    await update.message.reply_text(
        "Bienvenido.\n\n"
        "Seleccione el tipo de pedido:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TIPO

async def tipo_pedido(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["tipo"] = query.data

    await query.edit_message_text(
        "Por favor, describa los detalles del pedido."
    )
    return DETALLES

async def detalles(update, context):
    context.user_data["detalles"] = update.message.text

    resumen = (
        "📄 *Resumen del pedido*\n\n"
        f"{context.user_data['detalles']}\n\n"
        "Su pedido estará listo en el menor tiempo posible.\n\n"
        "¿Desea confirmar?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
        ]
    ]

    await update.message.reply_text(
        resumen,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMAR

async def confirmar(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "confirmar":
        pedidos = cargar_pedidos()

        pedido_id = str(uuid.uuid4())[:8]

        pedido = {
            "id": pedido_id,
            "tipo": context.user_data["tipo"],
            "detalles": context.user_data["detalles"],
            "cliente_chat_id": query.from_user.id,
            "estado": "pendiente"
        }

        pedidos.append(pedido)
        guardar_pedidos(pedidos)

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"📥 *Nuevo pedido*\n"
                f"ID: `{pedido_id}`\n\n"
                f"{pedido['detalles']}"
            ),
            parse_mode="Markdown"
        )

        await query.edit_message_text(
            "✅ Pedido registrado correctamente.\n"
            "Su pedido estará listo en el menor tiempo posible."
        )

    else:
        await query.edit_message_text("❌ Pedido cancelado.")

    context.user_data.clear()
    return ConversationHandler.END

# ------------------ ADMIN ------------------

async def pedidos(update, context):
    if update.message.chat_id != ADMIN_CHAT_ID:
        return

    pedidos = cargar_pedidos()
    pendientes = [p for p in pedidos if p["estado"] == "pendiente"]

    if not pendientes:
        await update.message.reply_text("No hay pedidos pendientes.")
        return

    texto = "📋 *Pedidos pendientes:*\n\n"
    for p in pendientes:
        texto += f"• ID: `{p['id']}`\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

async def completar(update, context):
    if update.message.chat_id != ADMIN_CHAT_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Uso: /completar ID")
        return

    pedido_id = context.args[0]
    pedidos = cargar_pedidos()

    for p in pedidos:
        if p["id"] == pedido_id and p["estado"] == "pendiente":
            p["estado"] = "completado"
            guardar_pedidos(pedidos)

            await context.bot.send_message(
                chat_id=p["cliente_chat_id"],
                text=(
                    "✅ Su pedido ha sido completado.\n\n"
                    "Gracias por su confianza."
                )
            )

            await update.message.reply_text("Pedido marcado como completado.")
            return

    await update.message.reply_text("Pedido no encontrado.")

# ------------------ APP ------------------

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TIPO: [CallbackQueryHandler(tipo_pedido)],
        DETALLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, detalles)],
        CONFIRMAR: [CallbackQueryHandler(confirmar)],
    },
    fallbacks=[],
)

app.add_handler(conv)
app.add_handler(CommandHandler("pedidos", pedidos))
app.add_handler(CommandHandler("completar", completar))

print("🤖 Bot profesional activo.")
app.run_polling()
