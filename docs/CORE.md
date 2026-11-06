# Çekirdek sözleşmesi

`me_core_module` motorun kendisidir: iç işleyiş, `load`, `tick` ve modüllerin
bağlandığı hook slot'ları. Bu dosya, çekirdeğin bir modüle **verdiği** sözü ve
ondan **beklediği** şeyi tanımlar. Sözleşme dışında hiçbir şey garanti değildir.

## 1. Çekirdek hiçbir modülü adıyla çağırmaz

Bu, bütün düzenin dayandığı tek kural. Çekirdeğin bir modülün işine ihtiyacı
olduğunda yaptığı şey şudur:

```mcfunction
function #me_core_module:hook/trigger_dispatch
```

`#` işaretine dikkat: bu bir fonksiyon değil, bir **tag**. Tag'in içinde kimin
olduğunu çekirdek bilmez ve bilmemesi gerekir.

Modül tarafında karşılığı, modülün **kendi paketinde**:

```json
// me_trigger_module/data/me_core_module/tags/function/hook/trigger_dispatch.json
{
  "replace": false,
  "values": [
    { "id": "me_trigger_module:core/internal/trigger/dispatch", "required": false }
  ]
}
```

İki dosya **aynı tag kimliğini** tanımlar. `replace: false` olduğu için oyun ikisini
birleştirir: çekirdeğin boş listesi + modülün tek elemanı. Sonuç, çekirdeğin
`#me_core_module:hook/trigger_dispatch` çağrısının modülün fonksiyonunu çalıştırması.

`required: false` da tesadüf değil: modül yoksa çekirdeğin tag'i yine de yüklenir.
Modülü silmek paketi bozmaz — sadece o özellik sessizce durur.

## 2. Slot listesi

| Slot | Çalıştığı yer | Dönüş | Katkıda bulunan |
|---|---|---|---|
| `tick` | her tick | — | (boş; üçüncü taraf için) |
| `load` | dünya yüklenirken | — | (boş) |
| `player_tick` | her tick, oyuncu bağlamında | — | (boş) |
| `cb_tick` | komut bloğu kuyruğu doluyken | — | `me_cb_module` |
| `cmd_freeze_tick` | her tick | — | `me_cmd_module` |
| `interaction_tick` | her tick | — | `me_interaction_module` |
| `wand_tick` | her tick | — | `me_wand_module` |
| `trigger_dispatch` | her tick, oyuncu action skoru > 0 | — | `me_trigger_module` |
| `perm_tick` | her tick | — | `me_perm_module` |
| `perm_require` | izin sorulduğunda | **evet** | `me_perm_module` |
| `player_get_name` | isim çözümlemesi | **evet** | `me_player_module` |
| `player_enumerate` | load, adım 2 | — | `me_player_module` |
| `player_resolve` | load, adım 3 | — | `me_player_module` |
| `player_init` | load, adım 4 | — | `me_player_module` |
| `player_init_online` | çevrimiçi oyuncular için load | — | `me_player_module` |
| `player_init_from_name` | isimden çözümlenen oyuncu | — | `me_player_module` |

### Dönüş değeri taşıyan slot'lar

Bir tag birden çok fonksiyon çalıştırabilir, bu yüzden "tag'in dönüş değeri" diye
tek bir şey yoktur. Oyun şunu yapar:

- `execute store result ... run function #tag` → katkıların dönüş değerlerinin **toplamı**
- `unless function #tag` → tag'in tamamı sıfırdan farklı dönerse başarılı

Tek katkı olduğu sürece bu, eski skaler dönüşle birebir aynıdır. `perm_require` ve
`player_get_name` bugün tek katkılıdır; ikinci bir katkı eklenirse değerler toplanır —
bunu bilerek yapın, kazara değil.

## 3. Çekirdeğin yayınladığı servisler

Modüller bu kimlikleri çağırabilir; hepsi kararlı yüzeydir, imzaları değişmez:

| Kimlik | İş |
|---|---|
| `me_core_module:text/split` | metni ayırıcıya göre böl → `macroengine:output` |
| `me_core_module:text/concat` | metinleri birleştir |
| `me_core_module:text/safe` | dize skor/etiket olarak güvenli mi (1/0) |
| `me_core_module:text/ctl` | kontrol karakteri var mı |
| `me_core_module:text/lower` / `upper` | büyük/küçük harf |
| `me_core_module:text/replace` | metin değiştir |
| `me_core_module:text/reset` | metin çalışma alanını temizle |
| `me_core_module:core/ext/perm_count` | izin sayacı |
| `me_core_module:core/ext/player/add_var_clamped` | oyuncu değişkenine sınırlı ekleme |
| `me_core_module:core/ext/player/toggle_var` | oyuncu değişkenini çevir |
| `me_core_module:core/ext/world/count_near` | çevredeki varlıkları say |

`core/internal/...` altındaki hiçbir şey sözleşme değildir. Bir modül oraya
bakarsa `verify.py` derlemeyi kırar — bilerek: o ağacı değiştirme özgürlüğü ancak
kimse ona yaslanmadığı sürece vardır.

## 4. Modülden beklenenler

1. Namespace `me_<ad>_module`, kimlikler `me_<ad>_module:<yol>`; `api/` ve `systems/`
   segmenti yok (bu, `split.py`'nin uyguladığı adlandırma kuralıdır).
2. Başka bir modülün `core/internal` ağacına girmek yok. Gerekiyorsa o modül
   fonksiyonu **yayınlar**, sen yayınlanmış kimliği çağırırsın.
3. `pack.mcmeta` içinde `min_format`/`max_format` (26.x'in okuduğu biçim).
4. Hook'a katılmak istiyorsan kendi paketinde `data/me_core_module/tags/function/hook/<slot>.json`
   dosyasını yaz — çekirdeğin dosyasını **değiştirme**.

## 5. Ne denetlenir

`python3 tools/verify.py --pack build/packs` (veya `gradlew check`) şunları arar:

- çözülemeyen fonksiyon/tag referansı (`dangling`)
- eski `macroengine:` namespace'ine kalan gerçek çağrı (`old-namespace`)
- modülün başka modülün iç ağacına erişmesi (`private-access`)
- çekirdeğin bir modülü adıyla çağırması (`hooks`)
- modül bağımlılık grafiğinde döngü (`cycle`)
- eksik `pack.mcmeta` / boş paket (`pack-layout`)

Sıfır sorun = `[verify] OK`.
