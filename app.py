from datetime import datetime
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import pandas as pd
from shapely.geometry import Point, mapping

from seed_data import generate_sample_data
from gis_engine import (
    load_spatial_layers,
    save_orders,
    save_shippers,
    assign_hub_by_topology,
    find_nearest_shippers,
    create_dispatch_route,
    compute_zone_statistics,
)

st.set_page_config(
    page_title="WebGIS Logistics Cầu Giấy - EPU",
    page_icon="🗺️",
    layout="wide",
)

# Khởi tạo dữ liệu mẫu GeoJSON nếu chưa tồn tại
generate_sample_data(force=False)
zones, hubs, shippers, orders = load_spatial_layers()

# Tâm bản đồ quận Cầu Giấy, Hà Nội
CAU_GIAY_CENTER = [21.0315, 105.7875]

st.title("🗺️ HỆ THỐNG WEBGIS QUẢN LÝ VÀ ĐIỀU PHỐI GIAO NHẬN HÀNG HÓA")
st.caption("Khu vực nghiên cứu: Quận Cầu Giấy, Thành phố Hà Nội)")

# Thanh bên hiển thị chỉ số nhanh & nút khôi phục dữ liệu
with st.sidebar:
    st.header("📊 Tổng quan vận hành")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Tổng đơn hàng", len(orders))
    col_s2.metric("Chờ điều phối", sum(1 for o in orders if o["status"] == "Chờ phân tuyến"))

    col_s3, col_s4 = st.columns(2)
    col_s3.metric("Shipper rảnh", sum(1 for s in shippers if s["status"] == "Rảnh"))
    col_s4.metric("Số bưu cục", len(hubs))

    st.divider()
    st.markdown("**Thông số kỹ thuật GIS:**")
    st.markdown("- Hệ tọa độ lưu trữ: `WGS-84 (EPSG:4326)`")
    st.markdown("- Hệ tọa độ đo đạc: `UTM 48N (EPSG:32648)`")
    st.markdown("- Mô hình dữ liệu: `Vector (Point, Line, Polygon)`")
    st.divider()

    if st.button("🔄 Khôi phục dữ liệu mẫu ban đầu", use_container_width=True):
        generate_sample_data(force=True)
        st.success("Đã khôi phục 30 đơn hàng và 15 shipper mẫu!")
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Bản đồ giám sát & Phân lớp",
    "2️⃣ Tạo đơn & Phân tuyến Topology",
    "3️⃣ Điều phối Shipper theo bán kính",
    "4️⃣ Bản đồ nhiệt (Heatmap) & Thống kê",
])

# ==============================================================================
# TAB 1: BẢN ĐỒ GIÁM SÁT TỔNG THỂ & LAYER CONTROL
# ==============================================================================
with tab1:
    st.subheader("Bản đồ giám sát đa lớp đối tượng Vector tại quận Cầu Giấy")
    m1 = folium.Map(location=CAU_GIAY_CENTER, zoom_start=13, tiles="OpenStreetMap")

    # Lớp 1: Phân khu giao hàng (Polygon)
    fg_zones = folium.FeatureGroup(name="Phân khu giao hàng (Polygon)", show=True)
    for z in zones:
        folium.GeoJson(
            mapping(z["geometry"]),
            style_function=lambda x, color=z["color"]: {
                "fillColor": color,
                "color": color,
                "weight": 2.5,
                "fillOpacity": 0.16,
            },
            tooltip=f"{z['zone_name']} ({z['zone_id']})",
            popup=folium.Popup(
                f"<b>{z['zone_name']}</b><br>Mã vùng: {z['zone_id']}<br>Phường: {z['wards']}",
                max_width=260,
            ),
        ).add_to(fg_zones)
    fg_zones.add_to(m1)

    # Lớp 2: Bưu cục (Point)
    fg_hubs = folium.FeatureGroup(name="Bưu cục trung chuyển (Point)", show=True)
    for h in hubs:
        folium.Marker(
            location=[h["geometry"].y, h["geometry"].x],
            tooltip=f"🏢 {h['hub_name']}",
            popup=folium.Popup(
                f"<b>{h['hub_name']}</b><br>Mã: {h['hub_id']}<br>Địa chỉ: {h['address']}<br>Công suất: {h['capacity']} đơn/ngày",
                max_width=280,
            ),
            icon=folium.Icon(color="darkblue", icon="home", prefix="fa"),
        ).add_to(fg_hubs)
    fg_hubs.add_to(m1)

    # Lớp 3: Tài xế Shipper (Point)
    fg_shippers = folium.FeatureGroup(name="Đội ngũ Shipper (Point)", show=True)
    for s in shippers:
        icon_color = "green" if s["status"] == "Rảnh" else "orange"
        folium.Marker(
            location=[s["geometry"].y, s["geometry"].x],
            tooltip=f"🛵 {s['full_name']} ({s['status']})",
            popup=folium.Popup(
                f"<b>{s['full_name']}</b> ({s['shipper_id']})<br>Biển số: {s['vehicle_plate']}<br>Trạng thái: <b>{s['status']}</b>",
                max_width=250,
            ),
            icon=folium.Icon(color=icon_color, icon="motorcycle", prefix="fa"),
        ).add_to(fg_shippers)
    fg_shippers.add_to(m1)

    # Lớp 4: Đơn hàng (Point)
    fg_orders = folium.FeatureGroup(name="Điểm giao đơn hàng (Point)", show=True)
    status_colors = {
        "Chờ phân tuyến": "red",
        "Đã gán tài xế": "purple",
        "Hoàn tất": "cadetblue",
    }
    for o in orders:
        folium.CircleMarker(
            location=[o["geometry"].y, o["geometry"].x],
            radius=6,
            color=status_colors.get(o["status"], "blue"),
            fill=True,
            fill_opacity=0.85,
            tooltip=f"📦 {o['order_id']} - {o['status']}",
            popup=folium.Popup(
                f"<b>Đơn hàng: {o['order_id']}</b><br>"
                f"Khách hàng: {o['customer_name']}<br>"
                f"Địa chỉ: {o['address']}<br>"
                f"Thu hộ COD: {o['cod_amount']:,.0f} đ<br>"
                f"Bưu cục: {o['assigned_hub_id']}<br>"
                f"Trạng thái: <b>{o['status']}</b>",
                max_width=280,
            ),
        ).add_to(fg_orders)
    fg_orders.add_to(m1)

    folium.LayerControl(collapsed=False).add_to(m1)
    st_folium(m1, width="100%", height=540, key="map_overview")


# ==============================================================================
# TAB 2: TẠO ĐƠN HÀNG & TỰ ĐỘNG PHÂN TUYẾN (POINT-IN-POLYGON TOPOLOGY)
# ==============================================================================
with tab2:
    st.subheader("Tự động phân tuyến bưu cục theo quan hệ không gian Điểm – Vùng (Point-in-Polygon)")
    col_form, col_map2 = st.columns([1, 1.4])

    with col_form:
        st.info("💡 Mẹo: Bạn có thể click trực tiếp lên bản đồ bên phải để tự động lấy tọa độ (Lat, Lng) hoặc nhập thủ công.")
        default_lat = st.session_state.get("picked_lat", 21.0378)
        default_lng = st.session_state.get("picked_lng", 105.7842)

        with st.form("create_order_form"):
            customer_name = st.text_input("Tên khách hàng", value="Nguyễn Minh Hoàng")
            address = st.text_input("Địa chỉ giao hàng", value="Số 175 Xuân Thủy, Dịch Vọng Hậu, Cầu Giấy")
            cod_amount = st.number_input("Tiền thu hộ COD (VNĐ)", min_value=0, value=280000, step=10000)
            c_lat, c_lng = st.columns(2)
            lat_input = c_lat.number_input("Vĩ độ (Latitude - Y)", value=float(default_lat), format="%.6f")
            lng_input = c_lng.number_input("Kinh độ (Longitude - X)", value=float(default_lng), format="%.6f")

            submitted = st.form_submit_button("🚀 Kiểm tra Topology & Tạo đơn hàng", use_container_width=True)

        if submitted:
            topo_result = assign_hub_by_topology(lat_input, lng_input, zones, hubs)
            if topo_result["in_service_area"]:
                new_id = f"ORD_2026_{len(orders) + 1:03d}"
                orders.append({
                    "order_id": new_id,
                    "customer_name": customer_name,
                    "address": address,
                    "cod_amount": float(cod_amount),
                    "status": "Chờ phân tuyến",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "assigned_hub_id": topo_result["hub_id"],
                    "assigned_shipper_id": "",
                    "geometry": Point(lng_input, lat_input),
                })
                save_orders(orders)

                msg_success = (
                    f"✅ **Đã tạo đơn `{new_id}` thành công!**\n\n"
                    f"- Quan hệ Topology: Điểm `({lat_input}, {lng_input})` nằm trong **{topo_result['zone_name']}**\n"
                    f"- Tự động phân tuyến về: **{topo_result['hub_name']} (`{topo_result['hub_id']}`)**"
                )
                st.success(msg_success)
            else:
                st.error(f"⚠️ {topo_result['message']}")

    with col_map2:
        m2 = folium.Map(location=[default_lat, default_lng], zoom_start=13)
        for z in zones:
            folium.GeoJson(
                mapping(z["geometry"]),
                style_function=lambda x, color=z["color"]: {
                    "fillColor": color,
                    "color": color,
                    "weight": 2,
                    "fillOpacity": 0.2,
                },
                tooltip=z["zone_name"],
            ).add_to(m2)

        for h in hubs:
            folium.Marker(
                location=[h["geometry"].y, h["geometry"].x],
                tooltip=h["hub_name"],
                icon=folium.Icon(color="darkblue", icon="home", prefix="fa"),
            ).add_to(m2)

        folium.Marker(
            location=[default_lat, default_lng],
            tooltip="Vị trí đơn hàng đang chọn",
            icon=folium.Icon(color="red", icon="map-pin", prefix="fa"),
        ).add_to(m2)

        map_data = st_folium(m2, width="100%", height=470, key="map_create_order")
        if map_data and map_data.get("last_clicked"):
            clicked_lat = round(map_data["last_clicked"]["lat"], 6)
            clicked_lng = round(map_data["last_clicked"]["lng"], 6)
            if clicked_lat != default_lat or clicked_lng != default_lng:
                st.session_state["picked_lat"] = clicked_lat
                st.session_state["picked_lng"] = clicked_lng
                st.rerun()


# ==============================================================================
# TAB 3: ĐIỀU PHỐI SHIPPER THEO BÁN KÍNH (BUFFER & NEAREST NEIGHBOR)
# ==============================================================================
with tab3:
    st.subheader("Tìm kiếm Shipper gần nhất trong vùng đệm bán kính R (hệ tọa độ UTM 48N)")
    waiting_orders = [o for o in orders if o["status"] == "Chờ phân tuyến"]

    if not waiting_orders:
        st.success("🎉 Tất cả đơn hàng hiện tại đều đã được điều phối tài xế!")
    else:
        col_ctrl, col_map3 = st.columns([1, 1.4])
        with col_ctrl:
            order_options = [o["order_id"] for o in waiting_orders]
            selected_order_id = st.selectbox("1. Chọn đơn hàng chờ điều phối:", order_options)
            selected_order = next(o for o in waiting_orders if o["order_id"] == selected_order_id)

            info_md = (
                f"- **Khách hàng:** {selected_order['customer_name']}\n"
                f"- **Địa chỉ:** {selected_order['address']}\n"
                f"- **Bưu cục quản lý:** `{selected_order['assigned_hub_id']}`\n"
                f"- **Tọa độ:** `({selected_order['geometry'].y:.6f}, {selected_order['geometry'].x:.6f})`"
            )
            st.markdown(info_md)

            radius_km = st.slider(
                "2. Chọn bán kính vùng đệm Buffer (km):",
                min_value=0.5,
                max_value=3.0,
                value=1.5,
                step=0.25,
            )
            nearby_shippers, buffer_poly = find_nearest_shippers(
                selected_order["geometry"], shippers, radius_meters=radius_km * 1000
            )

            chosen_shipper = None
            if not nearby_shippers:
                st.warning(f"Không có Shipper nào đang 'Rảnh' trong bán kính {radius_km} km. Hãy tăng bán kính tìm kiếm!")
            else:
                st.markdown(f"**3. Danh sách {len(nearby_shippers)} Shipper rảnh trong bán kính {radius_km} km:**")
                display_df = pd.DataFrame([
                    {
                        "Mã Shipper": s["shipper_id"],
                        "Họ tên": s["full_name"],
                        "Biển số": s["vehicle_plate"],
                        "Khoảng cách (m)": s["distance_m"],
                    }
                    for s in nearby_shippers
                ])
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                chosen_shp_id = st.selectbox(
                    "4. Chọn tài xế gán đơn (mặc định gần nhất):",
                    [s["shipper_id"] for s in nearby_shippers],
                )
                chosen_shipper = next(s for s in nearby_shippers if s["shipper_id"] == chosen_shp_id)

                if st.button("✅ Xác nhận điều phối Shipper này", use_container_width=True):
                    for o in orders:
                        if o["order_id"] == selected_order_id:
                            o["status"] = "Đã gán tài xế"
                            o["assigned_shipper_id"] = chosen_shp_id
                    for s in shippers:
                        if s["shipper_id"] == chosen_shp_id:
                            s["status"] = "Đang giao"

                    save_orders(orders)
                    save_shippers(shippers)
                    st.success(f"Đã điều phối **{chosen_shipper['full_name']}** nhận đơn **{selected_order_id}**!")
                    st.rerun()

        with col_map3:
            m3 = folium.Map(
                location=[selected_order["geometry"].y, selected_order["geometry"].x],
                zoom_start=14,
            )

            if buffer_poly is not None:
                folium.GeoJson(
                    mapping(buffer_poly),
                    style_function=lambda x: {
                        "fillColor": "#0EA5E9",
                        "color": "#0284C7",
                        "weight": 2,
                        "fillOpacity": 0.18,
                        "dashArray": "5, 5",
                    },
                    tooltip=f"Vùng đệm Buffer bán kính {radius_km} km",
                ).add_to(m3)

            folium.Marker(
                location=[selected_order["geometry"].y, selected_order["geometry"].x],
                tooltip=f"📦 Đơn hàng {selected_order_id}",
                icon=folium.Icon(color="red", icon="cube", prefix="fa"),
            ).add_to(m3)

            if nearby_shippers:
                for s in nearby_shippers:
                    folium.Marker(
                        location=[s["geometry"].y, s["geometry"].x],
                        tooltip=f"🛵 {s['full_name']} - Cách {s['distance_m']}m",
                        icon=folium.Icon(color="green", icon="motorcycle", prefix="fa"),
                    ).add_to(m3)

                if chosen_shipper is not None:
                    route_line = create_dispatch_route(chosen_shipper["geometry"], selected_order["geometry"])
                    folium.PolyLine(
                        locations=[(lat, lng) for lng, lat in route_line.coords],
                        color="#DC2626",
                        weight=4,
                        tooltip=f"Tuyến điều phối: {chosen_shipper['distance_m']} m",
                    ).add_to(m3)

            st_folium(m3, width="100%", height=500, key="map_dispatch")


# ==============================================================================
# TAB 4: BẢN ĐỒ NHIỆT (HEATMAP) & THỐNG KÊ THEO PHÂN KHU
# ==============================================================================
with tab4:
    st.subheader("Bản đồ nhiệt mật độ đơn hàng (Heatmap) và Thống kê phân khu")
    stats_df = compute_zone_statistics(zones, hubs, orders)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

    m4 = folium.Map(location=CAU_GIAY_CENTER, zoom_start=13, tiles="CartoDB positron")

    for z in zones:
        folium.GeoJson(
            mapping(z["geometry"]),
            style_function=lambda x, color=z["color"]: {
                "fillColor": "transparent",
                "color": color,
                "weight": 2.5,
            },
            tooltip=z["zone_name"],
        ).add_to(m4)

    heat_data = [
        [o["geometry"].y, o["geometry"].x, o["cod_amount"] / 100000.0]
        for o in orders
    ]
    HeatMap(heat_data, radius=24, blur=16, max_zoom=15).add_to(m4)

    st_folium(m4, width="100%", height=480, key="map_heatmap")
