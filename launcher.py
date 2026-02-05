#!/usr/bin/env python3
"""
Launcher con Interfaz Gráfica (GUI) para el Sistema de Comprobantes.
Usa customtkinter para una apariencia moderna.
"""
import os
import sys
import json
import threading
import subprocess
import time
import signal
import psutil
import logging
import shutil
from datetime import datetime
import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox
from app.license import LicenseManager
from app.paths import (
    get_config_path,
    get_resource_dir,
    get_qr_path,
    get_usage_log_path,
    resolve_appdata_path,
    get_app_data_dir,
)
from storage.session_accumulator import get_accumulator, SessionAccumulator

# Configurar apariencia
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Paleta Premium - Teal oscuro con fondos cálidos
COLOR_BG = "#E8E4DE"
COLOR_BG_DARK = "#D9D4CC"
COLOR_CARD = "#FAFAF8"
COLOR_CARD_HOVER = "#F5F4F2"
COLOR_ACCENT = "#0D5C5A"
COLOR_ACCENT_DARK = "#073D3C"
COLOR_ACCENT_LIGHT = "#1A8A87"
COLOR_ACCENT_SOFT = "#D4EDEB"
COLOR_TEXT = "#1A1A1A"
COLOR_TEXT_SECONDARY = "#3D3D3D"
COLOR_MUTED = "#6E7179"
COLOR_BORDER = "#D4CFC6"
COLOR_BORDER_LIGHT = "#E8E4DE"
COLOR_SUCCESS = "#1D6F42"
COLOR_SUCCESS_SOFT = "#D4EDE0"
COLOR_WARNING = "#B5651D"
COLOR_WARNING_SOFT = "#F5E6D3"
COLOR_DANGER = "#B33A34"
COLOR_DANGER_SOFT = "#F5D4D2"
COLOR_GRADIENT_START = "#0D5C5A"
COLOR_GRADIENT_END = "#1A8A87"

# Config path
CONFIG_PATH = get_config_path()

class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Acerca de")
        self.geometry("500x400")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        
        # Centrar en pantalla (aprox)
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 200
        self.geometry(f"+{x}+{y}")
        self.transient(parent)
        self.grab_set()
        
        # Contenido
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(
            main_frame, 
            text="Sistema de Comprobantes", 
            font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
            text_color=COLOR_ACCENT
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            main_frame, 
            text="Versión 1.0.0", 
            font=ctk.CTkFont(family="Arial", size=14),
            text_color=COLOR_MUTED
        ).pack(pady=(0, 20))
        
        # Separador decorativo
        ctk.CTkFrame(main_frame, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=40, pady=10)
        
        # Info
        info_text = (
            "Esta aplicación automatiza la gestión y envío de\n"
            "comprobantes de transferencia mediante WhatsApp.\n\n"
            "Desarrollada para optimizar flujos de trabajo administrativos."
        )
        ctk.CTkLabel(
            main_frame, 
            text=info_text,
            font=ctk.CTkFont(family="Arial", size=13),
            text_color=COLOR_TEXT,
            justify="center"
        ).pack(pady=20)
        
        # Créditos
        credit_frame = ctk.CTkFrame(main_frame, fg_color=COLOR_ACCENT_SOFT, corner_radius=10)
        credit_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            credit_frame,
            text="Hecho 100% por Leonardo Caliva\nen febrero de 2026",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color=COLOR_ACCENT_DARK,
            justify="center"
        ).pack(padx=20, pady=15)
        
        # Botón cerrar
        ctk.CTkButton(
            main_frame,
            text="Cerrar",
            command=self.destroy,
            fg_color=COLOR_BG_DARK,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BORDER,
            width=100
        ).pack(side="bottom", pady=10)

class SystemLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Comprobantes")
        self.geometry("980x680")
        self.minsize(980, 680)
        self.resizable(True, True)
        self.configure(fg_color=COLOR_BG)

        if sys.platform == "win32":
            font_primary = "Aptos"
            font_display = "Aptos Display"
            font_mono = "Cascadia Mono"
        elif sys.platform == "darwin":
            font_primary = "Avenir Next"
            font_display = "Avenir Next Demi Bold"
            font_mono = "Menlo"
        else:
            font_primary = "Noto Sans"
            font_display = "Noto Sans"
            font_mono = "DejaVu Sans Mono"

        self.font_title = ctk.CTkFont(family=font_display, size=28, weight="bold")
        self.font_subtitle = ctk.CTkFont(family=font_primary, size=14)
        self.font_section = ctk.CTkFont(family=font_primary, size=16, weight="bold")
        self.font_body = ctk.CTkFont(family=font_primary, size=13)
        self.font_small = ctk.CTkFont(family=font_primary, size=11)
        self.font_tiny = ctk.CTkFont(family=font_primary, size=10)
        self.font_mono = ctk.CTkFont(family=font_mono, size=12)
        self.font_stat = ctk.CTkFont(family=font_display, size=32, weight="bold")
        self.font_stat_label = ctk.CTkFont(family=font_primary, size=11)

        # Variables de estado
        self.process_api = None
        self.process_bot = None
        self.is_running = False
        self.qr_path = get_qr_path()
        self.qr_last_mtime = 0
        self.qr_image = None
        
        # Cargar configuración
        self.config = self.load_config()
        
        # Verificar Licencia
        self.license_active, self.license_msg = self.check_license()

        # Estado de configuración
        self.first_run = self.is_first_run()
        
        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabs
        self.tabview = ctk.CTkTabview(self, width=940, height=620, corner_radius=20, fg_color=COLOR_BG_DARK, segmented_button_fg_color=COLOR_BG_DARK)
        self.tabview.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        
        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_config = self.tabview.add("Configuración")
        self.tab_logs = self.tabview.add("Logs")

        self.tab_dashboard.configure(fg_color=COLOR_BG_DARK)
        self.tab_config.configure(fg_color=COLOR_BG_DARK)
        self.tab_logs.configure(fg_color=COLOR_BG_DARK)

        self.tabview._segmented_button.configure(
            fg_color=COLOR_BG_DARK,
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_DARK,
            unselected_color=COLOR_BG_DARK,
            unselected_hover_color=COLOR_BG,
            text_color=COLOR_MUTED,
            text_color_disabled=COLOR_MUTED,
            font=self.font_body
        )

        # --- TAB DASHBOARD ---
        self.setup_dashboard()
        
        # --- TAB CONFIG ---
        self.setup_config()
        
        # --- TAB LOGS ---
        self.setup_logs()

        # Estado inicial de configuración
        self.update_config_status()
        if self.first_run:
            self.tabview.set("Configuración")
        
        # Iniciar thread de monitoreo de costos
        self.monitor_thread = threading.Thread(target=self.update_stats_loop, daemon=True)
        self.monitor_thread.start()

        # Loop de QR
        self.after(2000, self.refresh_qr_loop)

    def bind_mousewheel_to_scrollable(self, scrollable_frame):
        """Habilita scroll con rueda del mouse en un CTkScrollableFrame."""
        def on_mousewheel(event):
            # Para Windows y Linux
            if event.delta:
                scrollable_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            # Para macOS
            elif event.num == 4:
                scrollable_frame._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                scrollable_frame._parent_canvas.yview_scroll(1, "units")

        def bind_to_widget(widget):
            # Windows/macOS
            widget.bind("<MouseWheel>", on_mousewheel)
            # Linux
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
            # Recursivamente bindear a todos los hijos
            for child in widget.winfo_children():
                bind_to_widget(child)

        bind_to_widget(scrollable_frame)
        # También bindear al canvas padre
        scrollable_frame._parent_canvas.bind("<MouseWheel>", on_mousewheel)
        scrollable_frame._parent_canvas.bind("<Button-4>", on_mousewheel)
        scrollable_frame._parent_canvas.bind("<Button-5>", on_mousewheel)

    def ensure_config_file(self):
        if os.path.exists(CONFIG_PATH):
            return

        resource_dir = get_resource_dir()
        example_path = os.path.join(resource_dir, "config.example.json")
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

        if os.path.exists(example_path):
            shutil.copy2(example_path, CONFIG_PATH)
        else:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def load_config(self):
        try:
            self.ensure_config_file()
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self):
        try:
            # Update config object from UI
            self.config.setdefault('fuentes', {})
            self.config.setdefault('storage', {})

            self.config['fuentes']['whatsapp_enabled'] = self.chk_whatsapp.get()
            self.config['fuentes']['carpeta_enabled'] = self.chk_folder.get()
            self.config['fuentes']['carpeta_ruta'] = self.entry_folder.get().strip()

            self.config['storage']['excel_enabled'] = self.chk_excel.get()
            self.config['storage']['excel_path'] = self.entry_excel.get().strip()
            self.config['storage']['sheets_enabled'] = self.chk_sheets.get()
            self.config['storage']['sheets_id'] = self.entry_sheets_id.get().strip()
            self.config['storage']['sheets_name'] = self.entry_sheets_name.get().strip() or "Hoja 1"

            existing_openai = self.config.get('openai_api_key', '').strip()
            entry_openai = self.entry_openai_key.get().strip() if hasattr(self, "entry_openai_key") else ""
            self.config['openai_api_key'] = entry_openai or existing_openai
            self.config['google_credentials_path'] = self.entry_google_credentials.get().strip()
            
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            self.log_message("✅ Configuración guardada correctamente.")
            self.update_config_status()
        except Exception as e:
            self.log_message(f"❌ Error al guardar configuración: {e}")

    def check_license(self):
        try:
            client_id = self.config.get("client_id", "")
            license_url = self.config.get("license_url", "")
            if not client_id:
                return True, "Modo Developer"
            lm = LicenseManager(client_id, license_url)
            return lm.check_license()
        except:
            return True, "Error verificando (Offline)"

    def is_first_run(self):
        if self.config.get("openai_api_key", "").strip():
            return False
        return not os.environ.get("OPENAI_API_KEY", "")

    def create_card(self, parent, title, accent=False):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_ACCENT if accent else COLOR_CARD,
            corner_radius=20,
            border_width=0 if accent else 1,
            border_color=COLOR_BORDER
        )
        text_color = "white" if accent else COLOR_TEXT
        label = ctk.CTkLabel(card, text=title, font=self.font_section, text_color=text_color)
        label.pack(anchor="w", padx=20, pady=(18, 10))
        return card

    def get_openai_key(self):
        if hasattr(self, "entry_openai_key"):
            value = self.entry_openai_key.get().strip()
            if value:
                return value
        config_value = self.config.get("openai_api_key", "").strip()
        if config_value:
            return config_value
        return os.environ.get("OPENAI_API_KEY", "")

    def get_config_issues(self):
        issues = []
        if not (self.chk_whatsapp.get() or self.chk_folder.get()):
            issues.append("Active WhatsApp o carpeta local")

        if not (self.chk_excel.get() or self.chk_sheets.get()):
            issues.append("Active Excel o Google Sheets")

        if self.chk_folder.get():
            folder = self.entry_folder.get().strip()
            if not folder:
                issues.append("Complete la ruta de carpeta")
            elif not os.path.exists(folder):
                issues.append("La carpeta no existe")

        if self.chk_sheets.get():
            if not self.entry_sheets_id.get().strip():
                issues.append("Falta ID de Google Sheet")
            if not self.entry_google_credentials.get().strip():
                issues.append("Faltan credenciales de Google")

        if not self.get_openai_key():
            issues.append("Falta clave OpenAI (soporte)")

        return issues

    def update_config_status(self):
        if not hasattr(self, "chk_whatsapp"):
            return
        issues = self.get_config_issues()
        if hasattr(self, "config_hint_label"):
            if issues:
                self.config_hint_label.configure(
                    text="Configuración incompleta: " + " | ".join(issues),
                    text_color=COLOR_WARNING
                )
            else:
                self.config_hint_label.configure(
                    text="Configuración lista para iniciar",
                    text_color=COLOR_SUCCESS
                )

        if hasattr(self, "btn_start") and not self.is_running:
            self.btn_start.configure(state="disabled" if issues else "normal")

        if hasattr(self, "btn_test_sheets"):
            self.btn_test_sheets.configure(state="normal" if self.chk_sheets.get() else "disabled")

        self.update_excel_path_label()
        self.update_openai_status()
        self.render_config_chips()

    def update_openai_status(self):
        if not hasattr(self, "lbl_openai_status"):
            return
        if self.get_openai_key():
            self.lbl_openai_status.configure(text="OpenAI configurada (soporte)", text_color=COLOR_SUCCESS)
        else:
            self.lbl_openai_status.configure(text="OpenAI pendiente (soporte)", text_color=COLOR_WARNING)

    def render_config_chips(self):
        if not hasattr(self, "chips_frame"):
            return
        for child in self.chips_frame.winfo_children():
            child.destroy()

        chips = []
        if self.chk_whatsapp.get():
            chips.append("WhatsApp")
        if self.chk_folder.get():
            chips.append("Carpeta local")
        if self.chk_excel.get():
            chips.append("Excel")
        if self.chk_sheets.get():
            chips.append("Google Sheets")
        if self.get_openai_key():
            chips.append("OpenAI")

        if not chips:
            chips.append("Sin fuentes activas")

        for label in chips:
            chip = ctk.CTkFrame(self.chips_frame, fg_color=COLOR_ACCENT_SOFT, corner_radius=999, border_width=1, border_color=COLOR_BORDER)
            ctk.CTkLabel(
                chip,
                text=label,
                font=self.font_small,
                text_color=COLOR_TEXT,
                padx=10,
                pady=4
            ).pack()
            chip.pack(side="left", padx=(0, 8), pady=2)

    def update_excel_path_label(self):
        if not hasattr(self, "lbl_excel_path"):
            return
        excel_path = resolve_appdata_path(
            self.entry_excel.get().strip() or "transferencias.xlsx",
            fallback_name="transferencias.xlsx"
        )
        # Asegurar que muestre extensión .xlsx
        if not excel_path.lower().endswith('.xlsx'):
            excel_path += '.xlsx'
        self.lbl_excel_path.configure(text=excel_path)

    def set_system_status(self, status_text, color):
        if hasattr(self, "lbl_status"):
            self.lbl_status.configure(text=status_text, text_color=color)
        if hasattr(self, "status_pill"):
            self.status_pill.configure(fg_color=color)
        if hasattr(self, "status_pill_label"):
            self.status_pill_label.configure(text=status_text.upper())

    def open_data_folder(self):
        path = get_app_data_dir()
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, path)
            self.update_config_status()

    def browse_excel_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if path:
            self.entry_excel.delete(0, "end")
            self.entry_excel.insert(0, path)
            self.update_config_status()

    def browse_google_credentials(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        if path:
            self.entry_google_credentials.delete(0, "end")
            self.entry_google_credentials.insert(0, path)
            self.update_config_status()

    def toggle_folder_fields(self):
        state = "normal" if self.chk_folder.get() else "disabled"
        self.entry_folder.configure(state=state)
        self.btn_browse_folder.configure(state=state)
        self.update_config_status()

    def toggle_storage_fields(self):
        excel_state = "normal" if self.chk_excel.get() else "disabled"
        self.entry_excel.configure(state=excel_state)
        self.btn_browse_excel.configure(state=excel_state)

        sheets_state = "normal" if self.chk_sheets.get() else "disabled"
        self.entry_sheets_id.configure(state=sheets_state)
        self.entry_sheets_name.configure(state=sheets_state)
        self.entry_google_credentials.configure(state=sheets_state)
        self.btn_browse_google_credentials.configure(state=sheets_state)
        self.update_config_status()

    def toggle_admin_section(self):
        if not hasattr(self, "admin_section"):
            return
        if self.var_admin.get():
            self.admin_section.pack(fill="x", padx=16, pady=(0, 16))
        else:
            self.admin_section.pack_forget()
        self.update_config_status()

    def test_sheets_connection(self):
        if not self.chk_sheets.get():
            messagebox.showinfo("Google Sheets", "Activa Google Sheets para probar la conexion.")
            return

        sheets_id = self.entry_sheets_id.get().strip()
        sheets_name = self.entry_sheets_name.get().strip() or "Hoja 1"
        creds = self.entry_google_credentials.get().strip()

        if not sheets_id or not creds:
            messagebox.showwarning("Google Sheets", "Completa el ID y el archivo de credenciales.")
            return

        try:
            from storage.sheets_storage import verificar_conexion_sheets
            result = verificar_conexion_sheets(creds, sheets_id, sheets_name)
            if result.get("success"):
                messagebox.showinfo("Google Sheets", "Conexion exitosa.")
            else:
                messagebox.showwarning("Google Sheets", f"Error: {result.get('error', 'No se pudo conectar')}")
        except Exception as exc:
            messagebox.showwarning("Google Sheets", f"Error: {exc}")

    def setup_dashboard(self):
        self.dashboard_container = ctk.CTkScrollableFrame(self.tab_dashboard, fg_color="transparent")
        self.dashboard_container.pack(fill="both", expand=True, padx=16, pady=16)

        # Header con gradiente visual
        header = ctk.CTkFrame(self.dashboard_container, fg_color=COLOR_ACCENT, corner_radius=24)
        header.pack(fill="x", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        # Decoración abstracta
        header_decor = ctk.CTkFrame(header, fg_color=COLOR_ACCENT_DARK, corner_radius=200, width=280, height=180)
        header_decor.place(relx=0.92, rely=0.3, anchor="center")
        header_decor.lower()
        header_decor2 = ctk.CTkFrame(header, fg_color=COLOR_ACCENT_LIGHT, corner_radius=100, width=120, height=120)
        header_decor2.place(relx=0.78, rely=0.7, anchor="center")
        header_decor2.lower()

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.grid(row=0, column=0, padx=28, pady=24, sticky="w")
        ctk.CTkLabel(
            header_left,
            text="Sistema de Comprobantes",
            font=self.font_title,
            text_color="white"
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_left,
            text="Automatiza la carga de transferencias bancarias",
            font=self.font_subtitle,
            text_color="#C5E8E5"
        ).pack(anchor="w", pady=(6, 0))

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.grid(row=0, column=1, padx=28, pady=24, sticky="e")

        self.lbl_date = ctk.CTkLabel(
            header_right,
            text=datetime.now().strftime("%d %b %Y").upper(),
            font=self.font_tiny,
            text_color="#A8D8D5"
        )
        self.lbl_date.pack(anchor="e", pady=(0, 8))

        self.status_pill = ctk.CTkFrame(
            header_right,
            fg_color=COLOR_DANGER,
            corner_radius=999
        )
        self.status_pill.pack(anchor="e")
        self.status_pill_label = ctk.CTkLabel(
            self.status_pill,
            text="DETENIDO",
            font=self.font_small,
            text_color="white",
            padx=16,
            pady=8
        )
        self.status_pill_label.pack()

        if not self.license_active:
            blocked = self.create_card(self.dashboard_container, "Licencia bloqueada")
            blocked.pack(fill="x", padx=4, pady=12)
            ctk.CTkLabel(
                blocked,
                text=f"{self.license_msg}",
                font=self.font_body,
                text_color=COLOR_DANGER
            ).pack(anchor="w", padx=16, pady=(0, 16))
            return

        content = ctk.CTkFrame(self.dashboard_container, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=1, uniform="col")
        content.grid_columnconfigure(1, weight=1, uniform="col")
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        control_card = self.create_card(left, "Control del sistema")
        control_card.pack(fill="x", pady=(0, 14))

        self.lbl_status = ctk.CTkLabel(
            control_card,
            text="Detenido",
            font=self.font_section,
            text_color=COLOR_DANGER
        )
        self.lbl_status.pack(anchor="w", padx=20)

        self.config_hint_label = ctk.CTkLabel(
            control_card,
            text="",
            font=self.font_small,
            text_color=COLOR_WARNING
        )
        self.config_hint_label.pack(anchor="w", padx=20, pady=(4, 6))

        self.lbl_last_activity = ctk.CTkLabel(
            control_card,
            text="Última actividad: --",
            font=self.font_tiny,
            text_color=COLOR_MUTED
        )
        self.lbl_last_activity.pack(anchor="w", padx=20, pady=(0, 14))

        self.chips_frame = ctk.CTkFrame(control_card, fg_color="transparent")
        self.chips_frame.pack(fill="x", padx=20, pady=(0, 14))

        controls_row = ctk.CTkFrame(control_card, fg_color="transparent")
        controls_row.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_start = ctk.CTkButton(
            controls_row,
            text="Iniciar",
            command=self.start_system,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_DARK,
            corner_radius=14,
            height=44,
            font=self.font_body,
            width=100
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            controls_row,
            text="Detener",
            command=self.stop_system,
            fg_color=COLOR_BG_DARK,
            text_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_SOFT,
            corner_radius=14,
            height=44,
            font=self.font_body,
            state="disabled",
            width=100
        )
        self.btn_stop.pack(side="left", padx=(0, 10))

        self.btn_open_config = ctk.CTkButton(
            controls_row,
            text="Configuración",
            command=lambda: self.tabview.set("Configuración"),
            fg_color=COLOR_BG_DARK,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            height=40,
            font=self.font_body
        )
        self.btn_open_config.pack(side="left")

        # Botón Ayuda
        self.btn_help = ctk.CTkButton(
            controls_row,
            text="Ayuda",
            command=self.open_about_dialog,
            fg_color=COLOR_BG_DARK,
            text_color=COLOR_ACCENT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_ACCENT,
            corner_radius=12,
            height=40,
            font=self.font_body,
            width=80
        )
        self.btn_help.pack(side="left", padx=(10, 0))

        # Stats cards - diseño más impactante
        stats_card = self.create_card(left, "Resumen de Sesión")
        stats_card.pack(fill="x", pady=(0, 14))
        stats_row = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 10))
        stats_row.grid_columnconfigure(0, weight=1)
        stats_row.grid_columnconfigure(1, weight=1)

        stat_a = ctk.CTkFrame(stats_row, fg_color=COLOR_ACCENT_SOFT, corner_radius=16)
        stat_a.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
        self.lbl_processed = ctk.CTkLabel(
            stat_a,
            text="0",
            font=self.font_stat,
            text_color=COLOR_ACCENT
        )
        self.lbl_processed.pack(pady=(20, 4))
        ctk.CTkLabel(
            stat_a,
            text="Procesados",
            font=self.font_stat_label,
            text_color=COLOR_TEXT_SECONDARY
        ).pack(pady=(0, 16))

        stat_b = ctk.CTkFrame(stats_row, fg_color=COLOR_SUCCESS_SOFT, corner_radius=16)
        stat_b.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)
        self.lbl_total_amount = ctk.CTkLabel(
            stat_b,
            text="$0.00",
            font=self.font_stat,
            text_color=COLOR_SUCCESS
        )
        self.lbl_total_amount.pack(pady=(20, 4))
        ctk.CTkLabel(
            stat_b,
            text="Total Acumulado",
            font=self.font_stat_label,
            text_color=COLOR_TEXT_SECONDARY
        ).pack(pady=(0, 16))

        # Segunda fila de stats (Costo USD)
        stats_row2 = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_row2.pack(fill="x", padx=20, pady=(0, 20))
        stat_c = ctk.CTkFrame(stats_row2, fg_color=COLOR_BG_DARK, corner_radius=16)
        stat_c.pack(fill="x", pady=4)
        stat_c_inner = ctk.CTkFrame(stat_c, fg_color="transparent")
        stat_c_inner.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(
            stat_c_inner,
            text="Costo API:",
            font=self.font_body,
            text_color=COLOR_MUTED
        ).pack(side="left")
        self.lbl_cost_usd = ctk.CTkLabel(
            stat_c_inner,
            text="$0.00 USD",
            font=self.font_body,
            text_color=COLOR_TEXT
        )
        self.lbl_cost_usd.pack(side="right")

        # Pasos rápidos - más compacto
        steps_card = self.create_card(left, "Inicio rápido")
        steps_card.pack(fill="x")
        steps = [
            ("1", "Configura fuentes y destino"),
            ("2", "Inicia el sistema"),
            ("3", "Envía comprobantes")
        ]
        for num, text in steps:
            step_row = ctk.CTkFrame(steps_card, fg_color="transparent")
            step_row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(
                step_row,
                text=num,
                font=self.font_small,
                text_color="white",
                fg_color=COLOR_ACCENT,
                corner_radius=10,
                width=24,
                height=24
            ).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(
                step_row,
                text=text,
                font=self.font_body,
                text_color=COLOR_TEXT_SECONDARY
            ).pack(side="left")
        ctk.CTkFrame(steps_card, fg_color="transparent", height=16).pack()

        whatsapp_card = self.create_card(right, "WhatsApp")
        whatsapp_card.pack(fill="x", pady=(0, 14))

        wa_status_row = ctk.CTkFrame(whatsapp_card, fg_color="transparent")
        wa_status_row.pack(fill="x", padx=20, pady=(0, 10))
        self.wa_status_dot = ctk.CTkFrame(wa_status_row, fg_color=COLOR_WARNING, corner_radius=6, width=12, height=12)
        self.wa_status_dot.pack(side="left", padx=(0, 8))
        self.lbl_whatsapp_status = ctk.CTkLabel(
            wa_status_row,
            text="Desconectado",
            font=self.font_body,
            text_color=COLOR_TEXT_SECONDARY
        )
        self.lbl_whatsapp_status.pack(side="left")

        qr_holder = ctk.CTkFrame(whatsapp_card, fg_color=COLOR_BG_DARK, corner_radius=16)
        qr_holder.pack(padx=20, pady=(0, 14))
        self.lbl_qr = ctk.CTkLabel(qr_holder, text="Esperando QR...", text_color=COLOR_MUTED, font=self.font_small)
        self.lbl_qr.pack(padx=16, pady=16)

        ctk.CTkLabel(
            whatsapp_card,
            text="Escanea con WhatsApp para vincular",
            font=self.font_tiny,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=20, pady=(0, 10))

        self.btn_restart_qr = ctk.CTkButton(
            whatsapp_card,
            text="Reiniciar QR / Conexión",
            command=self.restart_bot,
            fg_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            height=32,
            font=self.font_small,
            state="disabled"
        )
        self.btn_restart_qr.pack(padx=20, pady=(0, 20), fill="x")

        # Tarjeta de Datos Acumulados con tabla
        accumulated_card = self.create_card(right, "Datos Acumulados")
        accumulated_card.pack(fill="x", pady=(0, 14))
        
        # Tabla de últimos comprobantes
        table_header = ctk.CTkFrame(accumulated_card, fg_color=COLOR_ACCENT, corner_radius=8)
        table_header.pack(fill="x", padx=20, pady=(0, 2))
        header_cols = ctk.CTkFrame(table_header, fg_color="transparent")
        header_cols.pack(fill="x", padx=8, pady=6)
        header_cols.grid_columnconfigure(0, weight=1)
        header_cols.grid_columnconfigure(1, weight=2)
        header_cols.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(header_cols, text="Fecha", font=self.font_small, text_color="white").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header_cols, text="Banco", font=self.font_small, text_color="white").grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(header_cols, text="Monto", font=self.font_small, text_color="white").grid(row=0, column=2, sticky="e")
        
        # Contenedor de filas de la tabla
        self.table_rows_frame = ctk.CTkFrame(accumulated_card, fg_color=COLOR_BG_DARK, corner_radius=8)
        self.table_rows_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.lbl_no_data = ctk.CTkLabel(
            self.table_rows_frame,
            text="Sin comprobantes aún",
            font=self.font_small,
            text_color=COLOR_MUTED
        )
        self.lbl_no_data.pack(pady=20)
        
        # Botones de exportación
        export_row = ctk.CTkFrame(accumulated_card, fg_color="transparent")
        export_row.pack(fill="x", padx=20, pady=(0, 10))
        self.btn_export_excel = ctk.CTkButton(
            export_row,
            text="📤 Exportar a Excel",
            command=self.export_accumulated_data,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_DARK,
            corner_radius=12,
            height=38,
            font=self.font_body
        )
        self.btn_export_excel.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.btn_reset_session = ctk.CTkButton(
            export_row,
            text="🔄 Reiniciar",
            command=self.reset_session,
            fg_color=COLOR_WARNING_SOFT,
            text_color=COLOR_WARNING,
            hover_color=COLOR_DANGER_SOFT,
            corner_radius=12,
            height=38,
            font=self.font_body,
            width=100
        )
        self.btn_reset_session.pack(side="left")
        
        # Info de última exportación
        self.lbl_last_export = ctk.CTkLabel(
            accumulated_card,
            text="",
            font=self.font_tiny,
            text_color=COLOR_MUTED
        )
        self.lbl_last_export.pack(anchor="w", padx=20, pady=(0, 16))

        # Tarjeta de accesos rápidos a Excel
        excel_card = self.create_card(right, "Archivo Excel")
        excel_card.pack(fill="x")
        self.lbl_excel_path = ctk.CTkLabel(
            excel_card,
            text="",
            font=self.font_tiny,
            text_color=COLOR_MUTED
        )
        self.lbl_excel_path.pack(anchor="w", padx=20, pady=(0, 10))

        actions_row = ctk.CTkFrame(excel_card, fg_color="transparent")
        actions_row.pack(fill="x", padx=20, pady=(0, 20))
        self.btn_open_excel = ctk.CTkButton(
            actions_row,
            text="Abrir Excel",
            command=self.open_excel_file,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_DARK,
            corner_radius=14,
            height=42,
            font=self.font_body,
            width=110
        )
        self.btn_open_excel.pack(side="left", padx=(0, 10))

        self.btn_open_data = ctk.CTkButton(
            actions_row,
            text="Carpeta",
            command=self.open_data_folder,
            fg_color=COLOR_BG_DARK,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG,
            border_width=0,
            corner_radius=14,
            height=42,
            font=self.font_body,
            width=100
        )
        self.btn_open_data.pack(side="left")
        
        # Inicializar la vista del acumulador
        self.refresh_accumulator_display()

    def setup_config(self):
        self.scroll_config = ctk.CTkScrollableFrame(self.tab_config, fg_color="transparent")
        self.scroll_config.pack(fill="both", expand=True, padx=16, pady=16)

        intro = ctk.CTkFrame(self.scroll_config, fg_color=COLOR_ACCENT, corner_radius=20)
        intro.pack(fill="x", pady=(0, 16))
        intro_text = "Configuración inicial" if self.first_run else "Configuración"
        ctk.CTkLabel(intro, text=intro_text, font=self.font_section, text_color="white").pack(
            anchor="w", padx=20, pady=(16, 4)
        )
        ctk.CTkLabel(
            intro,
            text="Completa los datos y guarda la configuración.",
            font=self.font_small,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 12))

        fuentes = self.create_card(self.scroll_config, "Fuentes de datos")
        fuentes.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            fuentes,
            text="Selecciona al menos una fuente de comprobantes.",
            font=self.font_small,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.chk_whatsapp = ctk.CTkCheckBox(
            fuentes,
            text="Recibir por WhatsApp",
            command=self.update_config_status
        )
        self.chk_whatsapp.pack(anchor="w", padx=16, pady=6)
        if self.config.get('fuentes', {}).get('whatsapp_enabled'):
            self.chk_whatsapp.select()

        self.chk_folder = ctk.CTkCheckBox(
            fuentes,
            text="Leer desde carpeta local",
            command=self.toggle_folder_fields
        )
        self.chk_folder.pack(anchor="w", padx=16, pady=6)
        if self.config.get('fuentes', {}).get('carpeta_enabled'):
            self.chk_folder.select()

        folder_row = ctk.CTkFrame(fuentes, fg_color="transparent")
        folder_row.pack(fill="x", padx=16, pady=(6, 16))
        self.entry_folder = ctk.CTkEntry(folder_row, placeholder_text="Ruta carpeta", width=420)
        self.entry_folder.pack(side="left", fill="x", expand=True)
        self.entry_folder.insert(0, self.config.get('fuentes', {}).get('carpeta_ruta', ''))
        self.entry_folder.bind("<KeyRelease>", lambda _e: self.update_config_status())
        self.btn_browse_folder = ctk.CTkButton(
            folder_row,
            text="Buscar",
            command=self.browse_folder,
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            width=90,
            height=32
        )
        self.btn_browse_folder.pack(side="left", padx=(8, 0))

        almacenamiento = self.create_card(self.scroll_config, "Almacenamiento")
        almacenamiento.pack(fill="x", pady=(0, 12))

        self.chk_excel = ctk.CTkCheckBox(
            almacenamiento,
            text="Guardar en Excel local",
            command=self.toggle_storage_fields
        )
        self.chk_excel.pack(anchor="w", padx=16, pady=6)
        if self.config.get('storage', {}).get('excel_enabled'):
            self.chk_excel.select()

        excel_row = ctk.CTkFrame(almacenamiento, fg_color="transparent")
        excel_row.pack(fill="x", padx=16, pady=(6, 12))
        self.entry_excel = ctk.CTkEntry(excel_row, placeholder_text="Nombre archivo Excel", width=420)
        self.entry_excel.pack(side="left", fill="x", expand=True)
        self.entry_excel.insert(0, self.config.get('storage', {}).get('excel_path', 'transferencias.xlsx'))
        self.entry_excel.bind("<KeyRelease>", lambda _e: self.update_config_status())
        self.btn_browse_excel = ctk.CTkButton(
            excel_row,
            text="Buscar",
            command=self.browse_excel_file,
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            width=90,
            height=32
        )
        self.btn_browse_excel.pack(side="left", padx=(8, 0))

        self.chk_sheets = ctk.CTkCheckBox(
            almacenamiento,
            text="Guardar en Google Sheets",
            command=self.toggle_storage_fields
        )
        self.chk_sheets.pack(anchor="w", padx=16, pady=6)
        if self.config.get('storage', {}).get('sheets_enabled'):
            self.chk_sheets.select()

        self.entry_sheets_id = ctk.CTkEntry(almacenamiento, placeholder_text="ID de Google Sheets (Spreadsheet ID)", width=420)
        self.entry_sheets_id.pack(anchor="w", padx=16, pady=4)
        self.entry_sheets_id.insert(0, self.config.get('storage', {}).get('sheets_id', ''))
        self.entry_sheets_id.bind("<KeyRelease>", lambda _e: self.update_config_status())

        ctk.CTkLabel(
            almacenamiento,
            text="(Se encuentra en la URL de Google Sheets)",
            font=self.font_small,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.entry_sheets_name = ctk.CTkEntry(almacenamiento, placeholder_text="Nombre de la hoja (pestaña)", width=420)
        self.entry_sheets_name.pack(anchor="w", padx=16, pady=(0, 12))
        self.entry_sheets_name.insert(0, self.config.get('storage', {}).get('sheets_name', 'Hoja 1'))
        self.entry_sheets_name.bind("<KeyRelease>", lambda _e: self.update_config_status())

        credenciales = self.create_card(self.scroll_config, "Credenciales")
        credenciales.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            credenciales,
            text="Solo necesitas Google Sheets si vas a usarlo.",
            font=self.font_small,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 10))

        status_row = ctk.CTkFrame(credenciales, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 8))
        status_row.grid_columnconfigure(0, weight=1)
        status_row.grid_columnconfigure(1, weight=0)

        self.lbl_openai_status = ctk.CTkLabel(
            status_row,
            text="",
            font=self.font_small,
            text_color=COLOR_MUTED
        )
        self.lbl_openai_status.grid(row=0, column=0, sticky="w")

        self.btn_test_sheets = ctk.CTkButton(
            status_row,
            text="Probar Sheets",
            command=self.test_sheets_connection,
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            height=28
        )
        self.btn_test_sheets.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            credenciales,
            text="Archivo JSON de credenciales (cuenta de servicio)",
            font=self.font_small,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 6))

        google_row = ctk.CTkFrame(credenciales, fg_color="transparent")
        google_row.pack(fill="x", padx=16, pady=(0, 16))
        self.entry_google_credentials = ctk.CTkEntry(
            google_row,
            placeholder_text="Selecciona el archivo JSON",
            width=420
        )
        self.entry_google_credentials.pack(side="left", fill="x", expand=True)
        self.entry_google_credentials.insert(0, self.config.get('google_credentials_path', ''))
        self.entry_google_credentials.bind("<KeyRelease>", lambda _e: self.update_config_status())
        self.btn_browse_google_credentials = ctk.CTkButton(
            google_row,
            text="Buscar",
            command=self.browse_google_credentials,
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            width=90,
            height=32
        )
        self.btn_browse_google_credentials.pack(side="left", padx=(8, 0))

        self.var_admin = ctk.BooleanVar(value=False)
        self.switch_admin = ctk.CTkSwitch(
            credenciales,
            text="Mostrar opciones de administrador",
            variable=self.var_admin,
            command=self.toggle_admin_section
        )
        self.switch_admin.pack(anchor="w", padx=16, pady=(0, 12))

        self.admin_section = ctk.CTkFrame(credenciales, fg_color=COLOR_BG, corner_radius=12)

        ctk.CTkLabel(
            self.admin_section,
            text="Clave OpenAI (solo soporte tecnico)",
            font=self.font_small,
            text_color=COLOR_MUTED
        ).pack(anchor="w", padx=12, pady=(10, 6))

        # Campo de API key - siempre muestra asteriscos, nunca se puede ver el valor real
        self.entry_openai_key = ctk.CTkEntry(
            self.admin_section,
            placeholder_text="Pegar API Key aqui",
            width=420,
            show="*"  # Siempre muestra asteriscos
        )
        self.entry_openai_key.pack(anchor="w", padx=12, pady=(0, 10))
        self.entry_openai_key.insert(0, self.config.get('openai_api_key', ''))
        self.entry_openai_key.bind("<KeyRelease>", lambda _e: self.update_config_status())

        actions = ctk.CTkFrame(self.scroll_config, fg_color="transparent")
        actions.pack(fill="x", pady=(8, 20))
        self.btn_save = ctk.CTkButton(
            actions,
            text="Guardar configuracion",
            command=self.save_config,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_DARK,
            corner_radius=12,
            height=40,
            font=self.font_body
        )
        self.btn_save.pack(side="left", padx=(0, 8))

        self.btn_to_dashboard = ctk.CTkButton(
            actions,
            text="Volver al Dashboard",
            command=lambda: self.tabview.set("Dashboard"),
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            height=40,
            font=self.font_body
        )
        self.btn_to_dashboard.pack(side="left", padx=(0, 8))

        self.btn_open_data_config = ctk.CTkButton(
            actions,
            text="Carpeta de datos",
            command=self.open_data_folder,
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            height=40,
            font=self.font_body
        )
        self.btn_open_data_config.pack(side="left")

        self.toggle_folder_fields()
        self.toggle_storage_fields()
        self.toggle_admin_section()

        # Habilitar scroll con rueda del mouse
        self.after(100, lambda: self.bind_mousewheel_to_scrollable(self.scroll_config))

    def setup_logs(self):
        self.txt_logs = ctk.CTkTextbox(
            self.tab_logs,
            width=700,
            height=500,
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.txt_logs.pack(padx=12, pady=12, fill="both", expand=True)
        self.txt_logs.configure(state="disabled")

    def open_about_dialog(self):
        AboutDialog(self)

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"[{timestamp}] {message}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def refresh_accumulator_display(self):
        """Actualiza la tabla de comprobantes acumulados y los contadores."""
        try:
            accumulator = get_accumulator()
            
            # Actualizar contadores
            count = accumulator.get_count()
            total = accumulator.get_total_amount()
            
            if hasattr(self, 'lbl_processed'):
                self.lbl_processed.configure(text=str(count))
            
            if hasattr(self, 'lbl_total_amount'):
                # Formatear monto con separadores de miles
                formatted_total = f"${total:,.2f}"
                self.lbl_total_amount.configure(text=formatted_total)
            
            # Actualizar tabla de comprobantes
            if hasattr(self, 'table_rows_frame'):
                # Limpiar filas existentes
                for widget in self.table_rows_frame.winfo_children():
                    widget.destroy()
                
                entries = accumulator.get_recent_entries(8)
                
                if not entries:
                    self.lbl_no_data = ctk.CTkLabel(
                        self.table_rows_frame,
                        text="Sin comprobantes aún",
                        font=self.font_small,
                        text_color=COLOR_MUTED
                    )
                    self.lbl_no_data.pack(pady=20)
                else:
                    for i, entry in enumerate(entries):
                        row_bg = COLOR_CARD if i % 2 == 0 else COLOR_BG_DARK
                        row_frame = ctk.CTkFrame(self.table_rows_frame, fg_color=row_bg, corner_radius=0)
                        row_frame.pack(fill="x")
                        
                        row_inner = ctk.CTkFrame(row_frame, fg_color="transparent")
                        row_inner.pack(fill="x", padx=8, pady=4)
                        row_inner.grid_columnconfigure(0, weight=1)
                        row_inner.grid_columnconfigure(1, weight=2)
                        row_inner.grid_columnconfigure(2, weight=1)
                        
                        # Fecha formateada
                        try:
                            ts = entry.get('timestamp', '')
                            if ts:
                                dt = datetime.fromisoformat(ts)
                                fecha_str = dt.strftime("%d/%m %H:%M")
                            else:
                                fecha_str = "--"
                        except:
                            fecha_str = "--"
                        
                        ctk.CTkLabel(
                            row_inner,
                            text=fecha_str,
                            font=self.font_tiny,
                            text_color=COLOR_TEXT_SECONDARY
                        ).grid(row=0, column=0, sticky="w")
                        
                        banco = entry.get('banco_origen', 'Sin banco')[:15]
                        ctk.CTkLabel(
                            row_inner,
                            text=banco,
                            font=self.font_tiny,
                            text_color=COLOR_TEXT
                        ).grid(row=0, column=1, sticky="w")
                        
                        monto = entry.get('monto', 0)
                        ctk.CTkLabel(
                            row_inner,
                            text=f"${monto:,.2f}",
                            font=self.font_tiny,
                            text_color=COLOR_SUCCESS
                        ).grid(row=0, column=2, sticky="e")
            
            # Actualizar info de última exportación
            if hasattr(self, 'lbl_last_export'):
                history = accumulator.get_export_history(1)
                if history:
                    last = history[0]
                    try:
                        dt = datetime.fromisoformat(last.get('timestamp', ''))
                        fecha_str = dt.strftime("%d/%m/%Y %H:%M")
                        self.lbl_last_export.configure(text=f"Última exportación: {fecha_str}")
                    except:
                        self.lbl_last_export.configure(text="")
                else:
                    self.lbl_last_export.configure(text="")
                    
        except Exception as e:
            logging.error(f"Error actualizando acumulador: {e}")

    def export_accumulated_data(self):
        """Exporta los datos acumulados a un archivo Excel."""
        try:
            accumulator = get_accumulator()
            
            if accumulator.get_count() == 0:
                messagebox.showinfo(
                    "Exportar a Excel",
                    "No hay comprobantes para exportar."
                )
                return
            
            result = accumulator.export_to_excel()
            
            if result.get('success'):
                filepath = result.get('filepath', '')
                count = result.get('count', 0)
                total = result.get('total_amount', 0)
                
                self.log_message(f"Exportados {count} comprobantes (${total:,.2f}) a Excel")
                self.refresh_accumulator_display()
                
                # Preguntar si abrir el archivo
                if messagebox.askyesno(
                    "Exportación Exitosa",
                    f"Se exportaron {count} comprobantes.\n"
                    f"Total: ${total:,.2f}\n\n"
                    f"¿Desea abrir el archivo?"
                ):
                    if sys.platform == "win32":
                        os.startfile(filepath)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", filepath])
                    else:
                        subprocess.run(["xdg-open", filepath])
            else:
                error = result.get('error', 'Error desconocido')
                messagebox.showerror("Error", f"Error al exportar: {error}")
                
        except Exception as e:
            logging.error(f"Error en export_accumulated_data: {e}")
            messagebox.showerror("Error", f"Error al exportar: {e}")

    def reset_session(self):
        """Reinicia la sesión, exportando primero los datos actuales."""
        try:
            accumulator = get_accumulator()
            count = accumulator.get_count()
            
            if count == 0:
                messagebox.showinfo(
                    "Reiniciar Sesión",
                    "No hay datos para reiniciar."
                )
                return
            
            total = accumulator.get_total_amount()
            
            # Confirmar con el usuario
            if not messagebox.askyesno(
                "Reiniciar Sesión",
                f"Hay {count} comprobantes acumulados (${total:,.2f}).\n\n"
                f"Se exportarán a Excel antes de reiniciar.\n\n"
                f"¿Desea continuar?"
            ):
                return
            
            result = accumulator.reset(export_first=True)
            
            if result.get('success'):
                export_result = result.get('export_result', {})
                filepath = export_result.get('filepath', '') if export_result else ''
                prev_count = result.get('previous_count', 0)
                prev_total = result.get('previous_total', 0)
                
                self.log_message(f"Sesión reiniciada: {prev_count} comprobantes (${prev_total:,.2f}) exportados")
                self.refresh_accumulator_display()
                
                messagebox.showinfo(
                    "Sesión Reiniciada",
                    f"Se exportaron {prev_count} comprobantes.\n"
                    f"Total: ${prev_total:,.2f}\n\n"
                    f"El contador ha sido reiniciado."
                )
            else:
                error = result.get('error', 'Error desconocido')
                messagebox.showerror("Error", f"Error al reiniciar: {error}")
                
        except Exception as e:
            logging.error(f"Error en reset_session: {e}")
            messagebox.showerror("Error", f"Error al reiniciar: {e}")

    def start_system(self):
        if self.is_running: return
        issues = self.get_config_issues()
        if issues:
            messagebox.showwarning(
                "Configuración incompleta",
                "Completa la configuración antes de iniciar:\n- " + "\n- ".join(issues)
            )
            self.tabview.set("Configuración")
            return

        self.save_config() # Guardar antes de iniciar
        self.is_running = True
        
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        self.set_system_status("Iniciando", COLOR_WARNING)
        self.log_message("Iniciando sistema...")
        
        # Iniciar API Python (run.py o Api.exe)
        # Usamos subprocess para ejecutar en background
        try:
            cmd = self.get_api_command()
            api_env = os.environ.copy()
            api_env["APP_DATA_DIR"] = get_app_data_dir()
            openai_key = self.get_openai_key()
            google_creds_raw = self.entry_google_credentials.get().strip()
            google_creds = resolve_appdata_path(google_creds_raw) if google_creds_raw else ""
            if openai_key:
                api_env["OPENAI_API_KEY"] = openai_key
            if google_creds:
                api_env["GOOGLE_CREDENTIALS_PATH"] = google_creds

            poppler_path = self.get_poppler_path()
            if poppler_path:
                api_env["POPPLER_PATH"] = poppler_path
            # Flags para ocultar ventana en Windows
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = 0x08000000  # CREATE_NO_WINDOW

            self.log_message(f"🚀 Iniciando API con: {' '.join(cmd)}")
            
            self.process_api = subprocess.Popen(cmd, 
                                              stdout=subprocess.PIPE, 
                                              stderr=subprocess.PIPE,
                                              text=True,
                                              encoding='utf-8',
                                              bufsize=1,
                                              cwd=get_resource_dir(),
                                              env=api_env,
                                              creationflags=creation_flags)
            
            # Thread para leer output de API
            threading.Thread(target=self.read_process_output, args=(self.process_api, "API"), daemon=True).start()
            threading.Thread(target=self.read_process_error_output, args=(self.process_api, "API"), daemon=True).start()
            
            # NUEVO: Esperar un poco y verificar que el proceso siga vivo
            time.sleep(2)
            if self.process_api.poll() is not None:
                # El proceso murió, intentar leer el error
                exit_code = self.process_api.returncode
                stderr_output = ""
                try:
                    stderr_output = self.process_api.stderr.read()
                except:
                    pass
                error_msg = f"❌ API crasheó al iniciar (exit code: {exit_code})"
                if stderr_output:
                    error_msg += f"\nError: {stderr_output[:500]}"
                self.log_message(error_msg)
                messagebox.showerror("Error de API", error_msg)
                self.stop_system()
                return
            
            self.log_message("✅ Motor de IA iniciado correctamente.")
            self.set_system_status("Ejecutando", COLOR_SUCCESS)
            
            # Iniciar Bot WhatsApp si está habilitado
            if self.chk_whatsapp.get():
                self._start_bot_process()
                if hasattr(self, "btn_restart_qr"):
                    self.btn_restart_qr.configure(state="normal")
                
        except Exception as e:
            self.log_message(f"❌ Error al iniciar: {e}")
            messagebox.showerror("Error Crítico", f"No se pudo iniciar el sistema:\n{e}")
            self.stop_system()

    def _start_bot_process(self):
        self.log_message("Iniciando bot de WhatsApp...")
        bot_dir = os.path.join(get_resource_dir(), "bot")
        bot_entry = os.path.join(bot_dir, "index.js")
        bot_env = os.environ.copy()
        bot_env["API_URL"] = "http://localhost:8000"
        bot_env["WWEBJS_AUTH_DIR"] = os.path.join(get_app_data_dir(), "wwebjs_auth")
        
        # Ensure QR directory exists
        qr_dir = os.path.dirname(self.qr_path)
        if not os.path.exists(qr_dir):
            os.makedirs(qr_dir, exist_ok=True)
        bot_env["QR_PATH"] = self.qr_path
        self.log_message(f"📸 QR se guardará en: {self.qr_path}")

        chromium_path = self.get_chromium_path()
        if chromium_path:
            self.log_message(f"🖥️ Usando Chromium en: {chromium_path}")
            bot_env["CHROMIUM_PATH"] = chromium_path
        else:
            self.log_message("⚠️ No se encontró Chromium embebido, usando el del sistema")

        node_path = self.get_node_path()
        bot_cmd = [node_path, bot_entry]
        
        # Flags para ocultar ventana en Windows
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = 0x08000000  # CREATE_NO_WINDOW
            
        self.process_bot = subprocess.Popen(bot_cmd,
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE,
                                          text=True,
                                          encoding='utf-8',
                                          cwd=bot_dir,
                                          bufsize=1,
                                          env=bot_env)
        threading.Thread(target=self.read_process_output, args=(self.process_bot, "BOT"), daemon=True).start()
        threading.Thread(target=self.read_process_error_output, args=(self.process_bot, "BOT"), daemon=True).start()
                


    def restart_bot(self):
        if not self.is_running or not self.chk_whatsapp.get():
            return
            
        self.log_message("♻️ Reiniciando servicio de WhatsApp...")
        self.btn_restart_qr.configure(state="disabled")
        
        # Kill existing
        if self.process_bot:
            self.kill_process_tree(self.process_bot.pid)
            self.process_bot = None
            
        # Clear QR
        if os.path.exists(self.qr_path):
             try:
                os.remove(self.qr_path)
             except:
                pass
        
        # CLEAR SESSION (Hard Reset)
        try:
            # Esperar a que el proceso libere los archivos
            import time
            time.sleep(2.0)
            
            auth_dir = os.path.join(get_app_data_dir(), "wwebjs_auth")
            if os.path.exists(auth_dir):
                self.log_message(f"🧹 Limpiando sesión anterior en: {auth_dir}")
                import shutil
                shutil.rmtree(auth_dir)
        except Exception as e:
            self.log_message(f"⚠️ No se pudo limpiar sesión: {e}")

        self.update_qr_image()
        self.update_whatsapp_status("Reiniciando...", COLOR_WARNING)

        # Start new
        try:
            self._start_bot_process()
        except Exception as e:
            self.log_message(f"❌ Error al reiniciar bot: {e}")
            
        # Re-enable button after a short delay
        self.after(5000, lambda: self.btn_restart_qr.configure(state="normal"))

    def stop_system(self):
        self.is_running = False
        self.log_message("⚠️ Deteniendo sistema...")
        
        if self.process_api:
            self.kill_process_tree(self.process_api.pid)
            self.process_api = None
            
        if self.process_bot:
            self.kill_process_tree(self.process_bot.pid)
            self.process_bot = None

        self.update_whatsapp_status("Desconectado", COLOR_DANGER)
        if hasattr(self, "btn_restart_qr"):
            self.btn_restart_qr.configure(state="disabled")
            
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.set_system_status("Detenido", COLOR_DANGER)
        self.log_message("Sistema detenido.")
        self.update_config_status()

    def get_api_command(self):
        if getattr(sys, "frozen", False):
            api_exe = os.path.join(get_resource_dir(), "Api.exe")
            if os.path.exists(api_exe):
                return [api_exe]
        return [sys.executable, "run.py"]

    def get_node_path(self):
        # 1. Check embedded Node (frozen)
        if getattr(sys, "frozen", False):
            node_exe = os.path.join(get_resource_dir(), "node", "node.exe")
            if os.path.exists(node_exe):
                return node_exe
        
        # 2. Check if node is in PATH
        import shutil
        node_in_path = shutil.which("node")
        if node_in_path:
            return node_in_path
        
        # 3. Check common Node.js installation paths on Windows
        common_paths = [
            r"C:\Program Files\nodejs\node.exe",
            r"C:\Program Files (x86)\nodejs\node.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs\node.exe"),
            os.path.expandvars(r"%APPDATA%\npm\node.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Fallback (will fail if not in PATH)
        return "node"

    def get_chromium_path(self):
        # 1. Check embedded Chromium (frozen/dev)
        if getattr(sys, "frozen", False):
            chrome_exe = os.path.join(get_resource_dir(), "chromium", "chrome.exe")
            if os.path.exists(chrome_exe):
                return chrome_exe
        
        # 2. Check System Chrome/Edge (common paths)
        common_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        return ""

    def get_poppler_path(self):
        # 1. Check embedded Poppler (frozen)
        if getattr(sys, "frozen", False):
            poppler_root = os.path.join(get_resource_dir(), "poppler")
            poppler_bin = os.path.join(poppler_root, "bin")
            poppler_alt_bin = os.path.join(poppler_root, "Library", "bin")
            if os.path.exists(poppler_bin):
                return poppler_bin
            if os.path.exists(poppler_alt_bin):
                return poppler_alt_bin
        
        # 2. Check LocalAppData (installed by user)
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            poppler_local = os.path.join(local_appdata, "poppler")
            if os.path.exists(poppler_local):
                # Search for pdftoppm.exe recursively
                for root, dirs, files in os.walk(poppler_local):
                    if "pdftoppm.exe" in files:
                        return root
        
        # 3. Check common installation paths
        common_paths = [
            r"C:\poppler\Library\bin",
            r"C:\poppler\bin",
            r"C:\Program Files\poppler\Library\bin",
            r"C:\Program Files\poppler\bin",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return ""

    def kill_process_tree(self, pid):
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
            else:
                parent = psutil.Process(pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
        except:
            pass

    def read_process_output(self, process, prefix):
        """Lee la salida de los subprocesos y la muestra en logs."""
        import re
        while process.poll() is None and self.is_running:
            line = process.stdout.readline()
            if line:
                # Mostrar todos los logs del BOT, filtrar solo los de API
                if prefix == "BOT" or "INFO" in line or "Error" in line or "✅" in line:
                    self.log_message(f"{prefix}: {line.strip()}")

                if prefix == "BOT":
                    # Parsear [QR_DATA]...[/QR_DATA] para generar QR desde Python
                    qr_match = re.search(r'\[QR_DATA\](.*?)\[/QR_DATA\]', line)
                    if qr_match:
                        qr_data = qr_match.group(1)
                        self.generate_qr_from_python(qr_data)
                    
                    lowered = line.lower()
                    if "escanear" in lowered or "[qr_data]" in lowered:
                        self.update_whatsapp_status("Esperando QR", COLOR_WARNING)
                    elif "[connected]" in lowered or "bot conectado y listo" in lowered:
                        self.update_whatsapp_status("Conectado", COLOR_SUCCESS)
                        # Borrar QR cuando conecta
                        if os.path.exists(self.qr_path):
                            try:
                                os.remove(self.qr_path)
                            except:
                                pass
                    elif "auth_failure" in lowered or "desconectado" in lowered:
                        self.update_whatsapp_status("Desconectado", COLOR_DANGER)
    
    def generate_qr_from_python(self, qr_data):
        """Genera el QR localmente usando Python en lugar de depender de Node."""
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(self.qr_path)
            self.log_message(f"✅ QR generado localmente: {self.qr_path}")
        except Exception as e:
            self.log_message(f"❌ Error generando QR: {e}")

    def read_process_error_output(self, process, prefix):
        """Lee stderr de los subprocesos y la muestra en logs."""
        while process.poll() is None and self.is_running:
            line = process.stderr.readline()
            if line:
                self.log_message(f"{prefix} ERR: {line.strip()}")

    def update_whatsapp_status(self, text, color):
        if not hasattr(self, "lbl_whatsapp_status"):
            return
        self.after(0, lambda: self.lbl_whatsapp_status.configure(text=text, text_color=color))

    def refresh_qr_loop(self):
        self.update_qr_image()
        self.after(2000, self.refresh_qr_loop)

    def update_qr_image(self):
        if not hasattr(self, "lbl_qr"):
            return
        try:
            if os.path.exists(self.qr_path):
                mtime = os.path.getmtime(self.qr_path)
                if mtime != self.qr_last_mtime:
                    # Keep strong reference to PIL image
                    self._pil_qr_image = Image.open(self.qr_path)
                    self._pil_qr_image = self._pil_qr_image.resize((240, 240))
                    # Keep strong reference to CTkImage
                    self.qr_image = ctk.CTkImage(
                        light_image=self._pil_qr_image, 
                        dark_image=self._pil_qr_image, 
                        size=(240, 240)
                    )
                    self.lbl_qr.configure(image=self.qr_image, text="")
                    self.qr_last_mtime = mtime
                    self.update_whatsapp_status("Esperando escaneo", COLOR_WARNING)
            else:
                if hasattr(self, "qr_image"):
                    self.qr_image = None
                    self._pil_qr_image = None
                self.lbl_qr.configure(image=None, text="Esperando QR...", text_color=COLOR_MUTED)
        except Exception as e:
            # Silently ignore image errors to prevent UI crash
            pass
        
    def update_stats_loop(self):
        """Actualiza las estadísticas de costos cada 5 segundos."""
        while True:
            if self.is_running:
                try:
                    if not hasattr(self, "lbl_processed"):
                        time.sleep(5)
                        continue
                    
                    # Actualizar costo desde el log de billing
                    try:
                        with open(get_usage_log_path(), 'r') as f:
                            data = json.load(f)
                            resumen = data.get('resumen', {})
                            self.lbl_cost_usd.configure(text=f"${resumen.get('costo_mostrado_usd', 0):.4f} USD")
                    except:
                        pass
                    
                    # Actualizar contador y monto desde el acumulador de sesión (reiniciable)
                    try:
                        accumulator = get_accumulator()
                        count = accumulator.get_count()
                        total = accumulator.get_total_amount()
                        
                        self.lbl_processed.configure(text=f"{count}")
                        self.lbl_total_amount.configure(text=f"${total:,.2f}")
                        
                        # Refrescar la tabla de datos acumulados (usar after para thread-safety)
                        self.after(0, self.refresh_accumulator_display)
                    except Exception as e:
                        logging.debug(f"Error actualizando acumulador: {e}")
                        
                except Exception as e:
                    logging.debug(f"Error en update_stats_loop: {e}")
            time.sleep(5)

    def open_excel_file(self):
        path = resolve_appdata_path(
            self.config.get('storage', {}).get('excel_path', 'transferencias.xlsx'),
            fallback_name="transferencias.xlsx"
        )
        # Asegurar que tenga extensión .xlsx
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        
        if os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            self.log_message(f"❌ No se encontró el archivo: {path}")

    def on_closing(self):
        if self.is_running:
            self.stop_system()
        self.destroy()

if __name__ == "__main__":
    app = SystemLauncher()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
