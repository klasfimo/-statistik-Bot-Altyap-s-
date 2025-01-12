import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import datetime
from database import Database
import io
import asyncio

# .env dosyasını yükle
load_dotenv()

# Bot yapılandırması
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True
intents.reactions = True
intents.emojis = True

# Prefix'i .env dosyasından al
bot = commands.Bot(command_prefix=os.getenv('BOT_PREFIX', '!'), intents=intents)
db = Database()

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    await db.setup()
    check_weekly_reset.start()

@tasks.loop(minutes=30)  # Her 30 dakikada bir kontrol et
async def check_weekly_reset():
    """Haftalık periyodu kontrol et ve güncelle"""
    await db.update_weekly_period()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Mesaj istatistiklerini kaydet
    await db.log_message(
        user_id=message.author.id,
        channel_id=message.channel.id,
        guild_id=message.guild.id,
        timestamp=datetime.datetime.now()
    )

    # Kalıcı istatistikleri güncelle
    await db.update_permanent_stats(
        user_id=message.author.id,
        guild_id=message.guild.id,
        messages=1
    )

    # XP ve seviye sistemi
    leveled_up, new_level = await db.update_user_xp(
        user_id=message.author.id,
        guild_id=message.guild.id
    )

    if leveled_up:
        await message.channel.send(
            f"🎉 Tebrikler {message.author.mention}! Seviye {new_level}'e ulaştın!"
        )

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    # Sesli kanal değişikliklerini izle
    if before.channel != after.channel:
        if after.channel:
            # Sesli kanala katılma
            await db.log_voice_join(
                user_id=member.id,
                channel_id=after.channel.id,
                guild_id=member.guild.id,
                timestamp=datetime.datetime.now()
            )
        elif before.channel:
            # Sesli kanaldan ayrılma
            await db.log_voice_leave(
                user_id=member.id,
                channel_id=before.channel.id,
                guild_id=member.guild.id,
                timestamp=datetime.datetime.now()
            )
            
            # Kalıcı istatistikleri güncelle (sesli kanal süresi)
            voice_time = await db.get_user_voice_time(member.id, member.guild.id)
            await db.update_permanent_stats(
                user_id=member.id,
                guild_id=member.guild.id,
                voice_minutes=voice_time
            )

@bot.event
async def on_reaction_add(reaction, user):
    """Emoji kullanımını takip et"""
    if user.bot:
        return

    emoji_id = str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else None
    emoji_name = str(reaction.emoji)
    
    await db.log_emoji_usage(
        user_id=user.id,
        guild_id=reaction.message.guild.id,
        emoji_id=emoji_id,
        emoji_name=emoji_name
    )

@bot.event
async def on_member_update(before, after):
    """Rol değişikliklerini takip et"""
    # Eklenen roller
    for role in after.roles:
        if role not in before.roles:
            await db.log_role_change(
                user_id=after.id,
                guild_id=after.guild.id,
                role_id=role.id,
                action="add"
            )
    
    # Çıkarılan roller
    for role in before.roles:
        if role not in after.roles:
            await db.log_role_change(
                user_id=after.id,
                guild_id=after.guild.id,
                role_id=role.id,
                action="remove"
            )

def is_owner():
    """Sunucu sahibi kontrolü için decorator"""
    async def predicate(ctx):
        return ctx.author.id == ctx.guild.owner_id
    return commands.check(predicate)

@bot.command(name='ayarlar')
@is_owner()
async def settings(ctx):
    """Sunucu ayarları menüsü (Sadece sunucu sahibi kullanabilir)"""
    embed = discord.Embed(
        title="⚙️ Sunucu Ayarları",
        description="Sunucu ayarlarını yapılandırın",
        color=discord.Color.blue()
    )
    
    # XP Oranı
    current_xp_rate = await db.get_xp_rate(ctx.guild.id)
    embed.add_field(
        name="📊 XP Ayarları",
        value=f"Mevcut XP Oranı: {current_xp_rate} XP/mesaj\n"
              f"Değiştirmek için: `!xp-ayarla <miktar>`",
        inline=False
    )
    
    # İstatistik Sıfırlama
    embed.add_field(
        name="🗑️ İstatistik Sıfırlama",
        value="Kullanıcı: `!stats-sifirla @kullanıcı`\n"
              "Haftalık: `!haftalik-sifirla`\n"
              "Aylık: `!aylik-sifirla`",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='xp-ayarla')
@is_owner()
async def set_xp_rate(ctx, amount: float):
    """XP kazanma oranını ayarla (Sadece sunucu sahibi kullanabilir)"""
    if amount < 0.1 or amount > 100:
        await ctx.send("❌ XP miktarı 0.1 ile 100 arasında olmalıdır!")
        return
    
    await db.update_xp_rate(ctx.guild.id, amount)
    await ctx.send(f"✅ Mesaj başına kazanılan XP miktarı {amount:.2f} olarak ayarlandı!")

@bot.command(name='stats-sifirla')
@is_owner()
async def reset_user_stats(ctx, member: discord.Member):
    """Kullanıcı istatistiklerini sıfırla (Sadece sunucu sahibi kullanabilir)"""
    await db.reset_user_stats(member.id, ctx.guild.id)
    await ctx.send(f"✅ {member.mention} kullanıcısının tüm istatistikleri sıfırlandı!")

@bot.command(name='haftalik-sifirla')
@is_owner()
async def reset_weekly(ctx):
    """Haftalık istatistikleri sıfırla (Sadece sunucu sahibi kullanabilir)"""
    await db.reset_period_stats(ctx.guild.id, 'haftalık')
    await ctx.send("✅ Haftalık istatistikler sıfırlandı!")

@bot.command(name='aylik-sifirla')
@is_owner()
async def reset_monthly(ctx):
    """Aylık istatistikleri sıfırla (Sadece sunucu sahibi kullanabilir)"""
    await db.reset_period_stats(ctx.guild.id, 'aylık')
    await ctx.send("✅ Aylık istatistikler sıfırlandı!")

@bot.command(name='kullanıcı')
async def user_stats(ctx, member: discord.Member = None):
    """Kullanıcı profilini gösterir"""
    if member is None:
        member = ctx.author

    # Ana profil embed'i
    profile_embed = discord.Embed(
        title=f"👤 {member.name} Profili",
        color=member.color
    )
    
    # Kullanıcı bilgileri
    profile_embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    profile_embed.add_field(
        name="🎮 Kullanıcı Bilgileri",
        value=f"🆔 ID: {member.id}\n"
              f"📅 Katılma: {member.joined_at.strftime('%d.%m.%Y')}\n"
              f"📝 Hesap: {member.created_at.strftime('%d.%m.%Y')}",
        inline=False
    )
    
    # İstatistikler
    message_count = await db.get_user_message_count(member.id, ctx.guild.id)
    voice_time = await db.get_user_voice_time(member.id, ctx.guild.id)
    xp, level = await db.get_user_level(member.id, ctx.guild.id)
    
    # Mesaj ve ses istatistikleri
    profile_embed.add_field(
        name="📊 İstatistikler",
        value=f"💬 Mesajlar: {message_count}\n"
              f"🎤 Ses Süresi: {voice_time//60}s {voice_time%60}d\n"
              f"⭐ Seviye: {level} ({xp} XP)",
        inline=False
    )
    
    # Roller
    roles = [role.mention for role in reversed(member.roles[1:])]  # @everyone hariç
    if roles:
        profile_embed.add_field(
            name=f"👥 Roller ({len(roles)})",
            value=" ".join(roles) if len(roles) <= 10 else " ".join(roles[:10]) + f" ...ve {len(roles)-10} daha",
            inline=False
        )
    
    await ctx.send(embed=profile_embed)

@bot.command(name='istatistik')
async def server_stats(ctx, period: str = 'günlük'):
    """Sunucu istatistiklerini gösterir"""
    guild = ctx.guild
    
    stats_embed = discord.Embed(
        title=f"📊 {guild.name} İstatistikleri",
        description=f"Periyot: {period}",
        color=discord.Color.blue()
    )
    
    # Sunucu bilgileri
    stats_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    stats_embed.add_field(
        name="👥 Üye Bilgileri",
        value=f"👤 Toplam: {guild.member_count}\n"
              f"🟢 Çevrimiçi: {sum(1 for m in guild.members if m.status != discord.Status.offline)}\n"
              f"🤖 Bot: {sum(1 for m in guild.members if m.bot)}",
        inline=True
    )
    
    # Kanal bilgileri
    stats_embed.add_field(
        name="📚 Kanal Bilgileri",
        value=f"💬 Metin: {len(guild.text_channels)}\n"
              f"🔊 Sesli: {len(guild.voice_channels)}\n"
              f"📑 Kategori: {len(guild.categories)}",
        inline=True
    )
    
    # Aktivite istatistikleri
    message_count = await db.get_message_count(ctx.guild.id, period)
    active_users = await db.get_active_users_count(ctx.guild.id, period)
    
    stats_embed.add_field(
        name="📈 Aktivite",
        value=f"💬 Mesajlar: {message_count}\n"
              f"👥 Aktif Üyeler: {active_users}\n"
              f"📊 Mesaj/Üye: {message_count/active_users:.1f}" if active_users > 0 else "Veri yok",
        inline=False
    )
    
    await ctx.send(embed=stats_embed)

@bot.command(name='seviye')
async def level(ctx, member: discord.Member = None):
    """Kullanıcı seviyesini gösterir"""
    if member is None:
        member = ctx.author

    xp, level = await db.get_user_level(member.id, ctx.guild.id)
    
    level_embed = discord.Embed(
        title=f"{member.name} Seviye Bilgileri",
        color=member.color
    )
    level_embed.add_field(name="Seviye", value=str(level), inline=True)
    level_embed.add_field(name="XP", value=str(xp), inline=True)
    level_embed.add_field(
        name="Sonraki Seviye",
        value=f"{(level + 1) * 100 - xp} XP kaldı",
        inline=True
    )
    
    await ctx.send(embed=level_embed)

@bot.command(name='liderlik')
async def leaderboard(ctx):
    """Sunucu liderlik tablosunu gösterir"""
    top_users = await db.get_top_users(ctx.guild.id)
    
    leaderboard_embed = discord.Embed(
        title="Sunucu Liderlik Tablosu",
        color=discord.Color.gold()
    )
    
    for i, (user_id, xp, level) in enumerate(top_users, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            leaderboard_embed.add_field(
                name=f"{i}. {member.name}",
                value=f"Seviye: {level} | XP: {xp}",
                inline=False
            )
    
    await ctx.send(embed=leaderboard_embed)

@bot.command(name='grafik')
async def activity_graph(ctx, days: int = 7):
    """Sunucu aktivite grafiğini gösterir"""
    if days > 30:
        await ctx.send("En fazla 30 günlük grafik görüntüleyebilirsiniz.")
        return

    buf = await db.generate_activity_graph(ctx.guild.id, days)
    
    file = discord.File(buf, filename="activity_graph.png")
    await ctx.send(f"Son {days} günün aktivite grafiği:", file=file)

@bot.command(name='emojiler')
async def emoji_stats(ctx):
    """Emoji kullanım istatistiklerini gösterir"""
    emoji_stats = await db.get_emoji_stats(ctx.guild.id)
    
    emoji_embed = discord.Embed(
        title="En Çok Kullanılan Emojiler",
        color=discord.Color.blue()
    )
    
    for emoji_name, count in emoji_stats.items():
        emoji_embed.add_field(
            name=emoji_name,
            value=f"{count} kez kullanıldı",
            inline=True
        )
    
    await ctx.send(embed=emoji_embed)

@bot.command(name='kanal')
async def channel_stats(ctx, channel: discord.TextChannel = None, period: str = 'günlük'):
    """
    Kanal istatistiklerini detaylı olarak gösterir
    Kullanım: !kanal #kanal-adı günlük/haftalık/aylık
    """
    if channel is None:
        channel = ctx.channel
    
    stats = await db.get_channel_stats(channel.id, ctx.guild.id, period)
    
    channel_embed = discord.Embed(
        title=f"#{channel.name} İstatistikleri ({period})",
        color=discord.Color.green()
    )
    
    # Temel istatistikler
    channel_embed.add_field(
        name="Toplam Mesaj",
        value=str(stats['message_count']),
        inline=True
    )
    channel_embed.add_field(
        name="Aktif Kullanıcılar",
        value=str(stats['active_users']),
        inline=True
    )
    
    # En aktif saatler
    peak_hours_text = "\n".join([f"{hour}:00 - {count} mesaj" for hour, count in stats['peak_hours']])
    channel_embed.add_field(
        name="En Aktif Saatler",
        value=peak_hours_text or "Veri yok",
        inline=False
    )
    
    # En aktif kullanıcılar
    top_users_text = ""
    for user_id, count in stats['top_users']:
        member = ctx.guild.get_member(user_id)
        if member:
            top_users_text += f"{member.name}: {count} mesaj\n"
    
    channel_embed.add_field(
        name="En Aktif Kullanıcılar",
        value=top_users_text or "Veri yok",
        inline=False
    )
    
    await ctx.send(embed=channel_embed)

# Sesli sıralama komutları
@bot.command(name='g-s')
async def daily_voice(ctx):
    """Günlük sesli sıralama"""
    await send_voice_leaderboard(ctx, 'günlük')

@bot.command(name='h-s')
async def weekly_voice(ctx):
    """Haftalık sesli sıralama"""
    await send_voice_leaderboard(ctx, 'haftalık')

@bot.command(name='a-s')
async def monthly_voice(ctx):
    """Aylık sesli sıralama"""
    await send_voice_leaderboard(ctx, 'aylık')

# Mesaj sıralama komutları
@bot.command(name='g-m')
async def daily_messages(ctx):
    """Günlük mesaj sıralaması"""
    await send_message_leaderboard(ctx, 'günlük')

@bot.command(name='h-m')
async def weekly_messages(ctx):
    """Haftalık mesaj sıralaması"""
    await send_message_leaderboard(ctx, 'haftalık')

@bot.command(name='a-m')
async def monthly_messages(ctx):
    """Aylık mesaj sıralaması"""
    await send_message_leaderboard(ctx, 'aylık')

async def send_voice_leaderboard(ctx, period: str):
    """Sesli sıralama gönderme yardımcı fonksiyonu"""
    leaderboard = await db.get_voice_leaderboard(ctx.guild.id, period)
    
    embed = discord.Embed(
        title=f"Sesli Sıralama ({period})",
        color=discord.Color.purple()
    )
    
    for i, (user_id, minutes) in enumerate(leaderboard, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            time_str = f"{hours} saat {remaining_minutes} dakika" if hours > 0 else f"{minutes} dakika"
            embed.add_field(
                name=f"{i}. {member.name}",
                value=time_str,
                inline=False
            )
    
    await ctx.send(embed=embed)

async def send_message_leaderboard(ctx, period: str):
    """Mesaj sıralaması gönderme yardımcı fonksiyonu"""
    leaderboard = await db.get_message_leaderboard(ctx.guild.id, period)
    
    embed = discord.Embed(
        title=f"Mesaj Sıralaması ({period})",
        color=discord.Color.blue()
    )
    
    for i, (user_id, message_count) in enumerate(leaderboard, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            embed.add_field(
                name=f"{i}. {member.name}",
                value=f"{message_count} mesaj",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='yardım')
async def custom_help(ctx):
    """Tüm komutları listeler"""
    embed = discord.Embed(
        title="Bot Komutları",
        description="Kullanılabilir tüm komutlar",
        color=discord.Color.blue()
    )

    # Genel Komutlar
    embed.add_field(
        name="📊 Genel İstatistikler",
        value="""
        `!istatistik [günlük/haftalık/aylık]` - Sunucu istatistikleri
        `!kullanıcı [@kullanıcı]` - Kullanıcı istatistikleri
        `!kanal [#kanal] [günlük/haftalık/aylık]` - Kanal detaylı istatistikleri
        """,
        inline=False
    )

    # Sıralama Komutları
    embed.add_field(
        name="🏆 Sıralama Komutları",
        value="""
        **Sesli Sıralama:**
        `!g-s` - Günlük sesli sıralama
        `!h-s` - Haftalık sesli sıralama
        `!a-s` - Aylık sesli sıralama
        
        **Mesaj Sıralama:**
        `!g-m` - Günlük mesaj sıralaması
        `!h-m` - Haftalık mesaj sıralaması
        `!a-m` - Aylık mesaj sıralaması
        """,
        inline=False
    )

    # Seviye Sistemi
    embed.add_field(
        name="⭐ Seviye Sistemi",
        value="""
        `!seviye [@kullanıcı]` - Seviye bilgisi
        `!liderlik` - Seviye liderlik tablosu
        """,
        inline=False
    )

    # Diğer Özellikler
    embed.add_field(
        name="🎯 Diğer Özellikler",
        value="""
        `!grafik [gün_sayısı]` - Aktivite grafiği (max 30 gün)
        `!emojiler` - Emoji kullanım istatistikleri
        """,
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name='top-stats')
async def permanent_stats(ctx):
    """Tüm zamanların en iyi istatistiklerini gösterir"""
    stats = await db.get_permanent_stats(ctx.guild.id)
    
    embed = discord.Embed(
        title="🏆 Tüm Zamanların En İyileri",
        color=discord.Color.gold()
    )
    
    for i, (user_id, messages, voice_minutes) in enumerate(stats, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            hours = voice_minutes // 60
            remaining_minutes = voice_minutes % 60
            voice_str = f"{hours}s {remaining_minutes}d" if hours > 0 else f"{voice_minutes}d"
            
            embed.add_field(
                name=f"{i}. {member.name}",
                value=f"📝 {messages} mesaj\n🎤 {voice_str}",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='avatar')
async def avatar(ctx, member: discord.Member = None):
    """Kullanıcının profil resmini büyük boyutta gösterir"""
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f"🖼️ {member.name} Profil Resmi",
        color=member.color
    )
    
    # En yüksek çözünürlüklü avatar URL'sini al
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    
    embed.set_image(url=avatar_url)
    embed.set_footer(text=f"İsteyen: {ctx.author.name}")
    
    await ctx.send(embed=embed)

@bot.command(name='sohbet-sil')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Belirtilen sayıda mesajı siler (Yönetici izni gerekir)"""
    if amount < 1 or amount > 100:
        await ctx.send("❌ 1 ile 100 arasında bir sayı belirtmelisiniz!")
        return
    
    # Silme işlemini gerçekleştir
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 komutu da siler
    
    # Bilgilendirme mesajı gönder
    info_message = await ctx.send(f"✅ {len(deleted)-1} mesaj silindi!")
    
    # 5 saniye sonra bilgilendirme mesajını da sil
    await asyncio.sleep(5)
    await info_message.delete()

# Botu çalıştır
bot.run(os.getenv('DISCORD_TOKEN')) 