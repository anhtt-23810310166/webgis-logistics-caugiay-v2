import os
import json
import random
from datetime import datetime, timedelta
from shapely.geometry import Point, Polygon, mapping

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _save_geojson(features: list, filepath: str):
    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)


def generate_sample_data(force: bool = False):
    """
    Tự động sinh dữ liệu không gian chuẩn GeoJSON (WGS-84 EPSG:4326)
    cho khu vực quận Cầu Giấy, thành phố Hà Nội.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    files = ["zones.geojson", "hubs.geojson", "shippers.geojson", "orders.geojson"]
    if not force and all(os.path.exists(os.path.join(DATA_DIR, f)) for f in files):
        return

    # 1. 3 Phân khu giao hàng liền kề không chồng lấn (Topology Adjacent)
    zone_bac = Polygon([
        (105.7720, 21.0410),
        (105.8020, 21.0410),
        (105.8020, 21.0525),
        (105.7720, 21.0525),
        (105.7720, 21.0410),
    ])
    zone_trung = Polygon([
        (105.7720, 21.0260),
        (105.8020, 21.0260),
        (105.8020, 21.0410),
        (105.7720, 21.0410),
        (105.7720, 21.0260),
    ])
    zone_nam = Polygon([
        (105.7720, 21.0070),
        (105.8060, 21.0070),
        (105.8060, 21.0260),
        (105.7720, 21.0260),
        (105.7720, 21.0070),
    ])

    zones_raw = [
        {
            "zone_id": "ZONE_BAC",
            "zone_name": "Phân khu Bắc Cầu Giấy",
            "wards": "Nghĩa Tân, Nghĩa Đô, Cổ Nhuế 1 (giáp Hoàng Quốc Việt)",
            "color": "#2563EB",
            "geom": zone_bac,
        },
        {
            "zone_id": "ZONE_TRUNG",
            "zone_name": "Phân khu Trung tâm Cầu Giấy",
            "wards": "Dịch Vọng, Dịch Vọng Hậu, Quan Hoa",
            "color": "#16A34A",
            "geom": zone_trung,
        },
        {
            "zone_id": "ZONE_NAM",
            "zone_name": "Phân khu Nam Cầu Giấy",
            "wards": "Yên Hòa, Trung Hòa",
            "color": "#D97706",
            "geom": zone_nam,
        },
    ]
    zone_features = [
        {
            "type": "Feature",
            "properties": {k: v for k, v in z.items() if k != "geom"},
            "geometry": mapping(z["geom"]),
        }
        for z in zones_raw
    ]
    _save_geojson(zone_features, os.path.join(DATA_DIR, "zones.geojson"))

    # 2. 3 Bưu cục nằm bên trong 3 phân khu
    hubs_raw = [
        {
            "hub_id": "HUB_01",
            "hub_name": "Bưu cục Nghĩa Tân - Hoàng Quốc Việt",
            "address": "Số 106 Hoàng Quốc Việt, Nghĩa Tân, Cầu Giấy",
            "zone_id": "ZONE_BAC",
            "capacity": 500,
            "geom": Point(105.7895, 21.0465),
        },
        {
            "hub_id": "HUB_02",
            "hub_name": "Bưu cục Dịch Vọng - Xuân Thủy",
            "address": "Số 144 Xuân Thủy, Dịch Vọng Hậu, Cầu Giấy",
            "zone_id": "ZONE_TRUNG",
            "capacity": 650,
            "geom": Point(105.7835, 21.0365),
        },
        {
            "hub_id": "HUB_03",
            "hub_name": "Bưu cục Trung Hòa - Trần Duy Hưng",
            "address": "Số 88 Trần Duy Hưng, Trung Hòa, Cầu Giấy",
            "zone_id": "ZONE_NAM",
            "capacity": 600,
            "geom": Point(105.7985, 21.0125),
        },
    ]
    hub_features = [
        {
            "type": "Feature",
            "properties": {k: v for k, v in h.items() if k != "geom"},
            "geometry": mapping(h["geom"]),
        }
        for h in hubs_raw
    ]
    _save_geojson(hub_features, os.path.join(DATA_DIR, "hubs.geojson"))

    # 3. 15 Shipper phân bố khắp quận Cầu Giấy
    random.seed(42)
    shipper_names = [
        "Nguyễn Văn Hùng", "Trần Minh Quân", "Lê Hoàng Nam", "Phạm Đức Anh", "Vũ Quốc Bảo",
        "Đặng Văn Tùng", "Bùi Quang Huy", "Đỗ Mạnh Dũng", "Ngô Thành Đạt", "Hoàng Văn Long",
        "Dương Minh Tuấn", "Phan Tuấn Kiệt", "Lý Văn Sơn", "Trịnh Xuân Trường", "Đinh Công Minh",
    ]
    shipper_features = []
    for i, name in enumerate(shipper_names, start=1):
        lng = round(random.uniform(105.7745, 105.8015), 6)
        lat = round(random.uniform(21.0095, 21.0505), 6)
        status = "Rảnh" if i % 3 != 0 else "Đang giao"
        shipper_features.append({
            "type": "Feature",
            "properties": {
                "shipper_id": f"SHP_{i:03d}",
                "full_name": name,
                "vehicle_plate": f"29-B1 {random.randint(100, 999)}.{random.randint(10, 99)}",
                "status": status,
            },
            "geometry": mapping(Point(lng, lat)),
        })
    _save_geojson(shipper_features, os.path.join(DATA_DIR, "shippers.geojson"))

    # 4. 30 Đơn hàng mẫu tại các tuyến phố Cầu Giấy
    streets = [
        "Xuân Thủy", "Cầu Giấy", "Hoàng Quốc Việt", "Trần Quốc Hoàn", "Tô Hiệu",
        "Trần Cung", "Duy Tân", "Thành Thái", "Trung Kính", "Vũ Phạm Hàm",
        "Nguyễn Khang", "Trần Duy Hưng", "Hoàng Đạo Thúy", "Nguyễn Chánh", "Chùa Hà",
    ]
    customers = [
        "Nguyễn Thị Lan", "Trần Văn Bình", "Lê Thu Hà", "Phạm Minh Châu", "Vũ Hải Yến",
        "Đỗ Hoàng Long", "Bùi Thị Mai", "Hoàng Ngọc Ánh", "Ngô Văn Toàn", "Đặng Thu Trang",
    ]

    order_features = []
    base_time = datetime(2026, 11, 23, 8, 0, 0)
    for i in range(1, 31):
        lng = round(random.uniform(105.7740, 105.8010), 6)
        lat = round(random.uniform(21.0090, 21.0500), 6)
        pt = Point(lng, lat)

        matched_hub = "HUB_02"
        for z in zones_raw:
            if pt.within(z["geom"]) or pt.touches(z["geom"]):
                matched_hub = next(h["hub_id"] for h in hubs_raw if h["zone_id"] == z["zone_id"])
                break

        if i <= 10:
            status = "Chờ phân tuyến"
            assigned_shp = ""
        elif i <= 22:
            status = "Đã gán tài xế"
            assigned_shp = f"SHP_{(i % 5) * 3 + 3:03d}"
        else:
            status = "Hoàn tất"
            assigned_shp = f"SHP_{(i % 15) + 1:03d}"

        order_features.append({
            "type": "Feature",
            "properties": {
                "order_id": f"ORD_2026_{i:03d}",
                "customer_name": random.choice(customers),
                "address": f"Số {random.randint(10, 280)} {random.choice(streets)}, Cầu Giấy, Hà Nội",
                "cod_amount": float(random.choice([85000, 120000, 195000, 250000, 340000, 480000, 620000])),
                "status": status,
                "created_at": (base_time + timedelta(minutes=i * 12)).strftime("%Y-%m-%d %H:%M:%S"),
                "assigned_hub_id": matched_hub,
                "assigned_shipper_id": assigned_shp,
            },
            "geometry": mapping(pt),
        })
    _save_geojson(order_features, os.path.join(DATA_DIR, "orders.geojson"))


if __name__ == "__main__":
    generate_sample_data(force=True)
    print("Đã khởi tạo dữ liệu mẫu GeoJSON tại quận Cầu Giấy thành công!")
