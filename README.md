# macroengine-modules

**macroEngine**, tek bir veri paketinden **bir çekirdek + bağımsız modüller** hâline
bölünmüş hâliyle. Düzen Fabric API'nin düzeni: çekirdek motoru taşır, her modül
çekirdeğe *hook tag'leri* üzerinden bağlanır ve çekirdek hiçbir modülün adını anmaz.

```
me_core_module      motor: iç işleyiş, load, tick, hook slot'ları
me_cmd_module       komut yürütme, freeze
me_player_module    oyuncu defteri
me_wand_module      asa
...                 (18 modül daha)
```

## Neden bu düzen

Tek paket hâlindeki macroEngine 1559 dosya, 1280 fonksiyon ve 105 tag'den oluşuyordu.
Hepsi tek namespace'te olduğu için "şu özelliği kaldırayım" demek, 9000'in üzerinde
referansın içinden o özelliğe ait olanları elle ayıklamak demekti. Bölünmüş hâlde bir
modülü kaldırmak, `build/packs/me_wand_module/` klasörünü silmekten ibarettir.

Bunu mümkün kılan iki kural var, ve ikisi de doğrulayıcı tarafından zorlanıyor:

1. **Çekirdek hiçbir modülü adıyla çağırmaz.** Çekirdeğin bir modüle ihtiyacı olduğunda
   `function #me_core_module:hook/<slot>` çağırır. Modül kendi paketinde *aynı tag
   kimliğini* tanımlayıp kendini ekler; oyun iki tanımı birleştirir.
2. **Bir modül başka bir modülün `core/internal` ağacına girmez.** Girebileceği tek yer
   karşı modülün *yayınlanmış* yüzeyidir.

İkisi de `gradlew check` ile denetlenir. Bir modülü silmek paketi bozmaz.

## Kimlik şeması

```
me_<modül>_module:<fonksiyon yolu>
```

`api/` ve `systems/` segmentleri **kaldırıldı**: namespace zaten modülü söylüyor, yol da
özelliği söylüyor. Eski `macroengine:api/cmd/other/run` → yeni
`me_cmd_module:cmd/other/run`. 1280 fonksiyonun tamamında çakışma yok.

| Eski | Yeni |
|---|---|
| `macroengine:api/wand/give_custom` | `me_wand_module:wand/give_custom` |
| `macroengine:systems/logic/if_or` | `me_core_module:logic/if_or` |
| `macroengine:core/internal/text/split` | `me_core_module:text/split` (yayınlandı) |
| `macroengine:core/internal/player/init` | `me_player_module:core/internal/player/init` |

## Derleme

Her modül ayrı bir Gradle alt-projesi, her biri kendi jar'ını üretir:

```bash
export JAVA_HOME=/path/to/jdk25     # 26.3 Java 25 ister

python3 tools/split.py --source <macroEngine-26.3 paketi> --out build
./gradlew dist                      # build/dist/*.jar — 20 paket
./gradlew check                     # referansları, sınırları, hook'ları doğrular
./gradlew :me_cmd_module:dist       # tek modülün jar'ı
```

`build/packs/` üretilen çıktıdır, depoya girmez (`build/` .gitignore'da). Jar'lar
doğrudan bir dünyanın `datapacks/` klasörüne atılabilir; **core olmadan hiçbir modül
yüklenmez**, ama core tek başına yüklenir ve çalışır.

## Modül listesi

| Modül | Dosya | Ne yapar |
|---|---:|---|
| `me_core_module` | 836 | motor, hook slot'ları, load/tick, metin ve matematik servisleri |
| `me_cmd_module` | 185 | komut yürütme, freeze, multi_cmd |
| `me_player_module` | 181 | oyuncu defteri, giriş/çıkış, isim çözümleme |
| `me_store_module` | 71 | kalıcı anahtar-değer deposu |
| `me_perm_module` | 34 | izinler |
| `me_world_module` | 29 | dünya işlemleri |
| `me_container_module` | 27 (+4 yayınlanmış) | konteyner slot işlemleri |
| `me_wand_module` | 26 | asa |
| `me_toggle_module` | 25 | açma/kapama bayrakları |
| `me_cb_module` | 23 | komut bloğu kuyruğu |
| `me_block_module` | 20 | blok davranış kaydı |
| `me_title_module` | 17 | başlık / actionbar |
| `me_item_module` | 16 | eşya |
| `me_interaction_module` | 16 | etkileşim taraması |
| `me_color_module` | 13 | renk |
| `me_gamerule_module` | 13 | gamerule |
| `me_trigger_module` | 12 | trigger kaydı |
| `me_tui_module` | 8 | metin arayüzü |
| `me_macro_module` | 5 | macro yardımcıları |
| `me_diagnostics_module` | 2 | teşhis |

## Kendi modülünü yazmak

`docs/CORE.md` hook sözleşmesini, `docs/MODULE.md` yeni bir modülün iskeletini anlatır.
Kısaca: bir klasör aç, `me_<ad>_module` namespace'ini kullan, çekirdeğin hook tag'ine
kendi değerini ekle. Çekirdekte tek satır değiştirmen gerekmez.

## Araçlar

| Dosya | İş |
|---|---|
| `tools/split.py` | kaynak paketi böler; kimlikleri yeniden yazar, hook tag'lerini üretir |
| `tools/verify.py` | bölünmüş çıktıyı denetler (referans, sınır, döngü, hook, pack.mcmeta) |

`split.py` kaynağı **hiç değiştirmez**; her koşuda `build/` ağacını sıfırdan yazar.

## Bilinen sınırlar

- `me_cmd_module:cmd/other/action_run` bir macro fonksiyondur: hedefi `$(type)` ile
  çalışma anında kurulur, statik olarak çözülemez. `build/MACRO_REFS.txt`'te listelenir
  ve doğrulayıcıda muaftır.
- `me_tui_module` bir tellraw `click_event`'i içinde `/function $(fn)` yazar; aynı sebep.
- Kaynak pakette zaten var olan bazı tag referansları (`#macroengine:internal/dispatch`
  gibi) bölünmüş çıktıda da aynı biçimde durur; bunlar bölme hatası değil, kaynağın
  kendi durumudur.

## Lisans

`LICENSE` dosyasına bakın.
