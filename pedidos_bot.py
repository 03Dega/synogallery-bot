import json
import uuid
import os
import shutil

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ================= CONFIG =================

TOKEN = "7716351305:AAE2jegN6vrND8y122xhNPiFPA9oM4K5XhM"
ADMIN_CHAT_ID = 5194160874

ARCHIVO_PEDIDOS = "pedidos.json"

(
    TIPO,
    CATEGORIA,
    PERSONAJE,
    SITUACION,
    DETALLES,
    CONFIRMAR,
) = range(6)

# ================= UTILIDADES =================

def cargar_pedidos():
    try:
        with open(ARCHIVO_PEDIDOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_pedidos(pedidos):
    if os.path.exists(ARCHIVO_PEDIDOS):
        shutil.copy(ARCHIVO_PEDIDOS, ARCHIVO_PEDIDOS + ".bak")

    with open(ARCHIVO_PEDIDOS, "w", encoding="utf-8") as f:
        json.dump(pedidos, f, indent=4, ensure_ascii=False)

# ================= CLIENTE =================

async def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton("🖼 Imagen", callback_data="Imagen"),
            InlineKeyboardButton("🎬 Animación", callback_data="Animación")
        ]
    ]
    await update.message.reply_text(
        "🎨 *Bienvenido*\n\n¿Qué deseas crear?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TIPO

async def tipo_pedido(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["tipo"] = query.data

    keyboard = [
        [
            InlineKeyboardButton("👤 Personaje", callback_data="Personaje"),
            InlineKeyboardButton("🌆 Ilustración", callback_data="Ilustración")
        ]
    ]

    await query.edit_message_text(
        "🧩 ¿Qué tipo de contenido deseas?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CATEGORIA

async def categoria(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["categoria"] = query.data

    if query.data == "Personaje":
        await query.edit_message_text(
            "👤 Escribe el nombre del personaje.\n"
            "Ejemplo: Firefly (Honkai Star Rail)"
        )
        return PERSONAJE
    else:
        context.user_data["personaje"] = "No aplica"
        await query.edit_message_text(
            "🌆 Describe la escena o situación."
        )
        return SITUACION

async def personaje(update, context):
    context.user_data["personaje"] = update.message.text
    await update.message.reply_text(
        "🎭 Describe la escena o situación."
    )
    return SITUACION

async def situacion(update, context):
    context.user_data["situacion"] = update.message.text
    await update.message.reply_text(
        "✨ Detalles visuales:\n"
        "- ropa\n"
        "- expresión\n"
        "- cámara\n"
        "- ambiente"
    )
    return DETALLES

async def detalles(update, context):
    context.user_data["detalles"] = update.message.text

    resumen = f"""
📄 *Resumen del pedido*

🎨 Tipo: {context.user_data['tipo']}
🧩 Categoría: {context.user_data['categoria']}
👤 Personaje: {context.user_data['personaje']}
🎭 Escena: {context.user_data['situacion']}
✨ Detalles: {context.user_data['detalles']}
"""

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

    if query.data == "cancelar":
        await query.edit_message_text("❌ Pedido cancelado.")
        context.user_data.clear()
        return ConversationHandler.END

    pedidos = cargar_pedidos()
    pedido_id = str(uuid.uuid4())[:8]

    pedido = {
        "id": pedido_id,
        "tipo": context.user_data["tipo"],
        "categoria": context.user_data["categoria"],
        "personaje": context.user_data["personaje"],
        "situacion": context.user_data["situacion"],
        "detalles": context.user_data["detalles"],
        "cliente": {
            "id": query.from_user.id,
            "username": query.from_user.username,
            "nombre": query.from_user.full_name
        },
        "estado": "pendiente"
    }

    pedidos.append(pedido)
    guardar_pedidos(pedidos)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Entregar pedido", callback_data=f"entregar_{pedido_id}")]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"📥 *Nuevo pedido*\n\n"
            f"🆔 `{pedido_id}`\n"
            f"👤 {pedido['cliente']['nombre']}\n"
            f"🎨 {pedido['tipo']} / {pedido['categoria']}\n"
            f"🎭 {pedido['situacion']}\n\n"
            f"{pedido['detalles']}"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await query.edit_message_text(
        "✅ Pedido registrado.\nTe avisaré cuando esté listo ✨"
    )

    context.user_data.clear()
    return ConversationHandler.END

# ================= ENTREGA ADMIN =================

async def activar_entrega(update, context):
    query = update.callback_query
    await query.answer()

    pedido_id = query.data.replace("entregar_", "")
    context.bot_data["pedido_entrega"] = pedido_id

    await query.edit_message_text(
        "📦 Modo entrega activado.\n"
        "Envía ahora la imagen, video o animación."
    )

async def recibir_entrega(update, context):
    if update.message.chat_id != ADMIN_CHAT_ID:
        return

    pedido_id = context.bot_data.get("pedido_entrega")
    if not pedido_id:
        return

    pedidos = cargar_pedidos()

    for p in pedidos:
        if p["id"] == pedido_id:
            cliente_id = p["cliente"]["id"]

            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=cliente_id,
                    photo=update.message.photo[-1].file_id,
                    caption="🖼 Pedido entregado. ¡Disfrútalo!"
                )

            elif update.message.animation:
                await context.bot.send_animation(
                    chat_id=cliente_id,
                    animation=update.message.animation.file_id,
                    caption="🎬 Pedido entregado. ¡Disfrútalo!"
                )

            elif update.message.video:
                await context.bot.send_video(
                    chat_id=cliente_id,
                    video=update.message.video.file_id,
                    caption="🎬 Pedido entregado. ¡Disfrútalo!"
                )

            p["estado"] = "completado"
            guardar_pedidos(pedidos)
            context.bot_data.pop("pedido_entrega")

            await update.message.reply_text("✅ Entrega enviada al cliente.")
            return

# ================= APP =================

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TIPO: [CallbackQueryHandler(tipo_pedido)],
        CATEGORIA: [CallbackQueryHandler(categoria)],
        PERSONAJE: [MessageHandler(filters.TEXT & ~filters.COMMAND, personaje)],
        SITUACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, situacion)],
        DETALLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, descripcion)],
        CONFIRMAR: [CallbackQueryHandler(confirmar)],
    },
    fallbacks=[CommandHandler("cancelar", start)]
)

app.add_handler(conv)
app.add_handler(CallbackQueryHandler(activar_entrega, pattern="^entregar_"))
app.add_handler(MessageHandler(
    filters.PHOTO | filters.VIDEO | filters.ANIMATION,
    recibir_entrega
))

print("🤖 Bot profesional activo.")
app.run_polling()
