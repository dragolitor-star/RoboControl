#!/bin/bash
# RCS-2000 Middleware - Tek Tuş Kurulum Scripti (Ubuntu/Debian için)
# Kullanım: sudo ./install.sh

set -e

echo "======================================================="
echo " RCS-2000 Middleware - On-Premise Kurulum Başlatılıyor"
echo "======================================================="

# 1. Root yetkisi kontrolü
if [ "$EUID" -ne 0 ]; then 
  echo "❌ Lütfen bu scripti root yetkisiyle (sudo ./install.sh) çalıştırın."
  exit 1
fi

echo -e "\n[1/4] Sistem güncelleniyor ve gerekli paketler kuruluyor..."
apt-get update -y
apt-get install -y curl ufw git jq

# 2. Docker Kurulumu Kontrolü
if ! command -v docker &> /dev/null; then
    echo -e "\n[2/4] Docker bulunamadı, kuruluyor..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo -e "\n[2/4] Docker zaten kurulu, atlanıyor..."
fi

# 3. Docker Compose Kurulumu Kontrolü
if ! command -v docker-compose &> /dev/null; then
    echo -e "\n[3/4] Docker Compose bulunamadı, kuruluyor..."
    curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo -e "\n[3/4] Docker Compose zaten kurulu, atlanıyor..."
fi

# 4. Güvenlik Duvarı (UFW) Ayarları
echo -e "\n[4/4] Güvenlik duvarı (UFW) yapılandırılıyor (Port 8000 açılıyor)..."
ufw allow 8000/tcp
ufw allow 22/tcp
# ufw --force enable # (Opsiyonel: Müşteri sistemlerinde ufw aktif etmek riskli olabilir, o yüzden sadece kural ekliyoruz)

# 5. .env Dosyası Oluşturma
if [ ! -f .env ]; then
    echo -e "\n⚠️ .env dosyası bulunamadı. .env.example'dan kopyalanıyor..."
    cp .env.example .env
    
    # API Key için rastgele güçlü bir şifre üret
    RANDOM_API_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
    sed -i "s/API_KEY=test-api-key/API_KEY=${RANDOM_API_KEY}/" .env
    
    echo "✅ Güvenli bir API Anahtarı üretildi."
else
    echo -e "\n✅ .env dosyası zaten mevcut."
fi

echo -e "\n======================================================="
echo " Kurulum Tamamlandı! Servisleri başlatmak için hazırlanıyor..."
echo "======================================================="

docker-compose up -d --build

echo -e "\n🚀 Sistem başarıyla başlatıldı!"
echo "-------------------------------------------------------"
echo "🌐 Dashboard Adresi : http://$(hostname -I | awk '{print $1}'):8000"
if [ ! -z "$RANDOM_API_KEY" ]; then
    echo "🔑 API Anahtarınız : $RANDOM_API_KEY"
    echo "   (Bu anahtarı güvenli bir yere kaydedin, dashboard'a girişte sorulacaktır.)"
else
    echo "🔑 API Anahtarınız : Lütfen .env dosyasındaki API_KEY değerine bakın."
fi
echo "-------------------------------------------------------"
echo "🛠 Sistem durumunu görmek için: docker-compose logs -f"
echo "======================================================="
