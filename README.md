# Discord İstatistik Botu

Discord sunucunuz için gelişmiş istatistik ve seviye sistemi botu.

## Özellikler

- 📊 Detaylı sunucu istatistikleri
- 🎤 Sesli kanal takibi
- 💬 Mesaj istatistikleri
- ⭐ Seviye sistemi
- 📈 Grafik raporları
- 😀 Emoji kullanım analizi
- 👥 Rol takip sistemi

## Kurulum

1. Python 3.8 veya daha yüksek bir sürümü yükleyin
2. Repository'yi klonlayın veya indirin
3. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

4. `.env` dosyasını düzenleyin:
   - Discord Developer Portal'dan bir bot oluşturun
   - Bot tokenınızı `.env` dosyasındaki `DISCORD_TOKEN=` kısmına yapıştırın
   - İsteğe bağlı olarak `BOT_PREFIX=` kısmını değiştirerek komut önekini değiştirebilirsiniz (varsayılan: !)

5. Botu çalıştırın:
```bash
python main.py
```

## Bot Komutları

### 📊 Genel İstatistikler
- `!istatistik [günlük/haftalık/aylık]` - Sunucu istatistikleri
- `!kullanıcı [@kullanıcı]` - Kullanıcı istatistikleri
- `!kanal [#kanal] [günlük/haftalık/aylık]` - Kanal detaylı istatistikleri

### 🏆 Sıralama Komutları
**Sesli Sıralama:**
- `!g-s` - Günlük sesli sıralama
- `!h-s` - Haftalık sesli sıralama
- `!a-s` - Aylık sesli sıralama

**Mesaj Sıralama:**
- `!g-m` - Günlük mesaj sıralaması
- `!h-m` - Haftalık mesaj sıralaması
- `!a-m` - Aylık mesaj sıralaması

### ⭐ Seviye Sistemi
- `!seviye [@kullanıcı]` - Seviye bilgisi
- `!liderlik` - Seviye liderlik tablosu

### 🎯 Diğer Özellikler
- `!grafik [gün_sayısı]` - Aktivite grafiği (max 30 gün)
- `!emojiler` - Emoji kullanım istatistikleri

## Bot İzinleri

Bot'un düzgün çalışması için aşağıdaki izinlere ihtiyacı vardır:

- Mesajları Görüntüle
- Mesaj Geçmişini Görüntüle
- Mesaj Gönder
- Dosya Yükle
- Üyeleri Görüntüle
- Sunucu İstatistiklerini Görüntüle
- Sesli Kanallara Bağlan
- Rolleri Yönet (isteğe bağlı, rol takibi için)

## Sorun Giderme

1. Bot çevrimiçi olmuyor:
   - `.env` dosyasındaki token'ı kontrol edin
   - Bot'un Discord Developer Portal'da aktif olduğundan emin olun

2. Komutlar çalışmıyor:
   - Bot'un gerekli izinlere sahip olduğunu kontrol edin
   - Komut önekini doğru kullandığınızdan emin olun

3. Veritabanı hataları:
   - `discord_stats.db` dosyasının yazma iznine sahip olduğundan emin olun
   - Gerekirse dosyayı silip botu yeniden başlatın (veriler sıfırlanır)

## Destek

Herhangi bir sorun veya öneriniz için GitHub üzerinden issue açabilirsiniz. 