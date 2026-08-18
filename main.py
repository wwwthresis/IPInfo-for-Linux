import io
import socket
import threading

import customtkinter as ctk
import requests
from PIL import Image

try:
    import speedtest
except ImportError:
    speedtest = None

ctk.set_default_color_theme("blue")

IP_API_URL = "http://ip-api.com/json/?fields=status,message,query,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org"
FLAG_URL_TEMPLATE = "https://flagcdn.com/w160/{code}.png"

FONT_FAMILY = "Segoe UI"


class RoundedCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            corner_radius=18,
            fg_color=("#f4f5f7", "#1f2126"),
            border_width=0,
            **kwargs,
        )


class IPInfoApp(ctk.CTk):
    WINDOW_W = 460
    WINDOW_H = 660

    def __init__(self):
        super().__init__()

        self.title("IP Info")

        self.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}")
        self.resizable(False, False)

        self.configure(fg_color=("#e9eaee", "#121317"))

        self.appearance_mode = "dark"
        ctk.set_appearance_mode(self.appearance_mode)

        self._build_ui()
        self.after(200, self.refresh_ip_info)

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 6))

        title_lbl = ctk.CTkLabel(
            header,
            text="IP Info",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(side="left")

        self.theme_btn = ctk.CTkButton(
            header,
            text="☀",
            width=40,
            height=36,
            corner_radius=12,
            font=ctk.CTkFont(size=16),
            fg_color=("#dcdde3", "#2a2c33"),
            hover_color=("#c9cad1", "#34363e"),
            text_color=("#1a1a1a", "#f5f5f5"),
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=(6, 0))

        self.tabs = ctk.CTkTabview(
            self,
            width=self.WINDOW_W - 56,
            fg_color="transparent",
            segmented_button_fg_color=("#dcdde3", "#1f2126"),
            segmented_button_selected_color=("#3a7ce0", "#3a7ce0"),
            segmented_button_selected_hover_color=("#2f6bcb", "#2f6bcb"),
        )
        self.tabs.pack(fill="both", expand=True, padx=28, pady=(10, 10))

        self.tab_ip = self.tabs.add("IP & Location")
        self.tab_speed = self.tabs.add("Network Speed")

        self._build_ip_tab(self.tab_ip)
        self._build_speed_tab(self.tab_speed)

        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=("#8a8d97", "#6d707a"),
        )
        self.status_label.pack(pady=(0, 14))

    def _build_ip_tab(self, parent):
        self.main_card = RoundedCard(parent)
        self.main_card.pack(fill="x", pady=(6, 8))

        self.flag_label = ctk.CTkLabel(self.main_card, text="", width=120, height=70)
        self.flag_label.pack(pady=(22, 8))

        self.ip_label = ctk.CTkLabel(
            self.main_card,
            text="—",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            cursor="hand2",
        )
        self.ip_label.pack(pady=(0, 2))
        self.ip_label.bind("<Button-1>", lambda e: self.copy_ip())

        self.copy_hint_label = ctk.CTkLabel(
            self.main_card,
            text="click IP to copy",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=("#9a9da7", "#6d707a"),
        )
        self.copy_hint_label.pack(pady=(0, 4))

        self.country_label = ctk.CTkLabel(
            self.main_card,
            text="Detecting…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=("#5b5e68", "#9a9da7"),
        )
        self.country_label.pack(pady=(0, 20))

        self.details_card = RoundedCard(parent)
        self.details_card.pack(fill="x", pady=8)

        self.detail_rows = {}
        for key, label in [
            ("local_ip", "Local IP"),
            ("city", "City"),
            ("region", "Region"),
            ("coords", "Coordinates"),
            ("timezone", "Timezone"),
            ("isp", "ISP"),
        ]:
            row = ctk.CTkFrame(self.details_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=7)

            name_lbl = ctk.CTkLabel(
                row,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=("#6d707a", "#8a8d97"),
                anchor="w",
                width=110,
            )
            name_lbl.pack(side="left")

            value_lbl = ctk.CTkLabel(
                row,
                text="—",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                anchor="e",
                justify="right",
                cursor="hand2" if key == "local_ip" else "arrow",
            )
            value_lbl.pack(side="right")

            if key == "local_ip":
                value_lbl.bind("<Button-1>", lambda e: self.copy_local_ip())

            self.detail_rows[key] = value_lbl

        spacer = ctk.CTkLabel(self.details_card, text="")
        spacer.pack(pady=2)

        self.refresh_btn = ctk.CTkButton(
            parent,
            text="⟳  Refresh",
            height=38,
            corner_radius=12,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self.refresh_ip_info,
        )
        self.refresh_btn.pack(fill="x", pady=(4, 6))

    def _build_speed_tab(self, parent):
        self.speed_card = RoundedCard(parent)
        self.speed_card.pack(fill="x", pady=(6, 8))

        info_lbl = ctk.CTkLabel(
            self.speed_card,
            text="Internet Speed Test",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        info_lbl.pack(pady=(20, 4))

        self.speed_server_label = ctk.CTkLabel(
            self.speed_card,
            text="No server selected",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=("#8a8d97", "#6d707a"),
        )
        self.speed_server_label.pack(pady=(0, 18))

        metrics_row = ctk.CTkFrame(self.speed_card, fg_color="transparent")
        metrics_row.pack(fill="x", padx=16, pady=(0, 20))

        self.speed_metrics = {}
        for key, label in [("ping", "Ping"), ("download", "Download"), ("upload", "Upload")]:
            col = ctk.CTkFrame(metrics_row, fg_color="transparent")
            col.pack(side="left", expand=True, fill="both")

            val_lbl = ctk.CTkLabel(
                col,
                text="—",
                font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            )
            val_lbl.pack()

            name_lbl = ctk.CTkLabel(
                col,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=("#8a8d97", "#6d707a"),
            )
            name_lbl.pack()

            self.speed_metrics[key] = val_lbl

        self.speed_progress = ctk.CTkProgressBar(parent)
        self.speed_progress.set(0)
        self.speed_progress.pack(fill="x", pady=(4, 10))
        self.speed_progress.pack_forget()

        self.speed_btn = ctk.CTkButton(
            parent,
            text="▶  Run Speed Test",
            height=38,
            corner_radius=12,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self.run_speed_test,
        )
        self.speed_btn.pack(fill="x", pady=(4, 6))

        if speedtest is None:
            self.speed_btn.configure(
                state="disabled", text="speedtest-cli not installed"
            )

    def toggle_theme(self):
        if self.appearance_mode == "dark":
            self.appearance_mode = "light"
            self.theme_btn.configure(text="🌙")
        else:
            self.appearance_mode = "dark"
            self.theme_btn.configure(text="☀")
        ctk.set_appearance_mode(self.appearance_mode)

    def copy_ip(self):
        ip_text = self.ip_label.cget("text")
        if ip_text and ip_text not in ("—", "Error"):
            self.clipboard_clear()
            self.clipboard_append(ip_text)
            self._flash_status(f"Copied: {ip_text}")

    def copy_local_ip(self):
        ip_text = self.detail_rows["local_ip"].cget("text")
        if ip_text and ip_text != "—":
            self.clipboard_clear()
            self.clipboard_append(ip_text)
            self._flash_status(f"Copied: {ip_text}")

    def _flash_status(self, text):
        self.status_label.configure(text=text)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "—"

    def refresh_ip_info(self):
        self.refresh_btn.configure(state="disabled", text="…")
        self.status_label.configure(text="Fetching data…")
        self.ip_label.configure(text="—")
        self.country_label.configure(text="Detecting…")
        for lbl in self.detail_rows.values():
            lbl.configure(text="—")
        self.flag_label.configure(image=None, text="")

        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        local_ip = self.get_local_ip()

        try:
            resp = requests.get(IP_API_URL, timeout=8)
            data = resp.json()
            if data.get("status") != "success":
                raise RuntimeError(data.get("message", "Unknown error"))
        except Exception as e:
            error_message = str(e)
            self.after(0, lambda: self._show_error(error_message, local_ip))
            return

        flag_img = None
        code = data.get("countryCode", "").lower()
        if code:
            try:
                flag_resp = requests.get(FLAG_URL_TEMPLATE.format(code=code), timeout=8)
                if flag_resp.status_code == 200:
                    pil_img = Image.open(io.BytesIO(flag_resp.content)).convert("RGBA")
                    w, h = pil_img.size
                    target_w = 120
                    target_h = int(h * (target_w / w))
                    pil_img = pil_img.resize((target_w, target_h), Image.LANCZOS)
                    flag_img = ctk.CTkImage(
                        light_image=pil_img, dark_image=pil_img, size=(target_w, target_h)
                    )
            except Exception:
                flag_img = None

        self.after(0, lambda: self._show_data(data, flag_img, local_ip))

    def _show_data(self, data, flag_img, local_ip):
        self.refresh_btn.configure(state="normal", text="⟳  Refresh")

        ip = data.get("query", "—")
        country = data.get("country", "—")
        country_code = data.get("countryCode", "")
        city = data.get("city", "—")
        region = data.get("regionName", "—")
        lat = data.get("lat")
        lon = data.get("lon")
        tz = data.get("timezone", "—")
        isp = data.get("isp") or data.get("org") or "—"

        self.ip_label.configure(text=ip)
        self.country_label.configure(
            text=f"{country} ({country_code})" if country_code else country
        )

        if flag_img:
            self.flag_label.configure(image=flag_img, text="")
            self.flag_label.image = flag_img
        else:
            self.flag_label.configure(text="🏳️", image=None, font=ctk.CTkFont(size=48))

        self.detail_rows["local_ip"].configure(text=local_ip)
        self.detail_rows["city"].configure(text=city)
        self.detail_rows["region"].configure(text=region)
        if lat is not None and lon is not None:
            self.detail_rows["coords"].configure(text=f"{lat:.4f}, {lon:.4f}")
        else:
            self.detail_rows["coords"].configure(text="—")
        self.detail_rows["timezone"].configure(text=tz)
        self.detail_rows["isp"].configure(text=isp)

        self.status_label.configure(text="Data updated • ip-api.com")

    def _show_error(self, message, local_ip):
        self.refresh_btn.configure(state="normal", text="⟳  Refresh")
        self.ip_label.configure(text="Error")
        self.country_label.configure(text="Failed to get data")
        self.detail_rows["local_ip"].configure(text=local_ip)
        self.status_label.configure(text=f"Error: {message}. Check internet connection.")

    def run_speed_test(self):
        if speedtest is None:
            return

        self.speed_btn.configure(state="disabled", text="Testing…")
        self.speed_progress.pack(fill="x", pady=(4, 10))
        self.speed_progress.set(0)
        self.speed_server_label.configure(text="Finding nearest server…")
        for lbl in self.speed_metrics.values():
            lbl.configure(text="—")

        threading.Thread(target=self._speed_test_worker, daemon=True).start()

    def _speed_test_worker(self):
        try:
            st = speedtest.Speedtest()
            self.after(0, lambda: self.speed_progress.set(0.1))

            st.get_best_server()
            server = st.results.server
            server_text = f"{server.get('sponsor', '—')} · {server.get('name', '—')}"
            self.after(0, lambda: self.speed_server_label.configure(text=server_text))
            self.after(0, lambda: self.speed_progress.set(0.25))

            ping_ms = st.results.ping
            self.after(0, lambda: self.speed_metrics["ping"].configure(text=f"{ping_ms:.0f} ms"))
            self.after(0, lambda: self.speed_progress.set(0.35))

            download_bps = st.download()
            download_mbps = download_bps / 1_000_000
            self.after(
                0,
                lambda: self.speed_metrics["download"].configure(
                    text=f"{download_mbps:.1f} Mbps"
                ),
            )
            self.after(0, lambda: self.speed_progress.set(0.7))

            upload_bps = st.upload()
            upload_mbps = upload_bps / 1_000_000
            self.after(
                0,
                lambda: self.speed_metrics["upload"].configure(
                    text=f"{upload_mbps:.1f} Mbps"
                ),
            )
            self.after(0, lambda: self.speed_progress.set(1.0))

            self.after(0, lambda: self.status_label.configure(text="Speed test completed"))
        except Exception as e:
            error_message = str(e)
            self.after(0, lambda: self._show_speed_error(error_message))
            return

        self.after(0, self._finish_speed_test)

    def _finish_speed_test(self):
        self.speed_btn.configure(state="normal", text="▶  Run Speed Test")
        self.after(600, self.speed_progress.pack_forget)

    def _show_speed_error(self, message):
        self.speed_btn.configure(state="normal", text="▶  Run Speed Test")
        self.speed_server_label.configure(text="Test failed")
        self.status_label.configure(text=f"Speed test error: {message}")
        self.speed_progress.pack_forget()


if __name__ == "__main__":
    app = IPInfoApp()
    app.mainloop()
