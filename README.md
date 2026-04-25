# RCS-2000 Middleware

Bu proje, **Hikrobot RCS-2000** robot kontrol yazılımı ile müşteri sistemleri (WMS, ERP, Web UI, Mobil UI) arasında köprü görevi gören, Python 3.10+, FastAPI, SQLAlchemy 2.0 (async), Redis ve Celery kullanılarak geliştirilmiş, production-grade bir middleware servisidir.

## Mimari Özeti

- **Web Çerçevesi:** FastAPI (Asenkron)
- **Veritabanı:** MySQL (aiomysql ile async SQLAlchemy 2.0)
- **Önbellek & Kuyruk:** Redis
- **Arka Plan Görevleri:** Celery
- **RCS İletişimi:** HTTPX, Tenacity (retry stratejisi)
- **Güvenlik:** API Anahtarı ve HMAC-SHA256 Webhook İmzalama
- **Kullanıcı Arayüzü:** Dashboard (Vanilla JS, HTML, CSS), `http://localhost:8000/`

### Dizin Yapısı

```
app/
├── api/             # FastAPI router'ları
├── clients/         # Dış servis istemcileri (RCS2000Client)
├── core/            # Config, loglama, exceptions, security
├── db/              # SQLAlchemy session ve model tanımları
├── models/          # Veritabanı tabloları
├── repositories/    # Veri erişim katmanı
├── schemas/         # Pydantic validasyon modelleri
├── services/        # İş mantığı
├── static/          # Web UI Dashboard (HTML, CSS, JS)
├── utils/           # Redis yardımcıları, imzalama stratejileri
└── workers/         # Celery task'ları
```

## Kurulum ve Çalıştırma (Docker Compose)

En kolay yöntem Docker Compose kullanmaktır. Gereksinimler:
- Docker & Docker Compose

### 1. Ortam Değişkenlerini Ayarlama
```bash
cp .env.example .env
# .env dosyasındaki değerleri (RCS bağlantı bilgileri, API Key vb.) ortamınıza göre güncelleyin.
```

### 2. Uygulamayı Başlatma
```bash
docker-compose up -d
```
Bu komut veritabanını, redis'i, API sunucusunu ve worker'ı başlatacaktır.

- **Dashboard:** [http://localhost:8000](http://localhost:8000)
- **API Dokümantasyonu (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

### Geliştirme Ortamı Kurulumu

Python 3.10+ ve bir virtual environment önerilir.

```bash
# Bağımlılıkları yükle
pip install -e ".[dev]"

# Migration'ları uygula
python -m alembic upgrade head

# Sunucuyu başlat
uvicorn app.main:app --reload

# Worker'ı başlat (Ayrı terminalde)
celery -A app.workers.celery_app worker -l info
```

## Testler

Testleri çalıştırmak için:
```bash
pytest tests/ -v
```
