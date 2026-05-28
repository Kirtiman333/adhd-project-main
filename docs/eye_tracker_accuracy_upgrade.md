# Eye tracker accuracy upgrade

Các thay đổi chính:

1. Không còn trộn tọa độ mống mắt trong camera với tọa độ gaze trên màn hình.
   - Đây là lỗi lớn vì `predict()` trả về tọa độ màn hình, còn iris center là tọa độ ảnh camera.
   - Trộn 2 hệ tọa độ này làm con trỏ lệch và nhảy.

2. Thêm lọc nhiễu 2 lớp:
   - Median filter 5 frame để giảm điểm sai lẻ.
   - Kalman + EMA để làm mượt nhưng vẫn phản hồi nhanh.

3. Cải thiện loại bỏ outlier:
   - Bỏ qua 1–2 frame nhảy quá xa.
   - Nếu gaze mới xuất hiện liên tiếp nhiều lần, chấp nhận vị trí mới để không bị kẹt.

4. Cải thiện fixation:
   - Dùng độ lệch chuẩn trong 8 frame thay vì chỉ 3 frame.
   - Ít báo nhầm “Fixating” hơn.

5. Cải thiện camera:
   - Ưu tiên 1280x720, 30 FPS.
   - Giảm buffer để hạn chế lag.
   - Copy frame khi đọc để tránh lỗi race condition giữa 2 thread.

Gợi ý để chính xác hơn khi dùng:

- Đặt camera ngang tầm mắt.
- Ngồi cách camera khoảng 50–70 cm.
- Mặt không bị ngược sáng.
- Sau khi đổi vị trí ngồi hoặc ánh sáng, hãy calibration lại.
- Nếu vẫn rung nhiều, giảm `ema_alpha` trong `eye_tracker.py` từ `0.18` xuống `0.12`.
- Nếu con trỏ phản hồi chậm, tăng `ema_alpha` từ `0.18` lên `0.25`.
