# Yeni bir modül yazmak

Bu dosya, kaynak paketi bölmenin dışında **elle** bir modül eklemenin yolunu
anlatır. Var olan bir modülü incelemek en hızlı yol: `build/packs/me_wand_module/`
iyi bir örnektir (26 fonksiyon, tek hook katkısı).

## 1. İskelet

```
me_shout_module/
├── pack.mcmeta
└── data/
    └── me_shout_module/
        ├── function/
        │   ├── shout/
        │   │   ├── send.mcfunction        # yayınlanmış yüzey
        │   │   └── internal/
        │   │       └── format.mcfunction  # özel
        │   └── hook/
        │       └── tick.mcfunction        # bu modülün tick işi
        └── tags/                          # (opsiyonel, kendi tag'lerin)
```

`pack.mcmeta` (26.x biçimi):

```json
{
  "pack": {
    "description": "me_shout_module (macroEngine 1.0.0)",
    "min_format": [121, 0],
    "max_format": [121, 0]
  }
}
```

## 2. Çekirdeğe bağlan

Çekirdeğin bir tick kancasına katılmak için **kendi paketinde** şu dosyayı yaz:

```
data/me_core_module/tags/function/hook/tick.json
```

```json
{
  "replace": false,
  "values": [
    { "id": "me_shout_module:hook/tick", "required": false }
  ]
}
```

Bu kadar. Çekirdekte hiçbir dosyaya dokunmadın, çekirdek senin adını bilmiyor,
ve sen silindiğinde çekirdek çalışmaya devam eder.

> `replace: false` **zorunlu**. `true` yazarsan çekirdeğin ve diğer modüllerin
> katkılarını silersin — tag'i son yazan kazanır, yani bir modül diğerlerini
> sessizce kapatır.

## 3. Çekirdeğin servislerini kullan

```mcfunction
# metni böl
data modify storage macroengine:input string set from storage me_shout:work line
data modify storage macroengine:input separator set value " "
data modify storage macroengine:input n set value 1
function me_core_module:text/split
data modify storage me_shout:work first set from storage macroengine:output string.result[0]
```

`core/internal/...` **çağırma**. Bir şeye ihtiyacın var ve yayınlanmamışsa, doğru
cevap onu çağırmak değil: ya kendi modülünde yaz, ya da o modülün deposunda bir
"bunu yayınlayalım" isteği aç.

## 4. Başka bir modülü kullan

Var olan bir modülün yayınlanmış yüzeyini çağır:

```mcfunction
function me_container_module:container/slot_set
```

`me_container_module:core/internal/container/slot_set_do` **hayır**. İlki sözleşme,
ikincisi o modülün kendi işi — yarın yeniden adlandırılabilir.

## 5. Derle

```bash
# paketleri üret (yalnızca kaynak paketten bölüyorsan)
python3 tools/split.py --source <paket> --out build

# senin modülün için jar
./gradlew :me_shout_module:dist

# hepsini birden + doğrulama
./gradlew check dist
```

`build/packs/` altındaki bir klasörü elle oluşturduysan `settings.gradle` onu
kendiliğinden bulur (klasörleri tarar, liste sabit değil) — ama `split.py` her
koşuda `build/` ağacını sıfırdan yazdığı için elle eklediğin klasör **silinir**.
Kalıcı bir modül yazıyorsan `tools/split.py` içindeki `MODULES` tablosuna ekle,
ya da modülü `build/` dışında ayrı bir proje olarak tut.

## 6. Doğrula

```bash
./gradlew check
```

Şu hataları görürsen:

| Mesaj | Anlamı |
|---|---|
| `dangling-reference` | bir `function x:y` var ama `y` hiçbir pakette tanımlı değil |
| `private-access` | başka bir modülün `core/internal` ağacına girdin |
| `hooks` | çekirdek bir modülü adıyla çağırıyor (bu senin değil, çekirdeğin hatası) |
| `cycle` | modül grafiğinde döngü var; genelde iki modül birbirini çağırıyor |
| `pack-layout` | `pack.mcmeta` yok ya da paket boş |

## 7. Yayınlanan yüzeyini belgele

Modülünün deposuna üç satırlık bir `PUBLIC.md` koy: hangi kimlikler sözleşme, hangi
girdi storage'ı okuyorlar, hangi çıktıyı yazıyorlar, ne döndürüyorlar. `verify.py`
bunu denetlemez; bir sonraki modülü yazan kişi denetler.
