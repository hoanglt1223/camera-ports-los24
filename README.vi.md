# Port camera cho LineageOS 24 (Android 17) — Xiaomi gauguin

MIUI Camera 4.5, bản port Leica và một số bản GCam chạy trên **LineageOS 24 (Android 17)**,
máy **Xiaomi Mi 10T Lite 5G / Redmi Note 9 Pro 5G (gauguin, SM7225 "lito")**.

File blob chỉ dùng cho gauguin, nhưng cách làm thì dùng lại được: blob vendor và thư viện app
dựng cho Android 11/12 hỏng trên Android 17 theo vài kiểu dễ đoán. Repo ghi lại cách tìm và
sửa từng lỗi để người làm ROM cho máy khác tham khảo.

English: [README.md](README.md)

## Trạng thái (kiểm tra ngày 2026-11-09)

| App | Phiên bản | Chụp | Quay | Ghi chú |
|---|---|---|---|---|
| MIUI Camera (`com.android.camera`) | 4.5.002030.1 (MIUI 14) | OK, đủ độ phân giải 4624x3472 | OK, 1080p có chống rung EIS | Cần các bản vá blob và vá framework bên dưới |
| Leica port (`com.kobbin.leica.wmrebuild`) | 8.0.0 (port 8.x), bản đã vá | OK, 3472x4624; góc rộng 2448x3264 | chưa thử | Chi tiết và màu tốt nhất |
| GCam MGC 9.8.102 | 9.8.102 | OK | – | Cân bằng, sạch |
| GCam LMC 8.4 R18F1 | 8.4.300 | OK | – | Mặc định mở chế độ Night Sight |
| GCam MGC 9.4.103 V41 BSG (`org.codeaurora.snapcam`) | 9.4.103 | OK | – | Chip ống 0.6 / 0.9 / 1.0 |
| GCam LMC 8.8 R2 | 8.8 | Chỉ preview | – | Chụp không lưu ảnh |
| GCam Urnyx 7.3 | 7.3 | – | – | Không dùng được: không có activity mở được trên Android 17 |
| Aperture | 17 | OK | OK | Nhiễu nhất: không xử lý đa khung |

Chất lượng ảnh (một cảnh thử trong nhà): Leica chi tiết và màu tốt nhất, GCam (MGC) cân bằng
và sạch, Aperture nhiễu hơn, MIUI Camera giờ ra đủ độ phân giải (trước bản vá
CaptureResultExtras chỉ lưu khung preview 720x960).

Ảnh mẫu: sẽ bổ sung sau.

### Lỗi đã biết

- MIUI Camera: `mediaserver` 32-bit crash trong `FrameDecoder` khi tạo thumbnail cho mp4. File
  video vẫn được lưu. Sau clip đầu, nút quay đôi khi không nhận cho tới khi mở lại app (có thể
  cùng nguyên nhân, chưa xác nhận).
- MIUI Camera: nhắc "lau ống kính" không bao giờ hiện (phần suy luận gây crash provider đã bị tắt).
- Leica port: một lần ANR khi đổi ống kính ngay sau khi chụp, chỉ gặp với ART bản debug của
  bản dựng eng (xem [docs/eng-build-gotchas.md](docs/eng-build-gotchas.md)).

## Cài đặt (gauguin, LineageOS 24)

Các file sau nằm ở GitHub Releases (không có trong git):

| File | Nội dung |
|---|---|
| `miuicamera-los24-gauguin-magisk.zip` | Module Magisk / KernelSU: blob đã vá, gralloc gốc, luật SELinux cho MIVI |
| `miuicamera-los24-gauguin-recovery.zip` | Cùng các file, ghi thẳng vào system/vendor từ LineageOS recovery |
| `miuicamera-los24-gauguin-recovery-restore.zip` | Trả lại file gốc đã sao lưu |
| `framework-legacy-ctors-los24-gauguin-magisk.zip` | Tùy chọn: `framework.jar` có constructor cũ. **Chỉ cho đúng bản dựng** `lineage_gauguin ... CP2A.260605.016` incremental `1794015279`, bản khác sẽ bị từ chối |
| `leica-gauguin-en.apk` | Leica port đã vá (532 MB) |

1. Cài MIUI Camera 4.5.002030.1. Repo không phát hành APK này: lấy
   `/system/priv-app/MiuiCamera/` từ ROM gốc **MIUI 14.0.4.0 (SJSEUXM) gauguin**, hoặc từ một
   trang mirror công khai của `com.android.camera` 4.5.002030.1 cho gauguin. ROM cũng phải có
   sẵn blob vendor camera của MIUI (MIVI `libmialgoengine.so`...) và các thư viện `*.xiaomi.so`.
2. Đưa constructor cũ vào framework: áp `patches/framework/*.patch` vào `frameworks/base` rồi
   dựng lại, hoặc (chỉ khi đúng bản dựng) flash module framework tùy chọn.
3. Flash **một trong hai**: module Magisk hoặc zip recovery.

Cả hai đều kiểm `ro.product.device == gauguin`, rồi băm SHA-256 từng file trên máy. Chỉ thay
khi hash đúng bản gốc (hoặc đã là bản vá). Hash lạ thì dừng, báo đường dẫn và hash, chưa ghi
file nào. `gralloc.lito.so` là file gốc nguyên vẹn nên luôn được thay (recovery sao lưu trước).

Zip recovery sao lưu file gốc vào `/data/media/0/camera-port-backup/` (nếu recovery không dùng
được `/data` thì lưu `<file>.camera-port.orig` cạnh file) và giữ SELinux context của file gốc.
Nếu system/vendor chỉ đọc trong recovery (ext4 `shared_blocks`), hãy dùng module Magisk.

Dựng lại zip: `python tools/build-zips.py`.

## Các bản vá

Chi tiết (tiếng Anh): [docs/binary-patches.md](docs/binary-patches.md). Tóm tắt:

- **Framework** (dùng chung mọi máy): thêm lại constructor 15 tham số của
  `StreamConfigurationMap` (MIUI gọi qua reflection, A17 đã bỏ) và các constructor cũ của
  `CaptureResultExtras` (thiếu thì MIUI chỉ lưu khung preview 720x960).
- **SELinux**: cho `priv_app` đọc/thực thi `vendor_file` để MIUI nạp được MIVI.
- **libcamera_dirty.so**: mạng NN phát hiện bẩn ống kính đọc tràn heap, làm chết camera
  provider. `DirtyCamera::Forward` trả về ngay.
- **libcamera_algoup_jni / mianode_jni.xiaomi.so**: object `IProducerListener` dựng theo ABI
  Android 12 bị đưa vào libgui A17, crash ở `String16::size`. Truyền listener null.
- **com.vidhance.node.eis.so**: cấp 0x100 byte cho `GraphicBuffer` trong khi bản A17 cần
  ~0xd30, tràn heap khi quay có EIS. Tăng lên 0x1000. Thêm vá đổi kênh màu NV12/NV21.
- **Leica port**: profile gauguin tự nhận, chip zoom 0.6/1/2, giao diện tiếng Anh, ẩn màn
  thử nghiệm chỉ chạy trên HTP. Xem [leica/README.md](leica/README.md). Repo riêng, nhiều máy hơn:
  [hoanglt1223/leica-port](https://github.com/hoanglt1223/leica-port).

## Phần nào dùng được cho máy khác

- Bản vá framework trong `patches/framework/`: dùng cho mọi ROM Android 14+ chạy app camera gốc
  MIUI/HyperOS dựng cho Android 10-13.
- Cách tìm lỗi ABI cũ: khi blob cũ crash sâu trong libgui/libui/libbinder với con trỏ hỏng mỗi
  lần một khác, nghi ngờ object C++ của framework đã đổi layout. (1) Lớp con của interface
  framework bị đưa vào framework mới: tìm chỗ truyền và truyền null nếu framework cho phép.
  (2) Blob tự cấp bộ nhớ với `sizeof` cũ rồi gọi constructor mới: dùng
  `tools/scan-framework-ctor-allocs.py` để liệt kê.
- Các bẫy của bản dựng eng: [docs/eng-build-gotchas.md](docs/eng-build-gotchas.md).

Riêng cho gauguin: mọi offset trong `patches/blobs/` và mọi file trong `blobs/`. Các script vá
kiểm tra đúng byte gốc nên sẽ từ chối chạy trên blob khác.

## Giấy phép

Script và tài liệu: MIT ([LICENSE](LICENSE)). File nhị phân trong `blobs/` và trong release
thuộc về Xiaomi, Qualcomm, Imint và các chủ sở hữu khác, chỉ cung cấp để tương thích; xem
[NOTICE](NOTICE).
