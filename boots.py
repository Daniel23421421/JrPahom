from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, filters
)
import asyncio
import aiohttp
import requests
import xml.etree.ElementTree as ET
import re
import binascii
import json
import urllib3
import time
import uuid
import hmac
import hashlib
import base64

# Отключаем предупреждения urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Список прокси (в формате "http://ip:port" или "http://user:password@ip:port")
PROXIES = [

]
current_proxy = None  # Текущий используемый прокси

# Список разрешённых юзернеймов
ALLOWED_USERS = {"@staff_of_motel_free_california", "@kriscastanova", "@itsfatalfantasm", "@god_mode_support"}

# Константы для ConversationHandler
CHOOSING_PLATFORM, CHOOSING_ACTION, INPUT_CREDENTIALS, INPUT_HEX_BODY, INPUT_CYCLES, INPUT_CHAR_NUMBERS, CHOOSING_PACK, INPUT_PURCHASE_REQUESTS = range(8)

# API URLs
URLS = {
    "access": "https://mkx-api.wbagora.com/access",
    "end_krypt_run": "https://mkx-api.wbagora.com/ssc/invoke/end_krypt_run",
    "claim_share_reward": "https://mkx-api.wbagora.com/ssc/invoke/claim_share_reward",
    "start_krypt_run": "https://mkx-api.wbagora.com/ssc/invoke/start_krypt_run",
    "commerce_purchase": "https://mkx-api.wbagora.com/ssc/invoke/commerce_purchase_product",
    "commerce_begin": "https://mkx-api.wbagora.com/ssc/invoke/commerce_begin_purchase_product",
    "end_challenge_fight": "https://mkx-api.wbagora.com/ssc/invoke/skip_challenge_fight",
    "on_login": "https://mkx-api.wbagora.com/ssc/invoke/on_login",
    "open_krypt_tombstone": "https://mkx-api.wbagora.com/ssc/invoke/open_krypt_tombstone",
    "open_krypt_chest": "https://mkx-api.wbagora.com/ssc/invoke/open_krypt_chest",
    "conditional_offer_trigger": "https://mkx-api.wbagora.com/ssc/invoke/conditional_offer_trigger",
    "open_pack": "https://mkx-api.wbagora.com/ssc/invoke/open_pack",
    "resolve_pending_rewards": "https://mkx-api.wbagora.com/ssc/invoke/resolve_pending_rewards",
}

# Платформы
PLATFORMS = {
    "ios": {"api_key": "5be763d97d0f45a5aeed7dfddea43c22", "OSName": "iOS", "client-platform-type": "iOS"},
    "android": {"api_key": "e4555515fbec4df09407fe04cef2dd7d", "OSName": "Android", "client-platform-type": "Android"}
}

# Базовые заголовки
HEADERS_TEMPLATE = {
    "User-Agent": "MKMobile/++nrs_mobile_stream+MKM_Release_Candidate-CL-1377399 Android/9",
    "Connection": "keep-alive",
    "Accept": "application/x-ag-binary",
    "Accept-Encoding": "gzip, deflate, br",
    "accept-language": "ru",
    "app-version": "6.2.0",
    "client-os-version": "Android 9",
    "commerce-backend": "google-service",
    "device-id": "39a1a9dd902b3bb6c5ad74bf896d605a",
    "device-model": "1",
    "local-utc-offset": "2",
    "passcode": "Zb59bqRmvLqS",
    "x-hydra-client-id": "6f1c98d2-a908-486a-8c3b-1b2f04065ef8",
    "x-hydra-user-agent": "Hydra-Cpp/1.182.1",
    "Content-Type": "application/x-ag-binary",
}

# Тела запросов (HEX -> bytes)
HEX_BODIES = {
    "end_krypt_run": "6008300644696457696E02300E506C61796572506F736974696F6E6002300158110A300159110D301250726576506C61796572506F736974696F6E6002300158110A300159110C300D52657665616C656443656C6C73501E11501162116111511152115311541165116611781177118B119E119D11B0118A119C119B11AE11AF11C111D211C011AD11D111E311F511E211F411F33009546F6B656E446174616003300D4F6E6554696D65546F6B656E736000300D546F6B656E73546F436865636B6000300B546F6B656E73546F5365746000300C547261636B656454696D65736002300546696768746001300854696D657370616E301C2B30303030303030302E30303A30303A30302E30303030303030303030084E6F6E46696768746001300854696D657370616E301C2B30303030303030302E30303A30303A34352E363537303030303030300E5472617665727365644E6F6465735018115011621151115211531154116511661178118B119E119D118A119C11AE11AF11C111D211C011D111E311F511E211F430065F5F747970653016456E644B7279707452756E52657175657374426F6479",
    "start_krypt_run": "600930124B616D656F4368617261637465724E616D653000300E506C61796572506F736974696F6E6002300158110030015911003014506C617965725465616D43686172616374657273500330094B656E7368695F4230300845726D61635F4130300C4A61784272696767735F4230301250726576506C61796572506F736974696F6E600230015811003001591100301753656C65637465644B72797074446966666963756C74793005456C6465723009546F6B656E446174616003300D4F6E6554696D65546F6B656E536000300D546F6B656E73546F436865636B6000300B546F6B656E73546F5365746000300C547261636B656454696D65736000300E5472617665727365644E6F646573500030065F5F74797065301853746172744B7279707452756E52657175657374426F6479",
    "packs": "",
    "end_challenge_fight": "",
}
BODIES = {key: bytes.fromhex(value) for key, value in HEX_BODIES.items() if value}

HEX_BODY_STATIC_PART_1 = "600230046175746860023004555549443020"
HEX_BODY_STATIC_PART_2 = "300F6661696C5F6F6E5F6D697373696E670330076F7074696F6E735004300D636F6E66696775726174696F6E30076163636F756E74300770726F66696C65300D6E6F74696669636174696F6E73"

# Константы
MAP_SIZE = 18
HEARTS_PER_TOMBSTONE = 240
NUM_REQUESTS = 800
MAX_ATTEMPTS = 99


# Функция генерации подписи
def generate_hydra_signature(url, method=None, body=None, secret_key='fl^09VzmIL50AY#^t'):
    secret_bytes = bytes(secret_key, "utf-8")
    h = hmac.new(secret_bytes, digestmod=hashlib.sha1)
    h.update(url.encode('utf-8'))
    if method:
        h.update(method.encode('utf-8'))
    if body:
        if isinstance(body, str):
            h.update(body.encode('utf-8'))
        else:
            h.update(body)
    signature = base64.b64encode(h.digest()).decode('utf-8')
    return signature

# Список персонажей с номерами
CHARACTERS = [
    (2, "Baraka_A"), (3, "Baraka_LZ"), (4, "BoRaiChoDLC_A"), (5, "CassieCage_A3"), (6, "CassieCage_B0"),
    (7, "CassieCage_F"), (8, "CassieCage_O"), (9, "CassieCage_Punk"), (10, "Dvorah_A2"), (11, "Dvorah_A3"),
    (12, "Dvorah_B0"), (13, "Dvorah_L_D"), (14, "Ermac_A0"), (15, "Ermac_B2"), (16, "Ermac_B3"),
    (17, "Ermac_H"), (18, "Ermac_N"), (19, "ErronBlack_A1"), (20, "ErronBlack_DD"), (21, "ErronBlack_L_D"),
    (22, "FreddyKrueger_A"), (23, "Fujin_11_PR"), (24, "Fujin_ONS"), (25, "Goro_A"), (26, "Goro_B"),
    (27, "JacquiBriggs_A"), (28, "JacquiBriggs_B0"), (29, "JacquiBriggs_N"), (30, "JacquiBriggs_O"),
    (31, "Jade_11_RV"), (32, "Jade_A"), (33, "Jade_DD"), (34, "Jade_KL"), (35, "Jade_LZ"),
    (36, "JasonVoorhees_A1"), (37, "JasonVoorhees_B2"), (38, "JasonVoorhees_C"), (39, "JaxBriggs_A1"),
    (40, "JaxBriggs_B0"), (41, "JaxBriggs_C3"), (42, "JaxBriggs_M0"), (43, "JaxBriggs_ONS"),
    (44, "JaxBriggs_Y"), (45, "JohnnyCage_A0"), (46, "JohnnyCage_B"), (47, "JohnnyCage_C2"),
    (48, "JohnnyCage_C3"), (49, "JohnnyCage_F"), (50, "JohnnyCage_M0"), (51, "JohnnyCage_MV"),
    (52, "Joker_AK"), (53, "Kabal_11_BD"), (54, "Kabal_11_PR"), (55, "Kano_A1"), (56, "Kano_A3"),
    (57, "Kano_B0"), (58, "Kano_T"), (59, "Kenshi_A1"), (60, "Kenshi_A2"), (61, "Kenshi_B0"),
    (62, "Kenshi_E"), (63, "Kenshi_F3"), (64, "Kenshi_MK1"), (65, "Kintaro"), (66, "Kitana_A2"),
    (67, "Kitana_B3"), (68, "Kitana_C0"), (69, "Kitana_DD"), (70, "Kitana_ED"), (71, "Kitana_F"),
    (72, "Kitana_M0"), (73, "KotalKahn_A1"), (74, "KotalKahn_A3"), (75, "KotalKahn_B0"),
    (76, "KotalKahn_E"), (77, "KungJin_A2"), (78, "KungJin_A3"), (79, "KungJin_B0"), (80, "KungJin_E"),
    (81, "KungLao_9A"), (82, "KungLao_A2"), (83, "KungLao_B3"), (84, "KungLao_C0"), (85, "Leatherface_B"),
    (86, "LinKuei_A0"), (87, "LiuKang_11_FG"), (88, "LiuKang_11_PR"), (89, "LiuKang_A1"),
    (90, "LiuKang_E"), (91, "LiuKang_T_D"), (92, "Mileena_A1"), (93, "Mileena_C1_D"), (94, "Mileena_H"),
    (95, "Mileena_M"), (96, "Mileena_MK1"), (97, "Nightwolf_11_PR"), (98, "Nightwolf_COS"),
    (99, "Noob_11_PR"), (100, "Noob_BAT"), (101, "Noob_KL"), (102, "Noob_LZ"), (103, "Oni_A0"),
    (104, "OshTekk_A0"), (105, "QuanChi_A2"), (106, "QuanChi_B3"), (107, "Raiden_11_PR"),
    (108, "Raiden_A1"), (109, "Raiden_B_D"), (110, "Raiden_C0"), (111, "Raiden_I2"), (112, "Raiden_MV"),
    (113, "Rain_11_PR"), (114, "Rain_ED"), (115, "Rain_KL"), (116, "Reptile_A2"), (117, "Reptile_A3"),
    (118, "Reptile_B0"), (119, "Reptile_H"), (120, "Reptile_N"), (121, "Saurian_A0"), (122, "Scorpion_11_PR"),
    (123, "Scorpion_A1"), (124, "Scorpion_A3"), (125, "Scorpion_B0"), (126, "Scorpion_C"),
    (127, "Scorpion_J"), (128, "Scorpion_M0"), (129, "Scorpion_MK1"), (130, "Scorpion_N0"),
    (131, "Scorpion_N1_D"), (132, "Scorpion_S0"), (133, "ShangTsung_11_PR"), (134, "ShangTsung_KL"),
    (135, "ShangTsung_MK1"), (136, "ShaoKahn_K"), (137, "Shinnok_A"), (138, "Shinnok_B"),
    (139, "ShiraiRyu_A0"), (140, "Sindel_11_PR"), (141, "Sindel_ED"), (142, "Skarlet_11_BR"),
    (143, "Skarlet_11_PR"), (144, "Skarlet_K"), (145, "Smoke_KL"), (146, "Smoke_MK1"),
    (147, "SonyaBlade_A2"), (148, "SonyaBlade_A3"), (149, "SonyaBlade_C0"), (150, "SonyaBlade_F"),
    (151, "SonyaBlade_K1"), (152, "SonyaBlade_MV"), (153, "SonyaBlade_T"), (154, "Spawn_11_PR"),
    (155, "SpecialForces_F0"), (156, "SpecialForces_M0"), (157, "SubZero_11_PR"), (158, "SubZero_A0"),
    (159, "SubZero_B1"), (160, "SubZero_B3"), (161, "SubZero_C2"), (162, "SubZero_K"),
    (163, "SubZero_N0"), (164, "SubZero_ONS"), (165, "Takeda_B"), (166, "Takeda_B3"),
    (167, "Tanya_A"), (168, "Tanya_B"), (169, "Tanya_P"), (170, "Terminator_101"), (171, "Terminator_DF"),
    (172, "Tremor_A"), (173, "Tremor_BD"), (174, "Triborg_CY"), (175, "Triborg_SK"), (176, "Triborg_SM"),
    (177, "Triborg_SZ"), (178, "WhiteLotus_A0")
]

CHAR_DICT = {num: code for num, code in CHARACTERS}

# Параметры наборов
PACKS = {
    "РАННИЙ ДОСТУП (МИЛИНА ИЗ МК1)": {"ProductSlug": "dso-s15-mk1-mileena-early-access", "PriceSlug": "dso-s15-mk1-mileena-early-access-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "РАННИЙ ДОСТУП (КЛАССИК СКАРЛЕТ)": {"ProductSlug": "dso-klassic-skarlet-early-access", "PriceSlug": "dso-klassic-skarlet-early-access-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "СЕРЕБРЯНЫЙ НАБОР": {"ProductSlug": "standard-booster-pack", "PriceSlug": "standard-booster-pack-hydra", "ExpectedInventoryItemSlug": "koin", "ExpectedQuantity": 30000},
    "НАБОР НОВИЧКА (500 ДУШ + ЗОЛОТО)": {"ProductSlug": "new-fighter-gold-pack1", "PriceSlug": "new-fighter-gold-pack-1-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "ЯЩИК С БАРАХЛОМ ИЗ КРИПТЫ": {"ProductSlug": "krypt-junk-box", "PriceSlug": "krypt-junk-box-hydra", "ExpectedInventoryItemSlug": "krypt-hearts", "ExpectedQuantity": 100},
    "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 1": {"ProductSlug": "new-fighter-diamond-pack1", "PriceSlug": "new-fighter-diamond-pack-1-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 2": {"ProductSlug": "new-fighter-diamond-pack2", "PriceSlug": "new-fighter-diamond-pack-2-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 3": {"ProductSlug": "new-fighter-diamond-pack3", "PriceSlug": "new-fighter-diamond-pack-3-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 4": {"ProductSlug": "new-fighter-diamond-pack4", "PriceSlug": "new-fighter-diamond-pack-4-hydra", "ExpectedInventoryItemSlug": "free-product-credit", "ExpectedQuantity": 1},
    "НАБОР ИСПЫТАНИЯ": {"ProductSlug": "challenge-booster-pack", "PriceSlug": "challenge-booster-pack-hydra", "ExpectedInventoryItemSlug": "soul", "ExpectedQuantity": 300},
    "НАБОР СНАРЯЖЕНИЯ": {"ProductSlug": "equipment-booster-pack", "PriceSlug": "equipment-booster-pack-hydra", "ExpectedInventoryItemSlug": "koin", "ExpectedQuantity": 70000},
    "ПРИЗЫВ КАМЕО": {"ProductSlug": "kameo-summon-pack", "PriceSlug": "kameo-summon-pack-hydra", "ExpectedInventoryItemSlug": "dragon-krystals", "ExpectedQuantity": 15},
    "ПРИЗЫВ СНАРЯЖЕНИЯ КРИПТЫ": {"ProductSlug": "krypt-equipment-summon-pack", "PriceSlug": "krypt-equipment-summon-pack-hydra", "ExpectedInventoryItemSlug": "dragon-krystals", "ExpectedQuantity": 15},
    "ЗОЛОТОЙ НАБОР (150 ДУШ)": {"ProductSlug": "premium-booster-pack", "PriceSlug": "premium-booster-pack-hydra", "ExpectedInventoryItemSlug": "soul", "ExpectedQuantity": 150},
    "АЛМАЗНЫЙ ЛАРЕЦ": {"ProductSlug": "kollectors-diamond-kasket", "PriceSlug": "kollectors-diamond-kasket-hydra", "ExpectedInventoryItemSlug": "dragon-krystals", "ExpectedQuantity": 400},
    "ЗОЛОТОЙ ЛАРЕЦ": {"ProductSlug": "kollectors-gold-kasket", "PriceSlug": "kollectors-gold-kasket-hydra", "ExpectedInventoryItemSlug": "dragon-krystals", "ExpectedQuantity": 300},
    "ЭПИЧЕСКИЙ ЛАРЕЦ": {"ProductSlug": "epic-equipment-kasket", "PriceSlug": "epic-equipment-kasket-hydra", "ExpectedInventoryItemSlug": "dragon-krystals", "ExpectedQuantity": 350},
    "РЕДКИЙ ЛАРЕЦ": {"ProductSlug": "rare-equipment-kasket", "PriceSlug": "rare-equipment-kasket-hydra", "ExpectedInventoryItemSlug": "dragon-krystals", "ExpectedQuantity": 250},
    "Купить монеты (1 500 000)": {"ProductSlug": "koin-pack-6", "PriceSlug": "koin-pack-6-hydra", "ExpectedInventoryItemSlug": "soul", "ExpectedQuantity": 2000},
}

# SOAP-аутентификация
def get_account_id(email: str, password: str):
    url = "https://tokenservice.psn.turbine.com/TokenService/AuthenticatorService.svc"
    headers = {
        "Host": "tokenservice.psn.turbine.com",
        "Accept": "*/*",
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://www.wbie.com/wbnet/contracts/authentication/IAuthenticationValidationContract/AuthenticateViaCredentials",
        "Content-Length": "584"
    }
    body = f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <AuthenticateViaCredentials xmlns="http://www.wbie.com/wbnet/contracts/authentication">
      <ValidationInfo xmlns:x="http://www.wbie.com/wbnet/data/authentication">
        <x:Identity>{email}</x:Identity>
        <x:Product>malcolm</x:Product>
        <x:Realm>WBID</x:Realm>
        <x:Secret>{password}</x:Secret>
      </ValidationInfo>
    </AuthenticateViaCredentials>
  </soap:Body>
</soap:Envelope>'''
    response = requests.post(url, headers=headers, data=body, verify=False)
    if response.status_code == 200:
        root = ET.fromstring(response.text)
        namespace = {'a': 'http://www.wbie.com/wbnet/data/authentication'}
        account_id_elem = root.find('.//a:AccountId', namespace)
        if account_id_elem is not None:
            return account_id_elem.text.replace("-", "")
        return None
    return None

# Получение access-токена
async def get_access_token(uuid: str, platform: str, use_proxy=False):
    formatted_uuid = uuid.replace("-", "").lower()
    if len(formatted_uuid) != 32:
        return None
    uuid_bytes = formatted_uuid.encode("utf-8").hex()
    full_hex_body = HEX_BODY_STATIC_PART_1 + uuid_bytes + HEX_BODY_STATIC_PART_2
    hex_body_bytes = binascii.unhexlify(full_hex_body)
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "false",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    headers["x-hydra-signature"] = generate_hydra_signature('/access', 'POST', hex_body_bytes)
    global current_proxy
    proxy_to_use = current_proxy if use_proxy else None

    for attempt in range(MAX_ATTEMPTS):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(URLS["access"], headers=headers, data=hex_body_bytes, proxy=proxy_to_use, ssl=False) as response:
                    if response.status == 200:
                        body = await response.read()
                        decoded_body = body.decode("latin1", errors="ignore")
                        match = re.search(r"RLO[a-zA-Z0-9+/=]+", decoded_body)
                        if match:
                            return match.group(0).rstrip("0")
                    elif response.status == 403:
                        print("Аккаунт заблокирован.")
                        return None
                    elif response.status == 417:
                        print("Не удалось начать фарм. Возможно, на аккаунте недостаточное количество ключей.")
                        return None
                    elif response.status == 429:
                        print(f"429 Too Many Requests при получении токена. Переключаем прокси и ждём 10 секунд...")
                        if use_proxy and PROXIES:
                            update_current_proxy()
                            proxy_to_use = current_proxy
                        await asyncio.sleep(5)
                        continue
                    else:
                        print(f"❌ Ошибка получения токена: {response.status}")
                        return None
        except aiohttp.ClientConnectionError as e:
            print(f"Ошибка подключения через прокси {proxy_to_use}: {e}. Переключаем прокси...")
            if use_proxy and PROXIES:
                update_current_proxy()
                proxy_to_use = current_proxy
            await asyncio.sleep(5)
            continue
    print("Превышено максимальное число попыток получения токена.")
    return None

def update_current_proxy():
    global current_proxy
    if PROXIES:
        current_proxy = format_proxy(random.choice([p for p in PROXIES if format_proxy(p) != current_proxy]))
        print(f"Переключён прокси: {current_proxy}")
    else:
        current_proxy = None

# Асинхронная отправка запросов с таймаутом
async def run_requests_with_timeout(request_type, num_requests, method, timeout, token, platform, use_proxy=False):
    url = URLS[request_type]
    body = BODIES[request_type] if request_type in BODIES else None
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "true",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    if body:
        headers["Content-Length"] = str(len(body))
    headers["x-hydra-signature"] = generate_hydra_signature(f'/ssc/invoke/{request_type}', method, body)
    success_counter = {"success": 0}
    semaphore = asyncio.Semaphore(900)
    connector = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [send_request(session, req_id, url, method, headers, body, semaphore, success_counter, use_proxy=use_proxy)
                 for req_id in range(1, num_requests + 1)]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"\n⏳ Время выполнения {request_type} запросов истекло ({timeout} сек).")
    return f"✅ Успешных запросов: {success_counter['success']} из {num_requests}"

async def send_request(session, req_id, url, method, headers, body, semaphore, success_counter, max_attempts=3, use_proxy=False):
    global current_proxy
    proxy_to_use = current_proxy if use_proxy else None
    async with semaphore:
        for attempt in range(max_attempts):
            try:
                async with session.request(method, url, headers=headers, data=body, proxy=proxy_to_use, ssl=False) as resp:
                    status = resp.status
                    if status == 403:
                        print(f"Запрос {req_id} - Аккаунт заблокирован.")
                        return
                    elif status == 417:
                        print(f"Запрос {req_id} - Не удалось начать фарм.")
                        return
                    elif status == 429:
                        print(f"Запрос {req_id} - 429 Too Many Requests. Переключаем прокси и ждём 10 секунд...")
                        if use_proxy and PROXIES:
                            update_current_proxy()
                            proxy_to_use = current_proxy
                        await asyncio.sleep(5)
                        continue
                    else:
                        print(f"Запрос {req_id} - Статус {status}")
                        if status == 200:
                            success_counter["success"] += 1
                        return
            except aiohttp.ClientConnectionError as e:
                print(f"Запрос #{req_id} - Ошибка подключения через прокси {proxy_to_use}: {e}. Переключаем прокси...")
                if use_proxy and PROXIES:
                    update_current_proxy()
                    proxy_to_use = current_proxy
                await asyncio.sleep(5)
                continue
    print(f"Запрос {req_id} - Превышено максимальное число попыток.")

# Функция для покупки набора с учетом количества purchase запросов
def generate_token():
    """Генерирует 32-символьный токен (HEX) в верхнем регистре."""
    return uuid.uuid4().hex.upper()

async def purchase_pack(uuid: str, platform: str, pack_name: str, cycles: int, num_purchase_requests: int):
    pack = PACKS[pack_name]
    product_quantity = 1 if pack_name in [
        "РАННИЙ ДОСТУП (МИЛИНА ИЗ МК1)",
        "НАБОР НОВИЧКА (500 ДУШ + ЗОЛОТО)",
        "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 1",
        "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 2",
        "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 3",
        "АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 4"
        "РАННИЙ ДОСТУП (КЛАССИК СКАРЛЕТ)"
    ] else 10

    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "false",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    })

    total_successful = 0
    results_by_cycle = []
    receipt_type = "IOS" if platform == "ios" else "Android"

    for cycle in range(1, cycles + 1):
        token = await get_access_token(uuid, platform)
        if not token:
            cycle_result = f"Цикл {cycle}: Не удалось получить токен"
            print(cycle_result)
            results_by_cycle.append(cycle_result)
            await asyncio.sleep(0)
            continue

        headers["x-hydra-access-token"] = token

        # Генерация begin-токена для цикла
        begin_token = generate_token()
        begin_payload = {
            "ProductQuantity": product_quantity,
            "ProductSlug": pack["ProductSlug"],
            "TokenData": {
                "OneTimeTokens": {"CommerceBeginPurchaseRequest": begin_token},
                "TokensToCheck": {},
                "TokensToSet": {}
            },
            "__type": "CommerceBeginPurchaseRequestBody"
        }
        begin_json = json.dumps(begin_payload)
        headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/commerce_begin_purchase_product', 'POST', begin_json)

        async with aiohttp.ClientSession() as session:
            async with session.post(URLS["commerce_begin"], headers=headers, data=begin_json, ssl=False) as begin_resp:
                if begin_resp.status != 200:
                    cycle_result = f"Цикл {cycle}: Ошибка начала покупки: {begin_resp.status}"
                    print(cycle_result)
                    results_by_cycle.append(cycle_result)
                    continue

            purchase_payload = {
                "BypassBackend": 0,
                "ExpectedInventoryItemSlug": pack["ExpectedInventoryItemSlug"],
                "ExpectedQuantity": pack["ExpectedQuantity"],
                "IAPCurrencyCode": "0",
                "IAPCurrencyPrice": 0,
                "IAPPurchaseState": 1,
                "IAPTransactionId": "0",
                "PriceSlug": pack["PriceSlug"],
                "ProductQuantity": product_quantity,
                "ProductSlug": pack["ProductSlug"],
                "ReceiptType": receipt_type,
                "Sales": 0,
                "SingularParameters": {"ANDI": "453ac869fa0f7dd00"},
                "AdvertisingID": "b1b4f925-40b1-4c13-8e4e-2e34147a757e",
                "IDFV": "0",
                "TokenData": {
                    "OneTimeTokens": {"CommercePurchaseProductRequest": begin_token},
                    "TokensToCheck": {},
                    "TokensToSet": {}
                },
                "__type": "CommercePurchaseProductRequestBody"
            }
            purchase_json = json.dumps(purchase_payload)
            headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/commerce_purchase_product', 'POST', purchase_json)

            tasks = [session.post(URLS["commerce_purchase"], headers=headers, data=purchase_json, ssl=False)
                     for _ in range(num_purchase_requests)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            successful_in_cycle = sum(1 for resp in responses if not isinstance(resp, Exception) and resp.status == 200)
            cycle_result = f"Цикл {cycle}: Успешных запросов: {successful_in_cycle} из {num_purchase_requests}"
            print(cycle_result)
            results_by_cycle.append(cycle_result)
            total_successful += successful_in_cycle

    final_result = "\n".join(results_by_cycle)
    if cycles > 1:
        final_result += f"\nОбщее количество успешных запросов: {total_successful} из {cycles * num_purchase_requests}"
    print(final_result)
    return final_result


async def run_end_krypt_run(uuid: str, platform: str):
    headers_end = headers.copy()
    headers_end["Content-Type"] = "application/x-ag-binary"
    headers_end["Accept"] = "application/x-ag-binary"
    headers_end["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/end_krypt_run', 'PUT', END_KRYPT_BODY)
    print(f"Подпись для end_krypt_run #{req_id}: {headers_end['x-hydra-signature']}")

    async with session.put(URLS["end"], headers=headers_end, data=END_KRYPT_BODY, ssl=False) as response:
        body = await response.read()
        print(f"Request #{req_id}: Статус: {response.status}, Ответ: {body}")
        return response.status == 200

async def run_keys_to_krystals(uuid: str, platform: str, cycles: int):
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "true",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    successful_cycles = 0
    start_krypt_run_count = 0

    for cycle in range(1, cycles + 1):
        print(f"\n=== Цикл #{cycle} ===")
        token = await get_access_token(uuid, platform)
        if not token:
            print("❌ Не удалось получить токен в цикле", cycle)
            await asyncio.sleep(5)
            continue
        headers["x-hydra-access-token"] = token

        start_krypt_run_count += 1
        print(f"🔑 Потрачено ключей крипты: {start_krypt_run_count}")
        await run_requests_with_timeout("start_krypt_run", 1, "POST", 33, token, platform)
        end_result = await run_requests_with_timeout("end_krypt_run", NUM_REQUESTS, "PUT", 15, token, platform)
        if "Успешных запросов" in end_result and int(end_result.split(":")[1].split()[0]) > 0:
            successful_cycles += 1
            print(f"Цикл {cycle}: Забег завершён и умножен ✅")
        else:
            print(f"Цикл {cycle}: Ошибка завершения забега 🚫")
        if cycle < cycles:
            print("⏳ Ожидание 10 секунд до следующего цикла...")
            await asyncio.sleep(5)

    return f"✅ Успешных циклов: {successful_cycles} из {cycles}"


import random

# Функция для преобразования формата прокси
def format_proxy(proxy_str):
    ip, port, username, password = proxy_str.split(":")
    return f"http://{username}:{password}@{ip}:{port}"

async def run_open_tombstone(uuid: str, platform: str, cycles: int, char_numbers: list):
    global current_proxy
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "true",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    total_tombstones = 0
    total_hearts = 0
    multiplied_runs = 0
    player_team = [CHAR_DICT[num] for num in char_numbers]

    # Инициализация прокси
    if PROXIES:
        update_current_proxy()
    else:
        current_proxy = None

    for cycle in range(1, cycles + 1):
        print(f"\n=== Цикл #{cycle} ===")
        # Используем прокси для получения токена
        token = await get_access_token(uuid, platform, use_proxy=True)
        if not token:
            print("❌ Не удалось получить токен в цикле", cycle)
            await asyncio.sleep(5)
            continue
        headers["x-hydra-access-token"] = token

        # Используем прокси для start_krypt_run
        start_headers = headers.copy()
        start_headers["Content-Type"] = "application/json"
        start_headers["Accept"] = "application/json"
        start_payload = {
            "KameoCharacterName": "",
            "PlayerPosition": {"X": 0, "Y": 0},
            "PlayerTeamCharacters": player_team,
            "PrevPlayerPosition": {"X": 0, "Y": 0},
            "SelectedKryptDifficulty": "Elder",
            "TokenData": {"OneTimeTokens": {}, "TokensToCheck": {}, "TokensToSet": {}},
            "TrackedTimes": {},
            "TraversedNodes": [],
            "__type": "StartKryptRunRequestBody"
        }
        start_json = json.dumps(start_payload)
        start_headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/start_krypt_run', 'POST', start_json)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    URLS["start_krypt_run"],
                    headers=start_headers,
                    data=start_json,
                    proxy=current_proxy,  # Прокси для start_krypt_run
                    ssl=False
            ) as start_resp:
                if start_resp.status != 200:
                    print(f"❌ Ошибка старта забега: {start_resp.status}")
                    if start_resp.status == 429:
                        print("429 Too Many Requests для start_krypt_run. Переключаем прокси...")
                        update_current_proxy()
                    continue

            # Открытие гробниц без прокси
            print("\n🔍 Поиск эпических гробниц на карте 18x18...")
            tasks = [open_tombstone(session, headers, x, y) for x in range(MAP_SIZE) for y in range(MAP_SIZE)]
            results = await asyncio.gather(*tasks)
            successful_opens = [r for r in results if r and "✅" in r]
            cycle_tombstones = len(successful_opens)
            total_tombstones += cycle_tombstones
            total_hearts += cycle_tombstones * HEARTS_PER_TOMBSTONE
            print(f"\n📝 Найдено {cycle_tombstones} эпических гробниц:")
            if successful_opens:
                print("\n".join(successful_opens))
            else:
                print("🚫 Гробницы не найдены.")

        # Используем прокси для end_krypt_run
        update_current_proxy()  # Переключаем прокси перед end_krypt_run
        end_result = await run_requests_with_timeout("end_krypt_run", NUM_REQUESTS, "PUT", 15, token, platform, use_proxy=True)
        if "Успешных запросов" in end_result and int(end_result.split(":")[1].split()[0]) > 0:
            multiplied_runs += 1
            print(f"Цикл {cycle}: Забег завершён и умножен ✅")
        else:
            print(f"Цикл {cycle}: Ошибка завершения забега 🚫")
        if cycle < cycles:
            print("⏳ Ожидание 10 секунд до следующего цикла...")
            await asyncio.sleep(5)

    return (
        f"📊 Итоговая статистика:\n"
        f"🪦 Всего найдено эпических гробниц: {total_tombstones}\n"
        f"❤️ Всего получено сердец: {total_hearts}\n"
        f"🔄 Всего походов умножено: {multiplied_runs} из {cycles}"
    )


async def send_end_krypt_request(session, req_id, url, headers, body, semaphore, success_counter):
    global current_proxy
    async with semaphore:
        for attempt in range(MAX_ATTEMPTS):
            try:
                async with session.put(url, headers=headers, data=body, proxy=current_proxy, ssl=False) as resp:
                    status = resp.status
                    if status == 200:
                        success_counter["success"] += 1
                        print(f"Запрос #{req_id}: Успешно (200)")
                        return
                    elif status == 429:
                        print(f"Запрос #{req_id}: 429 Too Many Requests. Переключаем прокси...")
                        if PROXIES:
                            current_proxy = format_proxy(random.choice([p for p in PROXIES if format_proxy(p) != current_proxy]))
                            print(f"Новый прокси: {current_proxy}")
                        await asyncio.sleep(5)
                        continue
                    elif status == 403:
                        print(f"Запрос #{req_id}: Аккаунт заблокирован (403)")
                        return
                    elif status == 417:
                        print(f"Запрос #{req_id}: Не удалось завершить (417)")
                        return
                    else:
                        print(f"Запрос #{req_id}: Ошибка {status}")
                        return
            except aiohttp.ClientProxyError as e:
                print(f"Запрос #{req_id}: Ошибка прокси {current_proxy}: {e}. Переключаем прокси...")
                if PROXIES:
                    current_proxy = format_proxy(random.choice([p for p in PROXIES if format_proxy(p) != current_proxy]))
                    print(f"Новый прокси: {current_proxy}")
                await asyncio.sleep(5)
                continue
            except aiohttp.ClientConnectorError as e:
                print(f"Запрос #{req_id}: Ошибка подключения: {e}. Переключаем прокси...")
                if PROXIES:
                    current_proxy = format_proxy(random.choice([p for p in PROXIES if format_proxy(p) != current_proxy]))
                    print(f"Новый прокси: {current_proxy}")
                await asyncio.sleep(5)
                continue
        print(f"Запрос #{req_id}: Превышено максимальное число попыток.")

async def run_open_chest(uuid: str, platform: str, cycles: int):
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "true",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    total_chests = 0
    multiplied_runs = 0

    for cycle in range(1, cycles + 1):
        print(f"\n=== Цикл #{cycle} ===")
        token = await get_access_token(uuid, platform)
        if not token:
            print("❌ Не удалось получить токен в цикле", cycle)
            await asyncio.sleep(5)
            continue
        headers["x-hydra-access-token"] = token

        # Старт забега
        start_headers = headers.copy()
        start_headers["Content-Type"] = "application/json"
        start_headers["Accept"] = "application/json"
        start_payload = {
            "KameoCharacterName": "",
            "PlayerPosition": {"X": 0, "Y": 0},
            "PlayerTeamCharacters": ["Ermac_A0", "JaxBriggs_B0", "Kenshi_B0"],
            "PrevPlayerPosition": {"X": 0, "Y": 0},
            "SelectedKryptDifficulty": "Elder",
            "TokenData": {"OneTimeTokens": {}, "TokensToCheck": {}, "TokensToSet": {}},
            "TrackedTimes": {},
            "TraversedNodes": [],
            "__type": "StartKryptRunRequestBody"
        }
        start_json = json.dumps(start_payload)
        start_headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/start_krypt_run', 'POST', start_json)

        async with aiohttp.ClientSession() as session:
            async with session.post(URLS["start_krypt_run"], headers=start_headers, data=start_json, ssl=False) as start_resp:
                if start_resp.status != 200:
                    print(f"❌ Ошибка старта забега: {start_resp.status}")
                    continue

            # Открытие сундуков
            print("\n🔍 Поиск эпических сундуков на карте 18x18...")
            tasks = [open_chest(session, headers, x, y) for x in range(MAP_SIZE) for y in range(MAP_SIZE)]
            results = await asyncio.gather(*tasks)
            successful_opens = [r for r in results if r and "✅" in r]
            cycle_chests = len(successful_opens)
            total_chests += cycle_chests
            print(f"\n📝 Найдено {cycle_chests} эпических сундуков:")
            if successful_opens:
                print("\n".join(successful_opens))
            else:
                print("🚫 Сундуки не найдены.")

            # Завершение забега одним запросом
            print("\n🔚 Завершение забега...")
            end_headers = headers.copy()
            end_body = BODIES["end_krypt_run"]
            end_headers.update({
                "Content-Length": str(len(end_body)),
                "Content-Type": "application/x-ag-binary",
                "Accept": "application/x-ag-binary",
            })
            end_headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/end_krypt_run', 'PUT', end_body)

            async with session.put(URLS["end_krypt_run"], headers=end_headers, data=end_body, ssl=False) as end_resp:
                body = await end_resp.read()
                print(f"Статус end_krypt_run: {end_resp.status}")
                if end_resp.status == 200:
                    multiplied_runs += 1
                    print(f"Цикл {cycle}: Забег завершён и умножен ✅")
                else:
                    print(f"Цикл {cycle}: Ошибка завершения забега 🚫 (Статус: {end_resp.status})")

        if cycle < cycles:
            print("⏳ Ожидание 10 секунд перед следующим циклом...")
            await asyncio.sleep(5)

    return (
        f"📊 Итоговая статистика:\n"
        f"📦 Всего открыто эпических сундуков: {total_chests}\n"
        f"🔄 Всего походов умножено: {multiplied_runs} из {cycles}"
    )

async def open_tombstone(session, headers, x, y, max_attempts=MAX_ATTEMPTS):
    payload_open = {
        "ContainerRarity": "Epic",
        "KryptPositionIndex": 0,
        "PlayerPosition": {"X": x, "Y": y},
        "PrevPlayerPosition": {"X": max(0, x - 1), "Y": max(0, y - 1)},
        "TokenData": {"OneTimeTokens": {}, "TokensToCheck": {}, "TokensToSet": {}},
        "TrackedTimes": {
            "Fight": {"Timespan": "+00000000.00:00:00.000000000"},
            "NonFight": {"Timespan": "+00000000.00:00:02.000000000"}
        },
        "TraversedNodes": [x * MAP_SIZE + y],
        "__type": "OpenKryptTombstoneRequestBody"
    }
    headers_open = headers.copy()
    headers_open["Content-Type"] = "application/json"
    headers_open["Accept"] = "application/json"
    json_data = json.dumps(payload_open)
    headers_open["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/open_krypt_tombstone', 'PUT', json_data)

    for attempt in range(max_attempts):
        try:
            async with session.put(URLS["open_krypt_tombstone"], headers=headers_open, data=json_data, ssl=False) as response:
                if response.status == 200:
                    return f"✅ Гробница открыта в X: {x}, Y: {y}"
                elif response.status == 400:
                    return None
                elif response.status == 409:
                    if attempt < max_attempts - 1:
                        print(f"🔁 Повторная попытка ({attempt + 1}) в X: {x}, Y: {y} из-за 409...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        return None
                elif response.status == 429:
                    print(f"🔄 429 Too Many Requests в X: {x}, Y: {y}. Ждём 10 секунд...")
                    await asyncio.sleep(5)
                    continue
                else:
                    return None
        except aiohttp.ClientConnectorError as e:
            print(f"Ошибка подключения в X: {x}, Y: {y}: {e}. Ждём 5 секунд...")
            await asyncio.sleep(5)
            continue
    return None

async def open_chest(session, headers, x, y, max_attempts=MAX_ATTEMPTS):
    payload_open = {
        "ContainerRarity": "Epic",
        "KryptPositionIndex": 0,
        "PlayerPosition": {"X": x, "Y": y},
        "PrevPlayerPosition": {"X": max(0, x - 1), "Y": max(0, y - 1)},
        "TokenData": {"OneTimeTokens": {}, "TokensToCheck": {}, "TokensToSet": {}},
        "TrackedTimes": {
            "Fight": {"Timespan": "+00000000.00:00:00.000000000"},
            "NonFight": {"Timespan": "+00000000.00:00:02.000000000"}
        },
        "TraversedNodes": [x * MAP_SIZE + y],
        "__type": "OpenKryptChestRequestBody"
    }
    headers_open = headers.copy()
    headers_open["Content-Type"] = "application/json"
    headers_open["Accept"] = "application/json"
    json_data = json.dumps(payload_open)
    headers_open["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/open_krypt_chest', 'PUT', json_data)

    for attempt in range(max_attempts):
        try:
            async with session.put(URLS["open_krypt_chest"], headers=headers_open, data=json_data, ssl=False) as response:
                if response.status == 200:
                    return f"✅ Сундук открыт в X: {x}, Y: {y}"
                elif response.status == 400:
                    return None
                elif response.status == 409:
                    if attempt < max_attempts - 1:
                        print(f"🔁 Повторная попытка ({attempt + 1}) в X: {x}, Y: {y} из-за 409...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        return None
                elif response.status == 429:
                    print(f"🔄 429 Too Many Requests в X: {x}, Y: {y}. Ждём 10 секунд...")
                    await asyncio.sleep(5)
                    continue
                else:
                    return None
        except aiohttp.ClientConnectorError as e:
            print(f"Ошибка подключения: {e}. Ждём 5 секунд...")
            await asyncio.sleep(5)
            continue
    return None

async def end_krypt_run(session, headers, req_id):
    async with session.put(URLS["end_krypt_run"], headers=headers, data=BODIES["end_krypt_run"], ssl=False) as response:
        body = await response.read()
        print(f"Request #{req_id}: Статус: {response.status}, Ответ: {body}")
        return response.status == 200

async def run_custom_script(action: str, token: str, platform: str, body: bytes, proxy=None, timeout=60):
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "Content-Length": str(len(body)),
        "x-hydra-compress-response": "true",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    method = "POST" if action in ["packs", "start_krypt_run"] else "PUT"
    headers["x-hydra-signature"] = generate_hydra_signature(f'/ssc/invoke/{action}', method, body)
    success_counter = {"success": 0}
    connector = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            send_request(
                session,
                req_id,
                URLS[action],
                method,
                headers,
                body,
                asyncio.Semaphore(900),
                success_counter
            )
            for req_id in range(1, NUM_REQUESTS + 1)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    return f"✅ Успешных запросов: {success_counter['success']} из {NUM_REQUESTS}"

async def get_account_stats(uuid: str, platform: str):
    token = await get_access_token(uuid, platform)
    if not token:
        return "❌ Не удалось получить токен."

    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "x-hydra-compress-response": "false",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
        "x-hydra-client-id": "371e50b2-3e88-4a26-a627-d8bc01cc14d9",
    })
    timestamp_ms = int(time.time() * 1000)
    payload = {
        "CountryCode": "RU",
        "DeviceModel": "IPHONESE",
        "LocalTime": f"/Date({timestamp_ms})/",
        "OSName": PLATFORMS[platform]["OSName"],
        "OSVersion": "13.6.0",
        "ProfileVersion": 2,
        "RamLimitGB": 42,
        "TokenData": {
            "OneTimeTokens": {},
            "TokensToCheck": {},
            "TokensToRemove": [],
            "TokensToSet": {}
        },
        "__type": "OnLoginRequestBody"
    }
    data = json.dumps(payload).encode('utf-8')
    headers["Content-Length"] = str(len(data))
    headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/on_login', 'PUT', data)

    async with aiohttp.ClientSession() as session:
        async with session.put(URLS["on_login"], headers=headers, data=data, ssl=False) as resp:
            if resp.status == 200:
                resp_json = await resp.json()
                translation = {
                    "Koins": "💰 Монеты", "Souls": "👻 Души", "PVP": "💎 Кровавые рубины", "Talent": "✨ Таланты",
                    "Runes": "📜 Руны", "Shards": "🪓 Осколки Шао Кана", "QuestReinforcements": "🧪 Зелья режима заданий",
                    "QuestRenown": "🏅 % славы (Режим Заданий)", "SpiritFragments": "🌌 Фрагменты духа Рептилии",
                    "FeatPackCredit": "🎴 Наборы с Рунами",
                    "FreeProductCredit": "🎁 Бесплатные очки", "KombatPassPoints": "🎟️ Очки боевого пропуска",
                    "KryptKeys": "🔑 Ключи Крипты", "KryptHearts": "❤️ Сердца Крипты",
                    "DragonKrystals": "🐉 Кристаллы дракона"
                }
                global_translation = {
                    "IsKryptShareRewardClaimed": "📩 Кнопка Поделиться в Крипте получена",
                    "PayerUSD": "💵 Общая сумма доната",
                    "AESKey": "🔐 ID аккаунта"
                }

                def recursive_find_key(data, key):
                    if isinstance(data, dict):
                        if key in data:
                            return data[key]
                        for v in data.values():
                            result = recursive_find_key(v, key)
                            if result is not None:
                                return result
                    elif isinstance(data, list):
                        for item in data:
                            result = recursive_find_key(item, key)
                            if result is not None:
                                return result
                    return None

                def find_currency_objects(data):
                    results = []
                    if isinstance(data, dict):
                        if "count" in data and "server_data" in data and data["server_data"].get("ItemType") == "Currency":
                            results.append(data)
                        for value in data.values():
                            results.extend(find_currency_objects(value))
                    elif isinstance(data, list):
                        for item in data:
                            results.extend(find_currency_objects(item))
                    return results

                is_krypt = recursive_find_key(resp_json, "IsKryptShareRewardClaimed") or False
                payer_usd = recursive_find_key(resp_json, "PayerUSD") or 0
                aes_key = recursive_find_key(resp_json, "AESKey") or "Не найден"
                global_info = {
                    global_translation["IsKryptShareRewardClaimed"]: "✅ Да" if is_krypt else "❌ Нет",
                    global_translation["PayerUSD"]: round(payer_usd, 2),
                    global_translation["AESKey"]: aes_key
                }
                currency_objects = find_currency_objects(resp_json)
                currencies = [
                    f"{translation.get(obj['server_data'].get('CurrencyType', 'Unknown'), obj['server_data'].get('CurrencyType', 'Unknown'))}: {obj['count']}"
                    for obj in currency_objects if obj['server_data'].get("CurrencyType") != "RealWorld"
                ]
                result = "🌍 Глобальная информация:\n" + "\n".join(
                    f"{k}: {v}" for k, v in global_info.items()) + "\n\n💰 Валюты:\n" + "\n".join(currencies)
                return result
    return "❌ Не удалось получить статистику."

async def run_add_mileena_pack(uuid: str, platform: str):
    token = await get_access_token(uuid, platform)
    if not token:
        return "❌ Не удалось получить токен для активации пакета."

    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "Content-Type": "application/json",
        "Accept": "application/json",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    timestamp_ms = int(time.time() * 1000)
    payload = {
        "Products": ["DSO_S15MK1MileenaEarlyAccess"],
        "TokenData": {
            "OneTimeTokens": {},
            "TokensToCheck": {},
            "TokensToSet": {}
        },
        "__type": "ConditionalOfferTriggerRequestBody"
    }
    data = json.dumps(payload).encode('utf-8')
    headers["Content-Length"] = str(len(data))
    headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/conditional_offer_trigger', 'PUT', data)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(URLS["conditional_offer_trigger"], headers=headers, data=data, ssl=False) as response:
                if response.status == 200:
                    result = await response.json()
                    print("Запрос успешен:", result)
                    return f"✅ Набор РАННИЙ ДОСТУП активирован: {json.dumps(result, ensure_ascii=False)}"
                elif response.status == 409:
                    return "❌ Ошибка 409 Conflict – предложение уже активировано или условия не соблюдены."
                elif response.status == 400:
                    return "❌ Ошибка 400 Bad Request – проверьте корректность данных."
                else:
                    text = await response.text()
                    return f"⚠️ Ошибка {response.status}: {text}"
    except aiohttp.ClientError as e:
        return f"❌ Ошибка сети: {str(e)}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

async def run_add_skarlet_pack(uuid: str, platform: str):
    token = await get_access_token(uuid, platform)
    if not token:
        return "❌ Не удалось получить токен для активации пакета."

    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "Content-Type": "application/json",
        "Accept": "application/json",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
    })
    timestamp_ms = int(time.time() * 1000)
    payload = {
        "Products": ["DSO_KlassicSkarletEarlyAccess"],
        "TokenData": {
            "OneTimeTokens": {},
            "TokensToCheck": {},
            "TokensToSet": {}
        },
        "__type": "ConditionalOfferTriggerRequestBody"
    }
    data = json.dumps(payload).encode('utf-8')
    headers["Content-Length"] = str(len(data))
    headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/conditional_offer_trigger', 'PUT', data)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(URLS["conditional_offer_trigger"], headers=headers, data=data, ssl=False) as response:
                if response.status == 200:
                    result = await response.json()
                    print("Запрос успешен:", result)
                    return f"✅ Набор КЛАССИЧЕСКАЯ СКАРЛЕТ активирован: {json.dumps(result, ensure_ascii=False)}"
                elif response.status == 409:
                    return "❌ Ошибка 409 Conflict – предложение уже активировано или условия не соблюдены."
                elif response.status == 400:
                    return "❌ Ошибка 400 Bad Request – проверьте корректность данных."
                else:
                    text = await response.text()
                    return f"⚠️ Ошибка {response.status}: {text}"
    except aiohttp.ClientError as e:
        return f"❌ Ошибка сети: {str(e)}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

# Добавленные функции для открытия наборов и принятия наград
async def send_open_pack_request(access_token, inventory_ids, platform):
    url = URLS["open_pack"]
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": access_token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "accept-language": "ru",
        "app-version": "6.2.0",
        "client-os-version": "Android 9",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
        "commerce-backend": "google-service",
        "device-id": "10838243925acb665a11f9177864bbc2",
        "device-model": "SM-X910N",
        "local-utc-offset": "2",
        "passcode": "Zb59bqRmvLqS",
        "x-hydra-client-id": "0681b2e7-d3db-4b0a-8fc9-ec973208dcf2",
        "x-hydra-compress-response": "false",
        "x-hydra-user-agent": "Hydra-Cpp/1.182.1",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    payload = {
        "InventoryIds": inventory_ids,
        "TokenData": {
            "OneTimeTokens": {},
            "TokensToCheck": {},
            "TokensToSet": {}
        },
        "__type": "InventoryOpenPackRequestBody"
    }
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/open_pack', 'PUT', data)

    print(f"Отправляем запрос open_pack с {len(inventory_ids)} ID:")
    for inv_id in inventory_ids[:5]:
        print(f" - {inv_id}")
    if len(inventory_ids) > 5:
        print(f" ...и ещё {len(inventory_ids) - 5} ID")
    print("Тело запроса:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=data, ssl=False) as response:
            if response.status == 200:
                print(f"Пакеты успешно открыты (количество: {len(inventory_ids)})!")
                return True
            else:
                print(f"Ошибка при открытии пакетов: {response.status}")
                return False

async def send_resolve_pending_rewards(access_token, item_ids, platform):
    url = URLS["resolve_pending_rewards"]
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": access_token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "accept-language": "ru",
        "app-version": "6.2.0",
        "client-os-version": "Android 9",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
        "commerce-backend": "google-service",
        "device-id": "10838243925acb665a11f9177864bbc2",
        "device-model": "SM-X910N",
        "local-utc-offset": "2",
        "passcode": "Zb59bqRmvLqS",
        "x-hydra-client-id": "0681b2e7-d3db-4b0a-8fc9-ec973208dcf2",
        "x-hydra-compress-response": "false",
        "x-hydra-user-agent": "Hydra-Cpp/1.182.1",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    payload = {
        "ItemIds": item_ids,
        "TokenData": {
            "OneTimeTokens": {},
            "TokensToCheck": {},
            "TokensToSet": {}
        },
        "__type": "InventoryResolvePendingRewardRequestBody"
    }
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/resolve_pending_rewards', 'PUT', data)

    print(f"Отправляем запрос resolve_pending_rewards с {len(item_ids)} ID:")
    for item_id in item_ids[:5]:
        print(f" - {item_id}")
    if len(item_ids) > 5:
        print(f" ...и ещё {len(item_ids) - 5} ID")
    print("Тело запроса:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=data, ssl=False) as response:
            if response.status == 200:
                print(f"Pending rewards успешно обработаны (количество: {len(item_ids)})!")
                return True
            else:
                print(f"Ошибка при обработке pending rewards: {response.status}")
                return False

async def send_on_login_request(access_token, account_id, platform):
    url = URLS["on_login"]
    timestamp_ms = int(time.time() * 1000)
    payload = {
        "CountryCode": "RU",
        "DeviceModel": "IPHONESE",
        "LocalTime": f"/Date({timestamp_ms})/",
        "OSName": PLATFORMS[platform]["OSName"],
        "OSVersion": "13.6.0",
        "ProfileVersion": 2,
        "RamLimitGB": 42,
        "AccountUUID": account_id,
        "AccessToken": access_token,
        "TokenData": {
            "OneTimeTokens": {},
            "TokensToCheck": {},
            "TokensToRemove": [],
            "TokensToSet": {}
        },
        "__type": "OnLoginRequestBody"
    }
    data = json.dumps(payload).encode('utf-8')
    headers = HEADERS_TEMPLATE.copy()
    headers.update({
        "x-hydra-access-token": access_token,
        "x-hydra-api-key": PLATFORMS[platform]["api_key"],
        "accept-language": "ru",
        "app-version": "6.2.0",
        "client-os-version": "iOS",
        "client-platform-type": PLATFORMS[platform]["client-platform-type"],
        "commerce-backend": "google-service",
        "device-id": "10838243925acb665a11f9177864bbc2",
        "device-model": "SM-X910N",
        "local-utc-offset": "2",
        "passcode": "Zb59bqRmvLqS",
        "x-hydra-client-id": "371e50b2-3e88-4a26-a627-d8bc01cc14d9",
        "x-hydra-compress-response": "false",
        "x-hydra-user-agent": "Hydra-Cpp/1.182.1",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Length": str(len(data))
    })
    headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/on_login', 'PUT', data)

    print("Отправляем on_login запрос...")
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=data, ssl=False) as response:
            if response.status == 200:
                resp_json = await response.json()
                resp_json["UUID Аккаунта"] = account_id
                resp_json["Access Token"] = access_token
                return resp_json
            else:
                print(f"Ошибка при on_login запросе: {response.status}")
                return None

async def parse_on_login_for_open_pack(response_json, access_token, account_id, platform):
    pack_ids = []

    def recursive_search(data):
        if isinstance(data, dict):
            if "id" in data and "server_data" in data:
                server_data = data["server_data"]
                if server_data.get("__type") == "PackItemServerData":
                    pack_ids.append(data["id"])
            for value in data.values():
                recursive_search(value)
        elif isinstance(data, list):
            for item in data:
                recursive_search(item)

    recursive_search(response_json)
    result = ""
    if pack_ids:
        print(f"Найдено {len(pack_ids)} ID пакетов для открытия:")
        for pack_id in pack_ids[:5]:
            print(f" - {pack_id}")
        if len(pack_ids) > 5:
            print(f" ...и ещё {len(pack_ids) - 5} ID")
        result += f"🎁 Найдено {len(pack_ids)} неоткрытых наборов\n"

        batch_size = 3000
        successful_opens = 0
        for i in range(0, len(pack_ids), batch_size):
            batch = pack_ids[i:i + batch_size]
            print(f"Обрабатываем батч {i // batch_size + 1}: {len(batch)} пакетов (с {i} по {i + len(batch) - 1})")
            if await send_open_pack_request(access_token, batch, platform):
                successful_opens += len(batch)
                result += f"✅ Открыто {len(batch)} наборов (батч {i // batch_size + 1})\n"
            else:
                result += f"❌ Ошибка при открытии батча {i // batch_size + 1} ({len(batch)} наборов)\n"
            if i + batch_size < len(pack_ids):
                print("⏳ Ожидание 5 секунд перед следующим батчем...")
                await asyncio.sleep(5)

        result += f"📊 Всего успешно открыто: {successful_opens} из {len(pack_ids)} наборов\n"
        print(f"Всего успешно открыто: {successful_opens} из {len(pack_ids)} наборов")

        print("Повторный вызов on_login после открытия пакетов...")
        new_response_json = await send_on_login_request(access_token, account_id, platform)
        if new_response_json:
            result += await parse_on_login_for_pending_rewards(new_response_json, access_token, platform)
        else:
            result += "❌ Ошибка при повторном вызове on_login\n"
    else:
        print("Я проанализировал аккаунт и не нашёл неоткрытых наборов")
        result += "ℹ️ Неоткрытых наборов не найдено\n"
        print("Переходим к проверке наград...")
        result += await parse_on_login_for_pending_rewards(response_json, access_token, platform)
    return result

async def parse_on_login_for_pending_rewards(response_json, access_token, platform):
    pending_ids = []

    def recursive_search(data):
        if isinstance(data, dict):
            if "id" in data and "server_data" in data:
                server_data = data["server_data"]
                if server_data.get("__type") == "PendingRewardItemServerData":
                    pending_ids.append(data["id"])
            for value in data.values():
                recursive_search(value)
        elif isinstance(data, list):
            for item in data:
                recursive_search(item)

    recursive_search(response_json)
    result = ""
    if pending_ids:
        print(f"Найдено {len(pending_ids)} наград для обработки:")
        for pending_id in pending_ids[:5]:
            print(f" - {pending_id}")
        if len(pending_ids) > 5:
            print(f" ...и ещё {len(pending_ids) - 5} наград")
        result += f"🏆 Найдено {len(pending_ids)} необработанных наград\n"

        batch_size = 5000
        for i in range(0, len(pending_ids), batch_size):
            batch = pending_ids[i:i + batch_size]
            if await send_resolve_pending_rewards(access_token, batch, platform):
                result += f"✅ Обработано {len(batch)} наград\n"
            else:
                result += f"❌ Ошибка при обработке батча наград\n"
    else:
        result += "ℹ️ Необработанных наград не найдено\n"
    return result


async def process_open_packs_and_rewards(uuid, platform):
    token = await get_access_token(uuid, platform)
    if not token:
        return "❌ Не удалось получить токен."
    response_json = await send_on_login_request(token, uuid, platform)
    if not response_json:
        return "❌ Не удалось выполнить on_login запрос."
    return await parse_on_login_for_open_pack(response_json, token, uuid, platform)


# Telegram handlers
async def start(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    if f"@{username}" not in ALLOWED_USERS:
        await update.message.reply_text("🚫 Я тебя не знаю, съебись")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("🍎 iOS", callback_data="ios")],
        [InlineKeyboardButton("🤖 Android", callback_data="android")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Привет, выбирай платформу:", reply_markup=reply_markup)
    return CHOOSING_PLATFORM


async def choose_platform(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data["platform"] = query.data
    keyboard = [
        [InlineKeyboardButton("🏁 Завершение забега Крипты", callback_data="end_krypt_run")],
        [InlineKeyboardButton("🎁 Получение награды за поделиться", callback_data="claim_share_reward")],
        [InlineKeyboardButton("🔑 Ключи в кристаллы", callback_data="keys_to_krystals")],
        [InlineKeyboardButton("🛒 Открытие наборов", callback_data="open_packs")],
        [InlineKeyboardButton("⚔️ Пропуск боя испытания", callback_data="end_challenge_fight")],
        [InlineKeyboardButton("📈 Статистика аккаунта", callback_data="account_stats")],
        [InlineKeyboardButton("🪦 Открытие эпической гробницы", callback_data="open_epic_tombstone")],
        [InlineKeyboardButton("📦 Открытие эпического сундука", callback_data="open_epic_chest")],
        [InlineKeyboardButton("🎴 Добавление набора Милины MK1", callback_data="add_mileena_pack")],
        [InlineKeyboardButton("🎴 Добавление набора Классик Скарлет", callback_data="add_skarlet_pack")],  # Новая кнопка
        [InlineKeyboardButton("🎁 Открытие и принятие наград", callback_data="open_and_resolve_rewards")],
        [InlineKeyboardButton("📋 Список персонажей", callback_data="character_list")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("✅ Платформа выбрана! Выберите действие:", reply_markup=reply_markup)
    return CHOOSING_ACTION


async def choose_action(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data["action"] = query.data
    if query.data == "character_list":  # Обработка новой кнопки
        character_list_url = "https://docs.google.com/spreadsheets/d/1xzPo6VOZv_zBLED9L16rxEHPtgibmi2A_PM__25ES6c/edit?gid=302097284#gid=302097284"
        await query.edit_message_text(f"📋 Список персонажей (версия 6.1) находится здесь:\n{character_list_url}\n\nБот работает строго по таблице (от 2 до 178)")
        return ConversationHandler.END  # Завершаем диалог после отправки ссылки
    elif query.data in ["keys_to_krystals", "open_epic_tombstone", "open_epic_chest", "open_packs"]:
        await query.edit_message_text("🔢 Введите количество циклов:")
        return INPUT_CYCLES
    elif query.data in ["packs", "end_challenge_fight"]:
        await query.edit_message_text("📝 Введите HEX тело запроса:")
        return INPUT_HEX_BODY
    else:
        await query.edit_message_text(
            "🔑 Введите email и пароль WB ID через пробел (например: email@example.com пароль):")
        return INPUT_CREDENTIALS


async def input_cycles(update: Update, context: CallbackContext):
    try:
        context.user_data["cycles"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Введите корректное число циклов! 🔢")
        return ConversationHandler.END
    action = context.user_data["action"]
    if action == "open_epic_tombstone":
        await update.message.reply_text("👥 Введите 3 номера персонажей через пробел (от 1 до 177, например: 1 13 38):")
        return INPUT_CHAR_NUMBERS
    elif action == "open_packs":
        keyboard = [
            [InlineKeyboardButton("РАННИЙ ДОСТУП (МИЛИНА ИЗ МК1)", callback_data="РАННИЙ ДОСТУП (МИЛИНА ИЗ МК1)")],
            [InlineKeyboardButton("СЕРЕБРЯНЫЙ НАБОР", callback_data="СЕРЕБРЯНЫЙ НАБОР")],
            [InlineKeyboardButton("НАБОР НОВИЧКА (500 ДУШ + ЗОЛОТО)", callback_data="НАБОР НОВИЧКА (500 ДУШ + ЗОЛОТО)")],
            [InlineKeyboardButton("ЯЩИК С БАРАХЛОМ ИЗ КРИПТЫ", callback_data="ЯЩИК С БАРАХЛОМ ИЗ КРИПТЫ")],
            [InlineKeyboardButton("АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 1", callback_data="АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 1")],
            [InlineKeyboardButton("АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 2", callback_data="АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 2")],
            [InlineKeyboardButton("АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 3", callback_data="АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 3")],
            [InlineKeyboardButton("АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 4", callback_data="АЛМАЗНЫЙ НАБОР НОВЫЙ БОЕЦ 4")],
            [InlineKeyboardButton("НАБОР ИСПЫТАНИЯ", callback_data="НАБОР ИСПЫТАНИЯ")],
            [InlineKeyboardButton("НАБОР СНАРЯЖЕНИЯ", callback_data="НАБОР СНАРЯЖЕНИЯ")],
            [InlineKeyboardButton("ПРИЗЫВ КАМЕО", callback_data="ПРИЗЫВ КАМЕО")],
            [InlineKeyboardButton("ПРИЗЫВ СНАРЯЖЕНИЯ КРИПТЫ", callback_data="ПРИЗЫВ СНАРЯЖЕНИЯ КРИПТЫ")],
            [InlineKeyboardButton("ЗОЛОТОЙ НАБОР (150 ДУШ)", callback_data="ЗОЛОТОЙ НАБОР (150 ДУШ)")],
            [InlineKeyboardButton("АЛМАЗНЫЙ ЛАРЕЦ", callback_data="АЛМАЗНЫЙ ЛАРЕЦ")],
            [InlineKeyboardButton("ЗОЛОТОЙ ЛАРЕЦ", callback_data="ЗОЛОТОЙ ЛАРЕЦ")],
            [InlineKeyboardButton("ЭПИЧЕСКИЙ ЛАРЕЦ", callback_data="ЭПИЧЕСКИЙ ЛАРЕЦ")],
            [InlineKeyboardButton("РЕДКИЙ ЛАРЕЦ", callback_data="РЕДКИЙ ЛАРЕЦ")],
            [InlineKeyboardButton("Купить монеты (1 500 000)", callback_data="Купить монеты (1 500 000)")],
            [InlineKeyboardButton("РАННИЙ ДОСТУП (КЛАССИК СКАРЛЕТ)", callback_data="РАННИЙ ДОСТУП (КЛАССИК СКАРЛЕТ)")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🎁 Выберите набор для покупки:", reply_markup=reply_markup)
        return CHOOSING_PACK
    await update.message.reply_text("🔑 Введите email и пароль WB ID через пробел (например: email@example.com пароль):")
    return INPUT_CREDENTIALS


async def choose_pack(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data["pack_name"] = query.data
    await query.edit_message_text("🔢 Введите количество purchase запросов для каждого цикла:")
    return INPUT_PURCHASE_REQUESTS


async def input_purchase_requests(update: Update, context: CallbackContext):
    try:
        context.user_data["num_purchase_requests"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Введите корректное число purchase запросов! 🔢")
        return ConversationHandler.END
    await update.message.reply_text("🔑 Введите email и пароль WB ID через пробел (например: email@example.com пароль):")
    return INPUT_CREDENTIALS


async def input_char_numbers(update: Update, context: CallbackContext):
    try:
        char_numbers = [int(num) for num in update.message.text.split()]
        if len(char_numbers) != 3:  # Исправлено: numbers -> char_numbers
            await update.message.reply_text("❌ Ошибка: Введите ровно 3 номера персонажей через пробел! 👥")
            return ConversationHandler.END
        if any(num < 2 or num > 178 for num in char_numbers):  # Исправлено: numbers -> char_numbers
            await update.message.reply_text("❌ Ошибка: Номера должны быть от 2 до 178! 🔢")
            return ConversationHandler.END
        if len(set(char_numbers)) != 3:  # Исправлено: numbers -> char_numbers
            await update.message.reply_text("❌ Ошибка: Номера персонажей не должны повторяться! 🚫")
            return ConversationHandler.END
        context.user_data["char_numbers"] = char_numbers  # Исправлено: numbers -> char_numbers
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Введите корректные числа через пробел (например: 1 13 38)! 🔢")
        return ConversationHandler.END
    await update.message.reply_text("🔑 Введите email и пароль WB ID через пробел (например: email@example.com пароль):")
    return INPUT_CREDENTIALS

async def input_hex_body(update: Update, context: CallbackContext):
    hex_body_input = update.message.text.replace(" ", "").replace("\n", "")
    try:
        context.user_data["body"] = bytes.fromhex(hex_body_input)
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Некорректное значение HEX тела! 📝")
        return ConversationHandler.END
    await update.message.reply_text("🔑 Введите email и пароль WB ID через пробел (например: email@example.com пароль):")
    return INPUT_CREDENTIALS


async def input_credentials(update: Update, context: CallbackContext):
    action = context.user_data.get("action")
    platform = context.user_data.get("platform")
    if not action or not platform:
        await update.message.reply_text("❌ Ошибка: Действие или платформа не выбраны. Начните заново с /start! 🔄")
        return ConversationHandler.END

    pattern = r'^(\S+)\s+(?:"([^"]*)"|(.*))$'
    match = re.match(pattern, update.message.text)
    if not match:
        await update.message.reply_text("❌ Ошибка: Введите email и пароль через пробел! 📝")
        return ConversationHandler.END

    email = match.group(1)
    password = match.group(2) if match.group(2) is not None else match.group(3)

    uuid = get_account_id(email, password)
    if not uuid:
        await update.message.reply_text("❌ Ошибка: Неверные email или пароль! 🔑")
        return ConversationHandler.END

    await update.message.reply_text("🚀 Запускаю скрипт...")

    try:
        if action == "claim_share_reward":
            token = await get_access_token(uuid, platform)
            if not token:
                result = "❌ Не удалось получить токен."
            else:
                hex_body = "60023009546F6B656E446174616003300D4F6E6554696D65546F6B656E736000300D546F6B656E73546F436865636B6000300B546F6B656E73546F536574600030065F5F74797065301B436C61696D536861726552657761726452657175657374426F6479"
                body = bytes.fromhex(hex_body)

                headers = {
                    "User-Agent": "MKMobile/++nrs_mobile_stream+MKM_Release_Candidate-CL-1388016 Android/9",
                    "Connection": "keep-alive",
                    "Accept": "application/x-ag-binary",
                    "Accept-Encoding": "gzip, deflate, br",
                    "accept-language": "ru",
                    "app-version": "6.2.0",
                    "client-os-version": PLATFORMS[platform]["OSName"] + " 9",
                    "client-platform-type": PLATFORMS[platform]["client-platform-type"],
                    "commerce-backend": "google-service",
                    "device-id": "69a1a9dd902b3bb6c5ad74bf896d605a",
                    "device-model": "1",
                    "local-utc-offset": "2",
                    "passcode": "Zb59bqRmvLqS",
                    "x-hydra-access-token": token,
                    "x-hydra-api-key": PLATFORMS[platform]["api_key"],
                    "x-hydra-client-id": "ab061a51-7521-4cb1-9df8-d329fc2628b3",
                    "x-hydra-user-agent": "Hydra-Cpp/1.182.1",
                    "x-hydra-compress-response": "true",
                    "Content-Type": "application/x-ag-binary",
                    "Content-Length": str(len(body)),
                }
                headers["x-hydra-signature"] = generate_hydra_signature('/ssc/invoke/claim_share_reward', 'PUT', body)

                num_requests = 2000
                max_concurrent_tasks = 750
                status_counters = {"200": 0, "400": 0, "429": 0, "other": 0}
                semaphore = asyncio.Semaphore(max_concurrent_tasks)

                async def send_single_request(session, req_id):
                    async with semaphore:
                        try:
                            async with session.put(URLS["claim_share_reward"], headers=headers, data=body, ssl=False) as resp:
                                status = resp.status
                                if status == 200:
                                    status_counters["200"] += 1
                                elif status == 400:
                                    status_counters["400"] += 1
                                elif status == 429:
                                    status_counters["429"] += 1
                                    await asyncio.sleep(5)
                                else:
                                    status_counters["other"] += 1
                        except Exception as e:
                            status_counters["other"] += 1
                            print(f"Запрос #{req_id} - Исключение: {e}")

                connector = aiohttp.TCPConnector(limit=0, ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    tasks = [send_single_request(session, req_id) for req_id in range(1, num_requests + 1)]
                    await asyncio.gather(*tasks, return_exceptions=True)

                multiplied_success = status_counters["200"] * 5
                result = (
                    f"📊 Результат выполнения {num_requests} запросов claim_share_reward:\n"
                    f"✅ Успешных (200): {status_counters['200']}\n"
                    f"❌ Ошибок 400 (Bad Request): {status_counters['400']}\n"
                    f"⏳ Ошибок 429 (Too Many Requests): {status_counters['429']}\n"
                    f"⚠️ Прочих ошибок: {status_counters['other']}\n"
                    f"⭐ Итоговое количество (успешные × 5): {multiplied_success}\n"
                    f"ℹ️ Если успешных запросов мало, проверьте тело запроса или подпись."
                )

        elif action == "end_krypt_run":
            result = await run_end_krypt_run(uuid, platform)

        elif action == "keys_to_krystals":
            cycles = context.user_data.get("cycles")
            if not cycles:
                result = "❌ Ошибка: Количество циклов не указано! 🔢"
            else:
                result = await run_keys_to_krystals(uuid, platform, cycles)

        elif action == "open_epic_tombstone":
            cycles = context.user_data.get("cycles")
            char_numbers = context.user_data.get("char_numbers")
            if not cycles:
                result = "❌ Ошибка: Количество циклов не указано! 🔢"
            elif not char_numbers:
                result = "❌ Ошибка: Номера персонажей не указаны! 👥"
            else:
                result = await run_open_tombstone(uuid, platform, cycles, char_numbers)

        elif action == "open_epic_chest":
            cycles = context.user_data.get("cycles")
            if not cycles:
                result = "❌ Ошибка: Количество циклов не указано! 🔢"
            else:
                result = await run_open_chest(uuid, platform, cycles)

        elif action == "open_packs":
            cycles = context.user_data.get("cycles")
            pack_name = context.user_data.get("pack_name")
            num_purchase_requests = context.user_data.get("num_purchase_requests")
            if not cycles:
                result = "❌ Ошибка: Количество циклов не указано! 🔢"
            elif not pack_name:
                result = "❌ Ошибка: Набор не выбран! 🎁"
            elif not num_purchase_requests:
                result = "❌ Ошибка: Количество purchase запросов не указано! 🔢"
            else:
                result = await purchase_pack(uuid, platform, pack_name, cycles, num_purchase_requests)

        elif action == "end_challenge_fight":
            body = context.user_data.get("body")
            if not body:
                result = "❌ Ошибка: HEX тело запроса не указано! 📝"
            else:
                token = await get_access_token(uuid, platform)
                if not token:
                    result = "❌ Не удалось получить токен."
                else:
                    result = await run_custom_script(action, token, platform, body)

        elif action == "account_stats":
            result = await get_account_stats(uuid, platform)

        elif action == "add_mileena_pack":
            result = await run_add_mileena_pack(uuid, platform)

        elif action == "add_skarlet_pack":
            result = await run_add_skarlet_pack(uuid, platform)

        elif action == "open_and_resolve_rewards":
            result = await process_open_packs_and_rewards(uuid, platform)

        else:
            result = "❌ Ошибка: Неизвестное действие. Выберите действие заново с /start!"

    except Exception as e:
        result = f"❌ Произошла ошибка при выполнении скрипта: {str(e)}"

    await update.message.reply_text(f"🎉 Результат:\n{result}")
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("⛔ Действие отменено.")
    return ConversationHandler.END

TOKEN = "токен тг бота сюда"

def main():
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_PLATFORM: [CallbackQueryHandler(choose_platform)],
            CHOOSING_ACTION: [CallbackQueryHandler(choose_action)],
            INPUT_CREDENTIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_credentials)],
            INPUT_HEX_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_hex_body)],
            INPUT_CYCLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_cycles)],
            INPUT_CHAR_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_char_numbers)],
            CHOOSING_PACK: [CallbackQueryHandler(choose_pack)],
            INPUT_PURCHASE_REQUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_purchase_requests)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()