import asyncio
import os
import subprocess
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
import whisper
from gtts import gTTS

# Инициализация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не задан!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загружаем модель Whisper (base ~150MB)
model = whisper.load_model("base")

print("✅ Бот запущен! Модель Whisper загружена.")

@dp.message()
async def handle_message(message: types.Message):
    """Обработчик всех сообщений"""

    # Если голосовое сообщение - распознаем
    if message.voice or message.audio:
        await handle_voice(message)
        return

    # Обычный текст
    user_text = message.text
    if not user_text:
        return

    print(f"📨 Сообщение от {message.from_user.username}: {user_text}")

    # Генерируем ответ (здесь можно добавить AI логику)
    response_text = f"Привет! Я получил: {user_text}"

    # Отправляем голосовым
    await send_voice_response(message, response_text)

async def handle_voice(message: types.Message):
    """Распознавание голосового сообщения"""

    voice = message.voice or message.audio
    voice_file = await bot.get_file(voice.file_id)

    tmp_ogg = tempfile.mktemp(suffix=".ogg")
    tmp_wav = tmp_ogg.replace(".ogg", ".wav")

    try:
        await bot.download_file(voice_file.file_path, tmp_ogg)

        # Конвертируем OGG → WAV для Whisper
        result = subprocess.run(
            ["ffmpeg", "-i", tmp_ogg, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp_wav, "-y"],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr.decode()}")
            await message.reply("❌ Ошибка конвертации аудио")
            return

        # Распознаём речь
        transcription = model.transcribe(tmp_wav, language="ru")
        recognized_text = transcription["text"]

        await message.reply(f"🎙️ Распознано: {recognized_text}")

        # Голосовой ответ
        await send_voice_response(message, f"Вы сказали: {recognized_text}")

    except Exception as e:
        print(f"Voice error: {e}")
        await message.reply(f"❌ Ошибка распознавания: {str(e)}")
    finally:
        for f in (tmp_ogg, tmp_wav):
            if os.path.exists(f):
                os.unlink(f)

async def send_voice_response(message: types.Message, text: str):
    """Отправка голосового ответа в формате OGG Opus"""

    tmp_mp3 = None
    tmp_ogg = None
    try:
        tmp_mp3 = tempfile.mktemp(suffix=".mp3")
        text_short = text[:500] if len(text) > 500 else text

        tts = gTTS(text=text_short, lang='ru')
        tts.save(tmp_mp3)

        # MP3 → OGG Opus (Telegram требует этот формат для голосовых)
        tmp_ogg = tmp_mp3.replace(".mp3", ".ogg")
        result = subprocess.run(
            ["ffmpeg", "-i", tmp_mp3, "-c:a", "libopus", "-b:a", "64k", tmp_ogg, "-y"],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"TTS ffmpeg error: {result.stderr.decode()}")
            await message.reply(f"📝 {text}")
            return

        await message.answer_voice(voice=FSInputFile(tmp_ogg))

    except Exception as e:
        await message.reply(f"📝 {text}")
        print(f"TTS ошибка: {e}")
    finally:
        for f in (tmp_mp3, tmp_ogg):
            if f and os.path.exists(f):
                os.unlink(f)

async def main():
    print("🤖 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
