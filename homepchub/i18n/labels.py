"""Turkish labels for device feature UI (kasa reports English names)."""

from __future__ import annotations

FEATURE_IDS = {
    "rssi": "Sinyal gücü (RSSI)",
    "signal_level": "Sinyal seviyesi",
    "ssid": "Wi‑Fi ağı (SSID)",
    "device_id": "Cihaz kimliği",
    "mac": "MAC adresi",
    "on_since": "Açık olduğu süre",
    "cloud_connection": "Bulut bağlantısı",
    "device_time": "Cihaz saati",
    "overheated": "Aşırı ısınma",
    "update_available": "Güncelleme var",
    "auto_update_enabled": "Otomatik güncelleme",
    "current_firmware_version": "Mevcut yazılım sürümü",
    "available_firmware_version": "Mevcut yeni sürüm",
    "check_latest_firmware": "Son yazılımı kontrol et",
    "led": "Durum LED’i",
    "state": "Güç",
    "brightness": "Parlaklık",
    "hsv": "HSV renk",
    "color_temperature": "Renk sıcaklığı",
    "current_consumption": "Anlık tüketim",
    "consumption_today": "Bugünkü tüketim",
    "consumption_this_month": "Bu ayki tüketim",
    "consumption_total": "Toplam tüketim",
    "voltage": "Gerilim",
    "current": "Akım",
    "auto_off_enabled": "Otomatik kapanma",
    "auto_off_minutes": "Otomatik kapanma süresi",
    "auto_off_at": "Otomatik kapanma zamanı",
    "child_lock": "Çocuk kilidi",
    "overloaded": "Aşırı yük",
    "power_protection_threshold": "Güç koruma eşiği",
    "report_interval": "Rapor aralığı",
    "homekit_setup_code": "HomeKit kurulum kodu",
    "matter_setup_code": "Matter kurulum kodu",
    "smooth_transitions": "Yumuşak geçişler",
    "smooth_transition_on": "Açılış geçişi",
    "smooth_transition_off": "Kapanış geçişi",
}

FEATURE_NAMES = {
    "rssi": "Sinyal gücü (RSSI)",
    "signal level": "Sinyal seviyesi",
    "ssid": "Wi‑Fi ağı (SSID)",
    "device id": "Cihaz kimliği",
    "cloud connection": "Bulut bağlantısı",
    "device time": "Cihaz saati",
    "overheated": "Aşırı ısınma",
    "update available": "Güncelleme var",
    "auto update enabled": "Otomatik güncelleme",
    "current firmware version": "Mevcut yazılım sürümü",
    "available firmware version": "Mevcut yeni sürüm",
    "check latest firmware": "Son yazılımı kontrol et",
    "led": "Durum LED’i",
    "state": "Güç",
    "brightness": "Parlaklık",
    "hsv": "HSV renk",
    "color temperature": "Renk sıcaklığı",
    "current consumption": "Anlık tüketim",
    "today's consumption": "Bugünkü tüketim",
    "this month's consumption": "Bu ayki tüketim",
    "total consumption since reboot": "Yeniden başlatmadan beri toplam tüketim",
    "voltage": "Gerilim",
    "current": "Akım",
    "auto off enabled": "Otomatik kapanma",
    "auto off in": "Otomatik kapanma süresi",
    "auto off at": "Otomatik kapanma zamanı",
    "child lock": "Çocuk kilidi",
    "overloaded": "Aşırı yük",
    "power protection threshold": "Güç koruma eşiği",
    "report interval": "Rapor aralığı",
    "homekit setup code": "HomeKit kurulum kodu",
    "matter setup code": "Matter kurulum kodu",
    "smooth transitions": "Yumuşak geçişler",
    "smooth transition on": "Açılış geçişi",
    "smooth transition off": "Kapanış geçişi",
    "on since": "Açık olduğu süre",
}

CATEGORIES = {
    "Primary": "Birincil",
    "Info": "Bilgi",
    "Information": "Bilgi",
    "Config": "Yapılandırma",
    "Configuration": "Yapılandırma",
    "Debug": "Hata ayıklama",
    "Unknown": "Diğer",
}

TYPES = {
    "Sensor": "Sensör",
    "BinarySensor": "İkili sensör",
    "Switch": "Anahtar",
    "Number": "Sayı",
    "Choice": "Seçim",
    "Action": "Eylem",
    "Unknown": "Bilinmeyen",
}

KINDS = {
    "plug": "priz",
    "bulb": "ampul",
    "strip": "şerit",
    "other": "diğer",
}

LIGHT_FEATS = {
    "brightness": "parlaklık",
    "hsv": "renk (HSV)",
    "color_temp": "renk sıcaklığı",
}

UNITS = {
    "dBm": "dBm",
    "W": "W",
    "kWh": "kWh",
    "V": "V",
    "A": "A",
    "%": "%",
    "K": "K",
    "min": "dk",
    "s": "sn",
    "m": "m",
}

FEATURE_HELP = {
    "rssi": "Cihazın Wi‑Fi sinyal gücüdür. Negatif dBm cinsinden ölçülür; örneğin −50 iyi, −80 zayıf sayılır.",
    "signal_level": "Sinyal gücünün basitleştirilmiş seviyesidir (genelde 0–4 arası).",
    "ssid": "Cihazın bağlı olduğu kablosuz ağın adıdır.",
    "device_id": "Üreticinin cihaza verdiği benzersiz kimlik numarasıdır.",
    "mac": "Ağ kartının fiziksel adresidir; ağda cihazı ayırt etmek için kullanılır.",
    "on_since": "Cihazın (veya soketin) en son ne zamandan beri açık olduğunu gösterir.",
    "cloud_connection": "Cihazın TP‑Link bulutuna bağlı olup olmadığını gösterir. Yerel kontrol için zorunlu değildir.",
    "device_time": "Cihazın kendi saat bilgisidir.",
    "overheated": "Cihaz aşırı ısındığında uyarı verir.",
    "update_available": "Yeni bir yazılım güncellemesi olup olmadığını gösterir.",
    "auto_update_enabled": "Açıksa cihaz yazılımını otomatik güncelleyebilir.",
    "current_firmware_version": "Cihazda şu an yüklü olan yazılım sürümüdür.",
    "available_firmware_version": "İndirilebilecek daha yeni yazılım sürümüdür (varsa).",
    "check_latest_firmware": "Buluttan en güncel yazılım bilgisini sorgular.",
    "led": "Prizin / cihazın üzerindeki durum ışığını açıp kapatır.",
    "state": "Cihazın veya soketin açık/kapalı güç durumudur.",
    "brightness": "Ampulün parlaklık yüzdesidir (1–100).",
    "hsv": "Rengi ton (H), doygunluk (S) ve değer (V) ile ayarlar.",
    "color_temperature": "Beyaz ışığın sıcaklığını Kelvin cinsinden ayarlar (sıcak sarı ↔ soğuk beyaz).",
    "current_consumption": "Anlık güç tüketimidir (Watt).",
    "consumption_today": "Bugün kullanılan elektrik enerjisidir (kWh).",
    "consumption_this_month": "Bu ay kullanılan elektrik enerjisidir (kWh).",
    "consumption_total": "Ölçüm sıfırlanmasından beri toplam tüketimdir.",
    "voltage": "Şebeke gerilimidir (Volt).",
    "current": "Çekilen elektrik akımıdır (Amper).",
    "auto_off_enabled": "Belirli süre sonra cihazı otomatik kapatmayı açar/kapatır.",
    "auto_off_minutes": "Otomatik kapanmanın kaç dakika sonra olacağını belirler.",
    "auto_off_at": "Otomatik kapanmanın planlandığı zamandır.",
    "child_lock": "Fiziksel düğmeyle aç/kapa yapılmasını engeller.",
    "overloaded": "Cihaz aşırı yük korumasına takıldığında uyarır.",
    "power_protection_threshold": "Aşırı yük korumasının devreye girdiği güç eşiğidir.",
    "report_interval": "Cihazın durumunu ne sıklıkla bildirdiğidir.",
    "homekit_setup_code": "Apple HomeKit’e eklemek için kurulum kodu.",
    "matter_setup_code": "Matter ekosistemine eklemek için kurulum kodu.",
    "smooth_transitions": "Parlaklık/renk değişimlerinde yumuşak geçişi açar.",
    "smooth_transition_on": "Açılırken geçiş süresidir.",
    "smooth_transition_off": "Kapanırken geçiş süresidir.",
}

FEATURE_HELP_BY_NAME = {
    "rssi": FEATURE_HELP["rssi"],
    "signal level": FEATURE_HELP["signal_level"],
    "ssid": FEATURE_HELP["ssid"],
    "device id": FEATURE_HELP["device_id"],
    "cloud connection": FEATURE_HELP["cloud_connection"],
    "device time": FEATURE_HELP["device_time"],
    "overheated": FEATURE_HELP["overheated"],
    "update available": FEATURE_HELP["update_available"],
    "auto update enabled": FEATURE_HELP["auto_update_enabled"],
    "current firmware version": FEATURE_HELP["current_firmware_version"],
    "available firmware version": FEATURE_HELP["available_firmware_version"],
    "check latest firmware": FEATURE_HELP["check_latest_firmware"],
    "led": FEATURE_HELP["led"],
    "current consumption": FEATURE_HELP["current_consumption"],
    "today's consumption": FEATURE_HELP["consumption_today"],
    "this month's consumption": FEATURE_HELP["consumption_this_month"],
    "total consumption since reboot": FEATURE_HELP["consumption_total"],
    "voltage": FEATURE_HELP["voltage"],
    "current": FEATURE_HELP["current"],
    "auto off enabled": FEATURE_HELP["auto_off_enabled"],
    "auto off in": FEATURE_HELP["auto_off_minutes"],
    "auto off at": FEATURE_HELP["auto_off_at"],
    "child lock": FEATURE_HELP["child_lock"],
    "overloaded": FEATURE_HELP["overloaded"],
    "power protection threshold": FEATURE_HELP["power_protection_threshold"],
    "on since": FEATURE_HELP["on_since"],
}

UI_HELP = {
    "devices": "Kayıtlı Tapo cihazların listesi. Kartı seçip kaldırabilir, anahtarlarla aç/kapa yapabilirsin.",
    "scan": "Yerel ağdaki Tapo cihazlarını arar. Bulunanları seçip listeye ekleyebilirsin.",
    "remove": "Seçili cihazı kayıtlı listeden siler (cihazın kendisini fabrika ayarına almaz).",
    "scan_btn": "Ağı tarayıp henüz eklenmemiş cihazları listeler. Birkaç saniye sürebilir.",
    "add_btn": "Taramada seçtiğin cihazları kalıcı listeye ekler.",
    "theme": "Açık ve koyu tema arasında geçer. Tercih bilgisayarında saklanır.",
    "more": "Cihaza özel ayar ve detay penceresini açar.",
    "power": "Ampulü veya prizi açıp kapatır.",
    "presets": "Hazır ortam modları. Ekran Senkronu için monitör seçip Tanımla ile numaraları görebilirsin.",
    "preset_modes": (
        "Okuma — sıcak, yüksek parlaklık (okumak için).\n"
        "Çalışma — soğuk, parlak ışık (odak için).\n"
        "Ekran Senkronu — seçili monitörün ortalama rengine uyar.\n"
        "Dışarısı — yerel hava ve saate göre renk.\n"
        "Sirkadiyen Ritim — günün saatine göre Kelvin/parlaklık.\n"
        "Film — sıcak, çok loş yan ışık.\n"
        "Rahatlama — sıcak, yumuşak loş ışık."
    ),
    "brightness": "Işık şiddetini yüzde olarak ayarlar. Bırakınca cihaza gönderilir.",
    "color_temp": "Beyaz ışığın sıcak/soğuk tonunu Kelvin cinsinden ayarlar.",
    "color": "Renk tekerleği veya H/S/V kaydırıcılarıyla rengi seçer.",
    "hue": "Rengin tonu (0–360°): kırmızı, yeşil, mavi vb.",
    "saturation": "Rengin canlılığı (0 soluk, 100 doygun).",
    "value": "Rengin parlaklık bileşeni (HSV içindeki V).",
    "kind_plug": "Tek çıkışlı akıllı priz.",
    "kind_bulb": "Renk veya beyaz ışık kontrolü olan ampul.",
    "kind_strip": "Birden fazla soketi olan priz şeridi; her soket ayrı kontrol edilir.",
    "socket": "Şerit üzerindeki tek bir elektrik çıkışı.",
    "rename": "Cihazın veya priz soketinin adını değiştirir. İsim cihaza yazılır.",
    "status": "Uygulamanın son işlem durumunu gösterir.",
}


FEATURE_HELP_EN = {
    "rssi": "Wi‑Fi signal strength in dBm. Around −50 is strong; −80 is weak.",
    "signal_level": "Simplified signal strength level (often 0–4).",
    "ssid": "Name of the wireless network the device is connected to.",
    "device_id": "Unique manufacturer identifier for this device.",
    "mac": "Hardware network address used to identify the device on the LAN.",
    "on_since": "How long the device or outlet has been on since it was last turned on.",
    "cloud_connection": "Whether the device is linked to the TP‑Link cloud. Not required for local control.",
    "device_time": "The device’s own clock.",
    "overheated": "Warns when the device is overheating.",
    "update_available": "Whether a firmware update is available.",
    "auto_update_enabled": "When on, the device may update firmware automatically.",
    "current_firmware_version": "Firmware version currently installed.",
    "available_firmware_version": "Newer firmware version available to install, if any.",
    "check_latest_firmware": "Query the cloud for the latest firmware info.",
    "led": "Turns the status LED on the device on or off.",
    "state": "Power on/off state of the device or outlet.",
    "brightness": "Bulb brightness percentage (1–100).",
    "hsv": "Sets color via hue (H), saturation (S), and value (V).",
    "color_temperature": "White light warmth in Kelvin (warm amber ↔ cool white).",
    "current_consumption": "Instant power draw in watts.",
    "consumption_today": "Energy used today in kWh.",
    "consumption_this_month": "Energy used this month in kWh.",
    "consumption_total": "Total energy since the meter was reset.",
    "voltage": "Mains voltage in volts.",
    "current": "Current draw in amperes.",
    "auto_off_enabled": "Enables turning the device off after a delay.",
    "auto_off_minutes": "Minutes until auto-off triggers.",
    "auto_off_at": "Scheduled time for auto-off.",
    "child_lock": "Blocks using the physical button to toggle power.",
    "overloaded": "Warns when overload protection has tripped.",
    "power_protection_threshold": "Power threshold that triggers overload protection.",
    "report_interval": "How often the device reports status.",
    "homekit_setup_code": "Setup code for Apple HomeKit.",
    "matter_setup_code": "Setup code for Matter pairing.",
    "smooth_transitions": "Enables smooth fades when changing brightness/color.",
    "smooth_transition_on": "Fade duration when turning on.",
    "smooth_transition_off": "Fade duration when turning off.",
}

FEATURE_HELP_BY_NAME_EN = {
    "rssi": FEATURE_HELP_EN["rssi"],
    "signal level": FEATURE_HELP_EN["signal_level"],
    "ssid": FEATURE_HELP_EN["ssid"],
    "device id": FEATURE_HELP_EN["device_id"],
    "cloud connection": FEATURE_HELP_EN["cloud_connection"],
    "device time": FEATURE_HELP_EN["device_time"],
    "overheated": FEATURE_HELP_EN["overheated"],
    "update available": FEATURE_HELP_EN["update_available"],
    "auto update enabled": FEATURE_HELP_EN["auto_update_enabled"],
    "current firmware version": FEATURE_HELP_EN["current_firmware_version"],
    "available firmware version": FEATURE_HELP_EN["available_firmware_version"],
    "check latest firmware": FEATURE_HELP_EN["check_latest_firmware"],
    "led": FEATURE_HELP_EN["led"],
    "current consumption": FEATURE_HELP_EN["current_consumption"],
    "today's consumption": FEATURE_HELP_EN["consumption_today"],
    "this month's consumption": FEATURE_HELP_EN["consumption_this_month"],
    "total consumption since reboot": FEATURE_HELP_EN["consumption_total"],
    "voltage": FEATURE_HELP_EN["voltage"],
    "current": FEATURE_HELP_EN["current"],
    "auto off enabled": FEATURE_HELP_EN["auto_off_enabled"],
    "auto off in": FEATURE_HELP_EN["auto_off_minutes"],
    "auto off at": FEATURE_HELP_EN["auto_off_at"],
    "child lock": FEATURE_HELP_EN["child_lock"],
    "overloaded": FEATURE_HELP_EN["overloaded"],
    "power protection threshold": FEATURE_HELP_EN["power_protection_threshold"],
    "on since": FEATURE_HELP_EN["on_since"],
}

UI_HELP_EN = {
    "devices": "Your saved Tapo devices. Select a card to remove it; use switches to power on/off.",
    "scan": "Searches the LAN for Tapo devices. Select results to add them to your list.",
    "remove": "Removes the selected device from the saved list (does not factory-reset hardware).",
    "scan_btn": "Scans the network for devices not yet added. May take a few seconds.",
    "add_btn": "Adds the selected scan results to your permanent list.",
    "theme": "Toggles light and dark theme. Preference is saved on this PC.",
    "more": "Opens device-specific settings and details.",
    "power": "Turns the bulb or plug on or off.",
    "presets": "Ambient light recipes. For Screen Sync, pick a monitor and use Identify to see numbers on each display.",
    "preset_modes": (
        "Reading — warm, bright light for reading.\n"
        "Work — cool, bright light for focus.\n"
        "Screen Sync — follows the average color of the chosen monitor.\n"
        "Outside — color from local weather and time of day.\n"
        "Circadian Rhythm — Kelvin/brightness follow the time of day.\n"
        "Movie — warm, very dim bias light.\n"
        "Relax — warm, soft dim light."
    ),
    "brightness": "Sets light intensity as a percentage. Sent when you release the slider.",
    "color_temp": "Sets white light warmth/coolness in Kelvin.",
    "color": "Pick a color with the wheel or H/S/V sliders.",
    "hue": "Color hue (0–360°): red, green, blue, etc.",
    "saturation": "Color vividness (0 pale, 100 full).",
    "value": "Brightness component of HSV (V).",
    "kind_plug": "Single-outlet smart plug.",
    "kind_bulb": "Bulb with color and/or white light control.",
    "kind_strip": "Multi-outlet strip; each outlet can be controlled separately.",
    "socket": "A single outlet on a power strip.",
    "rename": "Renames the device or outlet. The name is written to the hardware.",
    "status": "Shows the app’s latest operation status.",
    "lang": "Switches the UI language. Preference is saved on this PC.",
}

UI_HELP["lang"] = "Arayüz dilini değiştirir. Tercih bilgisayarında saklanır."

CATEGORIES_EN = {
    "Primary": "Primary",
    "Info": "Info",
    "Information": "Information",
    "Config": "Configuration",
    "Configuration": "Configuration",
    "Debug": "Debug",
    "Unknown": "Other",
}

TYPES_EN = {
    "Sensor": "Sensor",
    "BinarySensor": "Binary sensor",
    "Switch": "Switch",
    "Number": "Number",
    "Choice": "Choice",
    "Action": "Action",
    "Unknown": "Unknown",
}

LIGHT_FEATS_EN = {
    "brightness": "brightness",
    "hsv": "color (HSV)",
    "color_temp": "color temperature",
}

UNITS_EN = {
    "dBm": "dBm",
    "W": "W",
    "kWh": "kWh",
    "V": "V",
    "A": "A",
    "%": "%",
    "K": "K",
    "min": "min",
    "s": "s",
    "m": "m",
}


def feature_help(feature_id: str | None, name: str | None) -> str:
    from homepchub.i18n import get_lang

    if get_lang() == "en":
        if feature_id and feature_id in FEATURE_HELP_EN:
            return FEATURE_HELP_EN[feature_id]
        if name:
            key = name.strip().lower()
            if key in FEATURE_HELP_BY_NAME_EN:
                return FEATURE_HELP_BY_NAME_EN[key]
            if key in FEATURE_HELP_EN:
                return FEATURE_HELP_EN[key]
        label = feature_label(feature_id, name)
        return f"“{label}” is a feature reported by the device. Values are read live."

    if feature_id and feature_id in FEATURE_HELP:
        return FEATURE_HELP[feature_id]
    if name:
        key = name.strip().lower()
        if key in FEATURE_HELP_BY_NAME:
            return FEATURE_HELP_BY_NAME[key]
        if key in FEATURE_HELP:
            return FEATURE_HELP[key]
    label = feature_label(feature_id, name)
    return f"“{label}” cihazın bildirdiği bir özelliktir. Değer canlı olarak cihazdan okunur."


def ui_help(key: str) -> str:
    from homepchub.i18n import get_lang, t

    if key == "theme":
        return t("theme.help")
    if key == "lang":
        return t("lang.help")
    if get_lang() == "en":
        return UI_HELP_EN.get(key, "No extra description for this item.")
    return UI_HELP.get(key, "Bu öğe hakkında ek açıklama yok.")


def feature_label(feature_id: str | None, name: str | None) -> str:
    from homepchub.i18n import get_lang, t

    if get_lang() == "en":
        return name or feature_id or t("plug.feature")
    if feature_id and feature_id in FEATURE_IDS:
        return FEATURE_IDS[feature_id]
    if name:
        key = name.strip().lower()
        if key in FEATURE_NAMES:
            return FEATURE_NAMES[key]
        return name
    return feature_id or t("plug.feature")


def category_label(category: str | None) -> str:
    from homepchub.i18n import get_lang

    if not category:
        return ""
    if get_lang() == "en":
        return CATEGORIES_EN.get(category, category)
    return CATEGORIES.get(category, category)


def type_label(ftype: str | None) -> str:
    from homepchub.i18n import get_lang

    if not ftype:
        return ""
    if get_lang() == "en":
        return TYPES_EN.get(ftype, ftype)
    return TYPES.get(ftype, ftype)


def kind_label(kind: str | None) -> str:
    from homepchub.i18n import t

    if not kind:
        return "—"
    key = f"kind.{kind}"
    mapped = t(key)
    return mapped if mapped != key else kind


def light_feat_label(key: str) -> str:
    from homepchub.i18n import get_lang

    if get_lang() == "en":
        return LIGHT_FEATS_EN.get(key, key)
    return LIGHT_FEATS.get(key, key)


def unit_label(unit: str | None) -> str:
    from homepchub.i18n import get_lang

    if not unit:
        return ""
    if get_lang() == "en":
        return UNITS_EN.get(unit, unit)
    return UNITS.get(unit, unit)


def value_label(value) -> str:
    from homepchub.i18n import get_lang, t

    if value is None:
        return "—"
    if isinstance(value, bool):
        return t("yes") if value else t("no")
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "on"):
            return t("yes")
        if low in ("false", "no", "off"):
            return t("no")
        if low in ("none", "null", "n/a"):
            return "—"
        if get_lang() == "en":
            mapped = {
                "not set": "Not set",
                "unknown": "Unknown",
                "available": "Available",
                "unavailable": "Unavailable",
            }
        else:
            mapped = {
                "not set": "Ayarlanmamış",
                "unknown": "Bilinmiyor",
                "available": "Mevcut",
                "unavailable": "Yok",
            }
        if low in mapped:
            return mapped[low]
        return value
    if isinstance(value, float):
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return text
    return str(value)


def format_display(value, unit: str | None = None) -> str:
    text = value_label(value)
    u = unit_label(unit)
    if text == "—" or not u:
        return text
    return f"{text} {u}"
