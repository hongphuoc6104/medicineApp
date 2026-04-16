# UONG THUOC - CAI DAT VA CHAY APP QUA WIFI (KHONG CAN CAP USB)

Tai lieu nay ghi lai quy trinh chuan de lan sau chi can lam dung tung buoc la cai duoc ban moi len dien thoai qua Wi-Fi.

## 1) Dieu kien can co

- Dien thoai Android 11+ (co `Wireless debugging`).
- Dien thoai va may tinh cung 1 mang Wi-Fi.
- Da bat Developer options tren dien thoai.
- Da cai `adb`, `flutter`, Android SDK tren may tinh.

## 2) Pair va connect ADB qua Wi-Fi

Tren dien thoai:
- Vao `Developer options` -> bat `Wireless debugging`.
- Chon `Pair device with pairing code`.
- Ghi lai:
  - `PHONE_IP`
  - `PAIR_PORT`
  - `PAIR_CODE`
  - `DEBUG_PORT` (hien trong man hinh Wireless debugging)

Tren may tinh:

```bash
adb pair <PHONE_IP>:<PAIR_PORT>
# nhap PAIR_CODE tren dien thoai

adb connect <PHONE_IP>:<DEBUG_PORT>
adb devices -l
```

Neu thanh cong, `adb devices -l` se thay thiet bi dang `device`.

## 3) Khoi dong backend nen cua project

Tu root project:

```bash
bash dev.sh
```

Script nay se:
- bat Postgres Docker
- migrate DB
- chay Node API (port 3001)
- chay Python AI (port 8000)

Log backend:
- Node: `/tmp/medicine-node.log`
- Python AI: `/tmp/python-ai.log`

## 4) Quan trong: doi API_BASE_URL cho che do Wi-Fi

`dev.sh` mac dinh set `mobile/.env` ve `127.0.0.1` (phu hop adb reverse).

Khi chay Wi-Fi khong day, can sua lai theo IP LAN cua may tinh:

```env
API_BASE_URL=http://<HOST_LAN_IP>:3001/api
```

Vi du (tren may hien tai):

```env
API_BASE_URL=http://192.168.1.64:3001/api
```

Cach tim `HOST_LAN_IP` nhanh:

```bash
ip route get 1.1.1.1
```

Tim gia tri sau `src` (vi du `src 192.168.1.64`).

## 5) Cai app ban moi len dien thoai qua Wi-Fi

```bash
cd mobile
flutter pub get
flutter run -d <PHONE_IP>:<DEBUG_PORT> --target lib/main.dart
```

Lenh tren se build, install va mo app tren dien thoai.

## 6) Kiem tra nhanh sau khi cai

1. Mo app tren dien thoai, vao tab `Tra cuu`.
2. Thu tim thuoc va mo chi tiet.
3. Thu tinh nang tuong tac:
   - theo danh sach thuoc
   - theo hoat chat
4. Neu bi day ve login do token het han -> dang nhap lai.

## 7) Cac loi thuong gap va cach xu ly

### Loi: `No supported devices found`
- Kiem tra lai:
  - `adb devices -l`
  - dien thoai con bat Wireless debugging
  - cung Wi-Fi
- Neu mat ket noi, connect lai:

```bash
adb connect <PHONE_IP>:<DEBUG_PORT>
```

### Loi: App khong goi duoc API
- Kiem tra `mobile/.env` co dung `HOST_LAN_IP` chua.
- Kiem tra backend:

```bash
curl http://127.0.0.1:3001/api/health
curl http://127.0.0.1:8000/api/health
```

### Loi: Chay `dev.sh` xong bi mat API LAN
- Binh thuong, vi `dev.sh` ghi de `mobile/.env`.
- Sau moi lan chay `dev.sh`, nho sua lai `mobile/.env` ve IP LAN.

### Loi: Pair code het han
- Tren dien thoai tao pairing code moi va pair lai:

```bash
adb pair <PHONE_IP>:<PAIR_PORT>
```

## 8) Quy trinh rut gon cho lan sau

Moi lan deploy ban moi qua Wi-Fi:

```bash
# 1) ket noi dien thoai
adb connect <PHONE_IP>:<DEBUG_PORT>

# 2) chay backend
bash dev.sh

# 3) sua lai mobile/.env thanh HOST_LAN_IP

# 4) cai va chay app
cd mobile
flutter run -d <PHONE_IP>:<DEBUG_PORT> --target lib/main.dart
```

---

Ghi chu thuc te (tham khao):
- Device: Redmi 9T (`M2010J19SG`)
- Vi du endpoint debug da dung: `192.168.1.36:38021` (co the thay doi moi lan bat Wireless debugging)
