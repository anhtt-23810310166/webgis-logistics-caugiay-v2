# Hệ Thống WebGIS Quản Lý & Điều Phối Giao Nhận Hàng Hóa (Quận Cầu Giấy)

Ứng dụng WebGIS hỗ trợ giám sát, phân tuyến topology và điều phối đơn hàng logistics theo không gian thực tế tại địa bàn quận Cầu Giấy, Thành phố Hà Nội.

---

## 📌 Tính năng chính

Hệ thống được thiết kế theo 4 phân hệ trực quan:

1. **Bản đồ giám sát đa lớp đối tượng (Layer Control):**
   - Lớp phân khu giao hàng (Polygon): Dịch Vọng - Yên Hòa, Cầu Giấy - Quan Hoa, Nghĩa Tân - Mai Dịch.
   - Lớp bưu cục trung chuyển (Point Hubs): thông tin vị trí, địa chỉ và công suất tiếp nhận.
   - Lớp nhân viên giao hàng (Point Shippers): trạng thái hoạt động (Rảnh / Đang giao) và phương tiện.
   - Lớp đơn hàng (Point Orders): trạng thái xử lý đơn.

2. **Tạo đơn hàng & Phân tuyến tự động theo Topology:**
   - Chọn vị trí giao hàng trực tiếp trên bản đồ hoặc nhập tọa độ.
   - Tự động kiểm tra quan hệ không gian (`contains` / `within`) để xác định đơn thuộc phân khu và gán về bưu cục quản lý tương ứng.

3. **Điều phối Shipper tối ưu theo bán kính:**
   - Lọc các shipper rảnh trong vùng lân cận.
   - Tính toán khoảng cách trắc địa bằng phép chiếu UTM 48N (EPSG:32648) để tìm shipper gần nhất.
   - Vẽ lộ trình giao hàng trực quan từ vị trí shipper đến điểm nhận.

4. **Bản đồ nhiệt (Heatmap) & Thống kê không gian:**
   - Trực quan hóa mật độ đơn hàng tập trung bằng Folium HeatMap plugin.
   - Thống kê tỷ lệ và số lượng đơn hàng theo từng phân khu hành chính.

---

## 🛠️ Công nghệ & Hệ quy chiếu

- **Framework giao diện:** [Streamlit](https://streamlit.io/)
- **Bản đồ tương tác:** [Folium](https://python-visualization.github.io/folium/) & [streamlit-folium](https://github.com/randyzwitch/streamlit-folium)
- **Xử lý hình học không gian:** [Shapely](https://shapely.readthedocs.io/)
- **Chuyển đổi hệ tọa độ:** [PyProj](https://pyproj4.github.io/pyproj/)
- **Định dạng dữ liệu:** GeoJSON (Chuẩn vector OGC)
- **Hệ tọa độ:**
  - Lưu trữ & hiển thị web: `WGS-84` (EPSG:4326)
  - Đo đạc & tính khoảng cách chính xác: `WGS-84 / UTM zone 48N` (EPSG:32648)

---

## 📁 Cấu trúc thư mục

```text
webgis-logistics-caugiay-v2/
├── .github/
│   └── workflows/
│       └── ci.yml             # Tự động hóa kiểm thử CI trên GitHub
├── .streamlit/
│   └── config.toml            # Cấu hình tối ưu server Streamlit
├── data/                      # Tệp dữ liệu không gian GeoJSON
│   ├── hubs.geojson           # Điểm bưu cục trung chuyển
│   ├── orders.geojson         # Điểm đơn hàng
│   ├── shippers.geojson       # Điểm vị trí tài xế
│   └── zones.geojson          # Đa giác phân khu giao hàng
├── .gitattributes             # Chuẩn hóa định dạng file git
├── .gitignore                 # Bỏ qua tệp tạm, cache, venv
├── app.py                     # Giao diện chính Streamlit & điều khiển bản đồ
├── gis_engine.py              # Xử lý các phép toán và thuật toán không gian
├── seed_data.py               # Sinh dữ liệu mẫu giả lập ban đầu
├── requirements.txt           # Danh sách thư viện phụ thuộc
└── README.md                  # Tài liệu hướng dẫn dự án
```

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Yêu cầu môi trường
- Python >= 3.9

### 2. Cài đặt các gói phụ thuộc
```bash
# Khuyến nghị tạo môi trường ảo (tùy chọn)
python -m venv venv
# Kích hoạt trên Windows:
.\venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Khởi chạy ứng dụng WebGIS
```bash
streamlit run app.py
```

Truy cập giao diện WebGIS tại: `http://localhost:8501`
