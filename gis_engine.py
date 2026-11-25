import os
import json
import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point, LineString, shape, mapping
from shapely.ops import transform

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Hệ quy chiếu tọa độ địa lý quốc tế WGS-84 (kinh độ, vĩ độ)
CRS_WGS84 = "EPSG:4326"
# Hệ tọa độ phẳng chiếu UTM Zone 48N dành cho khu vực miền Bắc Việt Nam (đơn vị: mét)
CRS_UTM48N = "EPSG:32648"

# Bộ chuyển đổi hệ quy chiếu hai chiều WGS-84 <-> UTM 48N
_TO_UTM = Transformer.from_crs(CRS_WGS84, CRS_UTM48N, always_xy=True).transform
_TO_WGS84 = Transformer.from_crs(CRS_UTM48N, CRS_WGS84, always_xy=True).transform


def _read_geojson(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = []
    for feat in data.get("features", []):
        row = dict(feat.get("properties", {}))
        row["geometry"] = shape(feat["geometry"])
        records.append(row)
    return records


def _write_geojson(records: list, filename: str):
    path = os.path.join(DATA_DIR, filename)
    features = []
    for r in records:
        props = {k: v for k, v in r.items() if k != "geometry"}
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(r["geometry"]),
        })
    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)


def load_spatial_layers():
    """Đọc toàn bộ 4 lớp dữ liệu không gian GeoJSON lên bộ nhớ."""
    zones = _read_geojson("zones.geojson")
    hubs = _read_geojson("hubs.geojson")
    shippers = _read_geojson("shippers.geojson")
    orders = _read_geojson("orders.geojson")
    return zones, hubs, shippers, orders


def save_orders(orders: list):
    _write_geojson(orders, "orders.geojson")


def save_shippers(shippers: list):
    _write_geojson(shippers, "shippers.geojson")


def assign_hub_by_topology(lat: float, lng: float, zones: list, hubs: list) -> dict:
    """
    Kiểm tra quan hệ Topology Điểm - Vùng (Point-in-Polygon: 'is contained in' / 'on border').
    Đầu vào: Tọa độ (lat, lng) của đơn hàng mới trong hệ WGS-84 (EPSG:4326).
    Đầu ra: Thông tin phân khu và bưu cục phụ trách tương ứng.
    """
    # Lưu ý chuẩn GIS: Shapely khởi tạo điểm theo thứ tự (Kinh độ - X, Vĩ độ - Y)
    order_point = Point(lng, lat)

    for z in zones:
        # Phép toán Topology: Kiểm tra điểm nằm hoàn toàn bên trong đa giác hoặc nằm trên đường biên
        if order_point.within(z["geometry"]) or order_point.touches(z["geometry"]):
            matched_hub = next(h for h in hubs if h["zone_id"] == z["zone_id"])
            return {
                "in_service_area": True,
                "zone_id": z["zone_id"],
                "zone_name": z["zone_name"],
                "hub_id": matched_hub["hub_id"],
                "hub_name": matched_hub["hub_name"],
                "hub_address": matched_hub["address"],
            }

    return {
        "in_service_area": False,
        "message": "Tọa độ đơn hàng nằm ngoài ranh giới 3 phân khu phục vụ tại quận Cầu Giấy!",
    }


def find_nearest_shippers(order_point_wgs84: Point, shippers: list, radius_meters: float):
    """
    Ứng dụng chuyển đổi hệ tọa độ UTM Zone 48N (EPSG:32648) và quan hệ Topology Điểm - Điểm:
    1. Lọc các tài xế đang có trạng thái 'Rảnh'.
    2. Tạo vùng đệm không gian (Buffer) bán kính R mét quanh điểm giao hàng.
    3. Lọc các tài xế thỏa mãn quan hệ 'is within' vùng đệm và sắp xếp theo khoảng cách Euclid gần nhất.
    """
    available = [s for s in shippers if s["status"] == "Rảnh"]
    if not available:
        return [], None

    # Chuyển đổi từ tọa độ cầu WGS-84 (độ) sang tọa độ phẳng UTM 48N (mét) để đo khoảng cách chính xác
    order_utm = transform(_TO_UTM, order_point_wgs84)

    # Tạo đối tượng vùng đệm (Buffer Polygon) bán kính R mét
    buffer_utm = order_utm.buffer(radius_meters)
    buffer_wgs84 = transform(_TO_WGS84, buffer_utm)

    nearby = []
    for s in available:
        shp_utm = transform(_TO_UTM, s["geometry"])
        dist_m = round(shp_utm.distance(order_utm), 1)
        if shp_utm.within(buffer_utm):
            s_copy = dict(s)
            s_copy["distance_m"] = dist_m
            nearby.append(s_copy)

    nearby.sort(key=lambda item: item["distance_m"])
    return nearby, buffer_wgs84


def create_dispatch_route(shipper_point: Point, order_point: Point) -> LineString:
    """Tạo đối tượng hình học Vector dạng Đường (LineString 1-D) nối từ tài xế tới điểm giao hàng."""
    return LineString([shipper_point, order_point])


def compute_zone_statistics(zones: list, hubs: list, orders: list) -> pd.DataFrame:
    """Thống kê tổng hợp số lượng đơn hàng và doanh thu thu hộ COD theo từng phân khu bưu cục."""
    zone_map = {z["zone_id"]: z["zone_name"] for z in zones}
    stats_rows = []
    for h in hubs:
        hub_orders = [o for o in orders if o["assigned_hub_id"] == h["hub_id"]]
        total_orders = len(hub_orders)
        waiting_orders = sum(1 for o in hub_orders if o["status"] == "Chờ phân tuyến")
        delivering_orders = sum(1 for o in hub_orders if o["status"] == "Đã gán tài xế")
        completed_orders = sum(1 for o in hub_orders if o["status"] == "Hoàn tất")
        total_cod = sum(o["cod_amount"] for o in hub_orders)

        stats_rows.append({
            "Mã phân khu": h["zone_id"],
            "Tên phân khu": zone_map.get(h["zone_id"], ""),
            "Bưu cục phụ trách": h["hub_name"],
            "Tổng đơn hàng": total_orders,
            "Chờ phân tuyến": waiting_orders,
            "Đang giao": delivering_orders,
            "Hoàn tất": completed_orders,
            "Tổng tiền COD (VNĐ)": f"{total_cod:,.0f}",
        })
    return pd.DataFrame(stats_rows)
