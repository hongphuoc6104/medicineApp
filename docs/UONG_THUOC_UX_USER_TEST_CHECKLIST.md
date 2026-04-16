# Uong Thuoc UX User Test Checklist

Last updated: 2026-04-14

## 1. Muc tieu

Checklist nay de anh cam app tren dien thoai va tra loi nhanh ve trai nghiem nguoi dung.

Tap trung vao 4 nhom:

- De hieu: vao app co biet lam gi tiep theo khong.
- De dung: bam nut, quay lai, chuyen man hinh co muot va hop ly khong.
- De doc: text co ro, bi cat, bi tran, kho nhin khong.
- De tin: thong diep thanh cong/that bai co ro va dung ky vong khong.

## 2. Dieu kien test

- App ban nay dang noi vao backend local cua may tinh qua `adb reverse`.
- Khi test, giu:
  - Dien thoai Android cam USB vao may.
  - May tinh van dang mo backend local.
- Neu rut cap USB thi app ban nay co the khong goi duoc API.

## 3. Tai khoan test

### 3.1 Tai khoan rong (de xem onboarding)

- Email: `qa_empty_20260414_005341@example.com`
- Password: `Test1234!`

### 3.2 Tai khoan co du lieu (de xem man co lich/ke hoach)

- Email: `qa_full_20260414_005341@example.com`
- Password: `Test1234!`

## 4. Cach tra loi cho tung muc

Moi muc chi can tra loi theo mau:

`[MA-TEST] Pass/Can sua - cam nhan ngan - neu loi thi noi ro man hinh + nut + dieu gi gay kho chiu`

Vi du:

- `[UX-02] Pass - login ro rang, bam 1 lan la vao`
- `[UX-05] Can sua - man Lich su hoi roi, o nho, kho doc tren dien thoai`

## 5. Checklist uu tien cao

### UX-01. Mo app lan dau

Buoc test:

1. Mo app.
2. Dung 3-5 giay dau tien nhin man hinh.

Can de y:

- App vao co nhanh khong.
- Co thay bi dung, giat, loading kho hieu khong.
- Man hinh dau co cho biet day la app gi khong.

### UX-02. Login bang tai khoan rong

Buoc test:

1. Dang nhap bang tai khoan rong.
2. Xem man Trang chu dau tien.

Can de y:

- O login, text field va nut co de hieu khong.
- Bam dang nhap co ro la dang xu ly khong.
- Sau login co vao dung man onboarding khong.

### UX-03. Trang chu rong

Buoc test:

1. O Trang chu cua tai khoan rong.
2. Nhin cac CTA chinh.

Can de y:

- Co biet nen bam Quet, Nhap thu cong, hay Dung lai khong.
- Thong diep onboarding co tu nhien, de hieu khong.
- Nhin tong the co gon, sach, de bat dau khong.

### UX-04. Khu vuc Kế hoạch va Lịch sử khi chua co du lieu

Buoc test:

1. Vao tab `Ke hoach`.
2. Vao tab `Lich su`.

Can de y:

- Empty state co ro rang khong.
- Co biet tiep theo nen lam gi khong.
- Chuyen tab co muot va khong gay roi khong.

### UX-05. Login bang tai khoan co du lieu

Buoc test:

1. Dang xuat.
2. Dang nhap bang tai khoan co du lieu.
3. Vao Trang chu.

Can de y:

- Trang chu co de quet nhanh thong tin quan trong khong.
- Muc due/upcoming/missed co nhin ra khac nhau khong.
- Mau sac va the hien trang thai co de hieu khong.

### UX-06. Ke hoach va chi tiet ke hoach

Buoc test:

1. Vao tab `Ke hoach`.
2. Mo 1 ke hoach bat ky.
3. Tu man chi tiet, thu vao sua.

Can de y:

- Danh sach ke hoach co de scan mat khong.
- Mo chi tiet co ro rang va khong bi ngop khong.
- Nut `Chinh sua thuoc va lich` co de thay va de hieu khong.

### UX-07. Tao ke hoach moi

Buoc test:

1. Vao `Ke hoach`.
2. Bam nut `Tao ke hoach`.
3. Xem 3 lua chon: quet, nhap thu cong, dung lai.

Can de y:

- Co hieu ngay 3 lua chon khac nhau o diem nao khong.
- Man hinh nay co de ra quyet dinh khong.
- Chu, icon, mo ta co ro khong.

### UX-08. Dung lai ke hoach cu

Buoc test:

1. Tu `Tao ke hoach`, vao `Dung lai`.
2. Xem danh sach ke hoach cu.

Can de y:

- Nhin vao co biet plan nao nen dung lai khong.
- Card item co qua chat, qua nho, kho doc khong.
- Nut quay lai co hop ly khong.

### UX-09. Lich su weekly grid

Buoc test:

1. Vao tab `Lich su` bang tai khoan co du lieu.
2. Xem luoi lich trong tuan.

Can de y:

- O grid co de doc tren dien thoai that khong.
- Mau/trang thai co ro khong.
- Neu nhin nhanh, anh co hieu ngay da uong/quen/bo qua khong.

### UX-10. Tra cuu thuoc

Buoc test:

1. Tu Trang chu rong, bam `Tra cuu thuoc`.
2. Tim `paracetamol`.
3. Mo ket qua.

Can de y:

- Search box co de dung khong.
- Ket qua co de doc va de chon khong.
- Man chi tiet co ro rang, bo cuc hop ly khong.

### UX-11. Cai dat

Buoc test:

1. Vao `Cai dat`.
2. Xem toggle nhac thuoc, dong bo, dang xuat.

Can de y:

- Cac tuy chon co de hieu khong.
- Thong diep sau khi bam co ro rang khong.
- Co thao tac nao gay lo lang vi khong biet app da lam gi chua khong.

### UX-12. Cam nhan tong the

Tra loi nhanh 4 y:

1. Man nao de dung nhat.
2. Man nao roi nhat.
3. Cho nao cham, giat, hoac khong tu nhien.
4. Neu chi duoc sua 3 diem UX truoc, anh muon sua gi.

## 6. Mau tra loi tong hop

Anh co the tra loi theo format nay trong chat:

```text
[UX-01] ...
[UX-02] ...
[UX-03] ...
[UX-04] ...
[UX-05] ...
[UX-06] ...
[UX-07] ...
[UX-08] ...
[UX-09] ...
[UX-10] ...
[UX-11] ...
[UX-12] ...
```
