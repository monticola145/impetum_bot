import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from discord.utils import get
import asyncio

# Установка необходимых намерений для бота
intents = discord.Intents.default()
intents.message_content = True  # Необходимо для получения содержимого сообщений
bot = commands.Bot(command_prefix='-', intents=intents)

DISCORD_TOKEN = None # Укажите Ваш discord_token

FFMPEG_PATH = None  # Укажите путь к вашему ffmpeg'у

# Настройки для youtube_dl
YDL_OPTIONS = {
    'format': 'bestaudio',  # Загрузка лучшего аудио формата
    'noplaylist': True,  # Отключение плейлистов
    'quiet': True,  # Отключение вывода сообщений
    'no_warnings': True,  # Отключение предупреждений
    'default_search': 'auto',  # Автоматический поиск видео
    'source_address': '0.0.0.0'  # Использование IPv4
}

# Настройки для ffmpeg
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # Настройки для повторного подключения
    'options': '-vn'  # Отключение видео
}

queue = []  # Очередь треков
current_song = None  # Текущий воспроизводимый трек
bot_messages = []  # Список сообщений бота и пользователя
repeat_mode = 0  # 0 - без повтора, 1 - повтор всей очереди, 2 - повтор текущего трека

@bot.event
async def on_ready():
    """
    Функция, вызываемая при готовности бота.
    """
    print(f'Вошел как {bot.user.name}')  # Вывод сообщения в консоль

async def delete_messages():
    """
    Асинхронно удаляет последние сообщения бота и пользователя.
    """
    for message in bot_messages:  # Проход по всем сообщениям в списке
        try:
            await message.delete()  # Попытка удаления сообщения
        except discord.errors.NotFound:
            pass  # Игнорирование ошибки, если сообщение не найдено
    bot_messages.clear()  # Очистка списка сообщений

async def play_next(ctx: commands.Context) -> None:
    """
    Воспроизводит следующий трек в очереди.
    """
    global current_song, repeat_mode
    #asyncio.create_task(delete_messages())  # Асинхронное удаление сообщений перед воспроизведением нового трека

    if repeat_mode == 2 and current_song:  # Если включен повтор текущего трека
        queue.insert(0, current_song)  # Вставка текущего трека в начало очереди
    elif repeat_mode == 1 and current_song:  # Если включен повтор всей очереди
        queue.append(current_song)  # Добавление текущего трека в конец очереди

    if len(queue) > 0:  # Если в очереди есть треки
        current_song = queue.pop(0)  # Получение следующего трека из очереди
        voice_client = get(bot.voice_clients, guild=ctx.guild)  # Получение голосового клиента
        if voice_client is None:  # Если голосовой клиент не подключен
            voice_channel = ctx.message.author.voice.channel  # Получение голосового канала автора сообщения
            voice_client = await voice_channel.connect()  # Подключение к голосовому каналу

        def after_playing(error):
            """
            Функция, вызываемая после завершения воспроизведения трека.
            """
            if error:
                print(f"Ошибка: {error}")  # Вывод ошибки, если она произошла
            bot.loop.create_task(play_next(ctx))  # Воспроизведение следующего трека

        try:
            print(f"Потоковая передача URL: {current_song['audio_url']}")  # Вывод URL текущего трека
            # Воспроизведение трека с использованием ffmpeg
            voice_client.play(discord.FFmpegPCMAudio(current_song['audio_url'], executable=FFMPEG_PATH, **FFMPEG_OPTIONS), after=after_playing)
            msg = await ctx.send(f"Сейчас играет: {current_song['title']} 🎶")  # Отправка сообщения о текущем треке
            bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
        except discord.errors.ClientException as e:
            msg = await ctx.send(f"Произошла ошибка при попытке воспроизвести аудио: {e}")  # Отправка сообщения об ошибке
            bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
        except Exception as e:
            msg = await ctx.send(f"Неожиданная ошибка: {e}")  # Отправка сообщения о неожиданной ошибке
            bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
    else:
        current_song = None  # Сброс текущего трека
        asyncio.create_task(delete_messages())  # Асинхронное удаление сообщений после завершения всех треков
        voice_client = get(bot.voice_clients, guild=ctx.guild)  # Получение голосового клиента
        if voice_client and voice_client.is_connected():  # Если голосовой клиент подключен
            await voice_client.disconnect()  # Отключение от голосового канала

@bot.command(name='play', help='Команда для воспроизведения музыки с YouTube')
async def play(ctx: commands.Context, url: str) -> None:
    """
    Добавляет трек в очередь и начинает воспроизведение, если очередь пуста.
    """
    bot_messages.append(ctx.message)  # Сохранение сообщения пользователя для последующего удаления
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:  # Использование youtube_dl для извлечения информации о треке
        try:
            info = ydl.extract_info(url, download=False)  # Извлечение информации без загрузки
            audio_url = info['url']  # Получение URL аудио
            title = info['title']  # Получение названия трека
            queue.append({'title': title, 'audio_url': audio_url})  # Добавление трека в очередь
            msg = await ctx.send(f"Добавлено в очередь: {title} 🎵")  # Отправка сообщения о добавлении трека
            bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
            if current_song is None:  # Если нет текущего трека
                await play_next(ctx)  # Начало воспроизведения следующего трека
        except Exception as e:
            msg = await ctx.send(f"Произошла ошибка: {e}")  # Отправка сообщения об ошибке
            bot_messages.append(msg)  # Сохранение сообщения для последующего удаления

@bot.command(name='skip', help='Пропускает текущий трек')
async def skip(ctx: commands.Context) -> None:
    """
    Пропускает текущий воспроизводимый трек и начинает следующий.
    """
    bot_messages.append(ctx.message)  # Сохранение сообщения пользователя для последующего удаления
    voice_client = ctx.message.guild.voice_client  # Получение голосового клиента
    if voice_client.is_playing():  # Если клиент воспроизводит трек
        voice_client.stop()  # Остановка текущего трека
        msg = await ctx.send("Пропущено ⏭")  # Отправка сообщения о пропуске трека
        bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
    else:
        msg = await ctx.send("Сейчас ничего не играет.")  # Отправка сообщения об отсутствии воспроизведения
        bot_messages.append(msg)  # Сохранение сообщения для последующего удаления

@bot.command(name='stop', help='Останавливает воспроизведение и очищает очередь')
async def stop(ctx: commands.Context) -> None:
    """
    Останавливает текущий трек, очищает очередь и отключает бота от голосового канала.
    """
    global queue, current_song
    bot_messages.append(ctx.message)  # Сохранение сообщения пользователя для последующего удаления
    queue = []  # Очистка очереди
    current_song = None  # Сброс текущего трека
    voice_client = ctx.message.guild.voice_client  # Получение голосового клиента
    if voice_client.is_playing():  # Если клиент воспроизводит трек
        voice_client.stop()  # Остановка текущего трека
        msg = await ctx.send("Остановлено ⏹")  # Отправка сообщения об остановке
        bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
    if voice_client.is_connected():  # Если клиент подключен
        await voice_client.disconnect()  # Отключение от голосового канала
    asyncio.create_task(delete_messages())  # Асинхронное удаление сообщений после остановки

@bot.command(name='repeat', help='Управляет режимом повтора')
async def repeat(ctx: commands.Context) -> None:
    """
    Управляет режимом повтора: очередь -> текущий трек -> без повтора.
    """
    global repeat_mode
    bot_messages.append(ctx.message)  # Сохранение сообщения пользователя для последующего удаления
    repeat_mode = (repeat_mode + 1) % 3  # Переключение режима повтора
    if repeat_mode == 0:
        msg = await ctx.send("Повтор отключен ❌")  # Сообщение о отключении повтора
    elif repeat_mode == 1:
        msg = await ctx.send("Повтор всей очереди 🔁")  # Сообщение о повторе всей очереди
    elif repeat_mode == 2:
        msg = await ctx.send("Повтор текущего трека 🔂")  # Сообщение о повторе текущего трека
    bot_messages.append(msg)  # Сохранение сообщения для последующего удаления

@bot.command(name='queue', help='Показывает текущую очередь воспроизведения')
async def show_queue(ctx: commands.Context) -> None:
    """
    Показывает текущую очередь воспроизведения.
    """
    bot_messages.append(ctx.message)  # Сохранение сообщения пользователя для последующего удаления
    if len(queue) == 0:  # Если очередь пуста
        msg = await ctx.send("Очередь пуста.")  # Сообщение о пустой очереди
        bot_messages.append(msg)  # Сохранение сообщения для последующего удаления
    else:
        # Формирование списка треков в очереди
        queue_list = "\n".join([f"{index + 1}. {song['title']}" for index, song in enumerate(queue)])
        msg = await ctx.send(f"Текущая очередь:\n{queue_list}")  # Отправка сообщения с очередью
        bot_messages.append(msg)  # Сохранение сообщения для последующего удаления

bot.run(DISCORD_TOKEN)