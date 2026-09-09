import sys
import os
import shutil
import json
from datetime import datetime
import qdarktheme
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QTreeView, 
                             QInputDialog, QFileDialog, QMessageBox, QLabel, QSplitter,
                             QStackedWidget, QAbstractItemView, QFrame, QFormLayout, 
                             QLineEdit, QTextEdit, QDialog, QDialogButtonBox, QMenu, 
                             QScrollArea, QComboBox, QCalendarWidget, QGridLayout, QCheckBox, 
                             QListWidgetItem, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QUrl, QTimer, QTime, QDate, pyqtSignal
from PyQt6.QtGui import QFileSystemModel, QDesktopServices, QAction, QTextCharFormat, QColor, QShortcut, QKeySequence
import database

class DoubleClickLabel(QLabel):
    doubleClicked = pyqtSignal()
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

class SelectableLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(str(text), parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)
        self.setWordWrap(True)

    def show_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("📋 Copy", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.selectedText() if self.selectedText() else self.text()))
        menu.addAction(copy_action)
        menu.exec(self.mapToGlobal(pos))

class ClickableFrame(QFrame):
    clicked = pyqtSignal(str)
    def __init__(self, project_name, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_name)
        super().mousePressEvent(event)

class DateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor

    def setEditorData(self, editor, index):
        date_str = index.model().data(index, Qt.ItemDataRole.EditRole)
        if date_str:
            editor.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        else:
            editor.setDate(QDate.currentDate())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.date().toString("yyyy-MM-dd"), Qt.ItemDataRole.EditRole)

class QuickLinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔗 Add Quick Link")
        self.setMinimumWidth(450)
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        layout.addRow("<b>Link Name:</b>", self.name_input)
        
        self.path_input = QLineEdit()
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.path_input)
        
        btn_file = QPushButton("📄 File")
        btn_file.clicked.connect(self.browse_file)
        btn_dir = QPushButton("📁 Folder")
        btn_dir.clicked.connect(self.browse_dir)
        
        path_layout.addWidget(btn_file)
        path_layout.addWidget(btn_dir)
        layout.addRow("<b>URL / Path:</b>", path_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path: self.path_input.setText(path)

    def browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path: self.path_input.setText(path)

    def get_data(self):
        return self.name_input.text().strip(), self.path_input.text().strip()

class IterationDialog(QDialog):
    def __init__(self, existing_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 Iteration Details")
        self.setMinimumWidth(400)
        self.layout = QFormLayout(self)
        
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Modeling", "Meshing", "FEA", "Post Processing"])
        
        self.iter_input = QLineEdit()
        self.prev_input = QLineEdit()
        
        self.change_input = QTextEdit()
        self.change_input.setMaximumHeight(80)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["WIP", "Under review", "Running", "Completed", "Archived"])
        
        self.result_combo = QComboBox()
        self.result_combo.addItems(["Not Run", "Pass", "Fail"])
        
        self.layout.addRow("Category", self.cat_combo)
        self.layout.addRow("Iteration count", self.iter_input)
        self.layout.addRow("Previous version", self.prev_input)
        self.layout.addRow("Current change", self.change_input)
        self.layout.addRow("Status", self.status_combo)
        self.layout.addRow("Result", self.result_combo)
        
        if existing_data:
            self.cat_combo.setCurrentText(existing_data.get("Category", "Modeling"))
            self.iter_input.setText(existing_data.get("Iteration count", ""))
            self.prev_input.setText(existing_data.get("Previous version", ""))
            self.change_input.setPlainText(existing_data.get("Current change", ""))
            self.status_combo.setCurrentText(existing_data.get("Status", "WIP"))
            self.result_combo.setCurrentText(existing_data.get("Result", "Not Run"))
            
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        self.layout.addRow(self.btn_box)
        
    def get_data(self):
        return {
            "Category": self.cat_combo.currentText(),
            "Iteration count": self.iter_input.text().strip(),
            "Previous version": self.prev_input.text().strip(),
            "Current change": self.change_input.toPlainText().strip(),
            "Status": self.status_combo.currentText(),
            "Result": self.result_combo.currentText()
        }

class TimelineDialog(QDialog):
    def __init__(self, project_name, timeline_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"🕒 Timeline: {project_name}")
        self.resize(750, 500)
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Date", "Remarks"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 150)
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.AnyKeyPressed | 
                                   QAbstractItemView.EditTrigger.SelectedClicked | 
                                   QAbstractItemView.EditTrigger.EditKeyPressed)
        self.table.cellDoubleClicked.connect(self.handle_double_click)

        layout.addWidget(self.table)

        for row_data in timeline_data:
            self.add_row(row_data.get("Date", ""), row_data.get("Remarks", ""))
            
        if not timeline_data:
            self.add_row("", "")

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Add Entry")
        btn_add.clicked.connect(lambda: self.add_row("", ""))
        btn_del = QPushButton("❌ Remove Selected Entry")
        btn_del.clicked.connect(self.remove_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def add_row(self, date_str, remarks):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(date_str))
        self.table.setItem(row, 1, QTableWidgetItem(remarks))

    def remove_row(self):
        for item in self.table.selectedItems():
            self.table.removeRow(item.row())

    def handle_double_click(self, row, col):
        if col == 0: 
            dlg = QDialog(self)
            dlg.setWindowTitle("📅 Select Date")
            dlg.resize(350, 250)
            dlg_layout = QVBoxLayout(dlg)
            
            cal = QCalendarWidget()
            cal.setGridVisible(True)
            
            existing_date = self.table.item(row, col).text().strip()
            if existing_date:
                qdate = QDate.fromString(existing_date, "yyyy-MM-dd")
                if qdate.isValid():
                    cal.setSelectedDate(qdate)
                    
            dlg_layout.addWidget(cal)
            
            btn_select = QPushButton("✔️ Select Date")
            btn_select.clicked.connect(dlg.accept)
            dlg_layout.addWidget(btn_select)
            
            if dlg.exec() == QDialog.DialogCode.Accepted:
                selected_date = cal.selectedDate().toString("yyyy-MM-dd")
                self.table.setItem(row, 0, QTableWidgetItem(selected_date))
        else:
            self.table.editItem(self.table.item(row, col))

    def get_data(self):
        data = []
        for row in range(self.table.rowCount()):
            d_item = self.table.item(row, 0)
            r_item = self.table.item(row, 1)
            date_val = d_item.text().strip() if d_item else ""
            rem_val = r_item.text().strip() if r_item else ""
            if date_val or rem_val:
                data.append({"Date": date_val, "Remarks": rem_val})
        return data

class TaskTableDialog(QDialog):
    def __init__(self, title, tasks, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 450)
        layout = QVBoxLayout(self)

        table = QTableWidget()
        layout.addWidget(table)
        headers = ["Date", "Task Name", "Deadline", "Priority", "Project", "Notes"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(tasks))

        for row_idx, (t_id, t_date, t_status, details_json) in enumerate(tasks):
            details = json.loads(details_json)
            table.setItem(row_idx, 0, QTableWidgetItem(t_date))
            table.setItem(row_idx, 1, QTableWidgetItem(details.get("Task Name", "")))
            table.setItem(row_idx, 2, QTableWidgetItem(details.get("Dead line", "")))
            table.setItem(row_idx, 3, QTableWidgetItem(details.get("Priority", "")))
            table.setItem(row_idx, 4, QTableWidgetItem(details.get("Project", "")))
            table.setItem(row_idx, 5, QTableWidgetItem(details.get("Notes", "")))

        btn_close = QPushButton("❌ Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class DynamicFormDialog(QDialog):
    def __init__(self, title, name_field_label, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📝 {title}")
        self.setMinimumWidth(450)
        self.layout = QFormLayout(self)
        self.inputs = {}
        
        self.name_input = QLineEdit()
        self.layout.addRow(f"<b>{name_field_label} *</b>", self.name_input)
        
        for field in fields:
            if "priority" in field.lower() or "complexity" in field.lower():
                inp = QComboBox()
                inp.addItems(["High", "Medium", "Low"])
            elif "description" in field.lower() or "notes" in field.lower():
                inp = QTextEdit()
                inp.setMaximumHeight(80)
            else:
                inp = QLineEdit()
                
            self.inputs[field] = inp
            self.layout.addRow(field, inp)
            
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        self.layout.addRow(self.btn_box)

    def get_data(self):
        data = {"Primary Name": self.name_input.text().strip()}
        for field, inp in self.inputs.items():
            if isinstance(inp, QComboBox):
                data[field] = inp.currentText()
            elif isinstance(inp, QTextEdit):
                data[field] = inp.toPlainText().strip()
            else:
                data[field] = inp.text().strip()
        return data

class NewTaskDialog(QDialog):
    def __init__(self, default_date, project_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("➕ Create New Task")
        self.setMinimumWidth(450)
        self.layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.layout.addRow("<b>Task Name *</b>", self.name_input)
        
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.fromString(default_date, Qt.DateFormat.ISODate))
        self.layout.addRow("Date", self.date_input)
        
        self.deadline_input = QDateEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDate(QDate.currentDate())
        self.layout.addRow("Dead line", self.deadline_input)
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["High", "Medium", "Low"])
        self.layout.addRow("Priority", self.priority_combo)
        
        self.project_combo = QComboBox()
        self.project_combo.addItem("None")
        self.project_combo.addItems(project_names)
        self.layout.addRow("Project", self.project_combo)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.layout.addRow("Notes", self.notes_input)
        
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        self.layout.addRow(self.btn_box)

    def get_data(self):
        return {
            "Task Name": self.name_input.text().strip(),
            "Date": self.date_input.date().toString(Qt.DateFormat.ISODate),
            "Dead line": self.deadline_input.date().toString(Qt.DateFormat.ISODate),
            "Priority": self.priority_combo.currentText(),
            "Project": self.project_combo.currentText(),
            "Notes": self.notes_input.toPlainText().strip()
        }

class EditProjectDialog(QDialog):
    def __init__(self, project_name, current_status, details_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"✏️ Edit Project: {project_name}")
        self.setMinimumWidth(450)
        self.layout = QFormLayout(self)
        self.inputs = {}
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "hold", "additional info", "closed"])
        
        idx = self.status_combo.findText(current_status, Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive)
        if idx >= 0: self.status_combo.setCurrentIndex(idx)
        else: self.status_combo.setCurrentText(current_status)
        
        self.layout.addRow("<b>Project Status</b>", self.status_combo)
        
        for field, val in details_dict.items():
            if field == "_quick_links": continue
            if "priority" in field.lower() or "complexity" in field.lower():
                inp = QComboBox()
                inp.addItems(["High", "Medium", "Low"])
                inp.setCurrentText(str(val))
            elif "description" in field.lower() or "notes" in field.lower():
                inp = QTextEdit()
                inp.setMaximumHeight(80)
                inp.setPlainText(str(val))
            else:
                inp = QLineEdit()
                inp.setText(str(val))
            self.inputs[field] = inp
            self.layout.addRow(field, inp)
            
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        self.layout.addRow(self.btn_box)

    def get_data(self):
        data = {}
        for field, inp in self.inputs.items():
            if isinstance(inp, QComboBox):
                data[field] = inp.currentText()
            elif isinstance(inp, QTextEdit):
                data[field] = inp.toPlainText().strip()
            else:
                data[field] = inp.text().strip()
        return self.status_combo.currentText(), data

class EngineeringWorkspace(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engineering Workspace")
        self.resize(1300, 850)
        self.current_theme = "dark"
        self.current_loaded_project = None
        self.highlighted_dates = []
        database.init_db()
        
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.handle_undo)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("QFrame { background-color: palette(alternate-base); border-right: 1px solid #3a3b45; }")
        sidebar_layout = QVBoxLayout(sidebar)
        
        app_title = QLabel("Engineering\nWorkspace")
        app_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CC2FF; padding: 15px 0px; border: none;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addSpacing(20)
        
        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_projects = QPushButton("📁 Projects")
        self.btn_tasks = QPushButton("✅ Tasks")
        
        for btn in [self.btn_dashboard, self.btn_projects, self.btn_tasks]:
            btn.setMinimumHeight(45)
            btn.setStyleSheet("text-align: left; padding-left: 15px; font-size: 14px; font-weight: bold;")
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch() 
        
        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_settings.setMinimumHeight(45)
        self.btn_settings.setStyleSheet("text-align: left; padding-left: 15px; font-size: 14px; font-weight: bold;")
        sidebar_layout.addWidget(self.btn_settings)
        
        main_layout.addWidget(sidebar)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        self.build_dashboard_page()
        self.build_projects_page()
        self.build_tasks_page()
        self.build_settings_page()
        self.refresh_dashboard()
        self.update_calendar_colors()
        self.update_task_counts()

        self.btn_dashboard.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.btn_projects.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_tasks.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.btn_settings.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))

    # --- ACTIVITY LOGGING ---
    def log_activity(self, action, details):
        main_path = database.get_setting('main_path')
        if main_path and os.path.isdir(main_path):
            log_file = os.path.join(main_path, "activity_log.txt")
        else:
            log_file = "activity_log.txt" 
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {action} | {details}\n")
        except Exception:
            pass

    def handle_undo(self):
        fw = QApplication.focusWidget()
        if hasattr(fw, 'undo'):
            fw.undo()

    def build_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        hero_widget = QWidget()
        hero_layout = QHBoxLayout(hero_widget)
        hero_layout.setContentsMargins(0, 0, 0, 15)
        hero_layout.setSpacing(20)
        
        greet_panel = QFrame()
        greet_panel.setObjectName("GreetPanel")
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_image.png")
        image_path_qt = image_path.replace("\\", "/") 
        
        if os.path.exists(image_path):
            greet_style = f"QFrame#GreetPanel {{ border-image: url({image_path_qt}) 0 0 0 0 stretch stretch; border-radius: 12px; }}"
        else:
            greet_style = "QFrame#GreetPanel { background-color: #1e1e2e; border-radius: 12px; border: 1px solid #3a3b45; }"
        greet_panel.setStyleSheet(greet_style)
        
        greet_layout = QVBoxLayout(greet_panel)
        greet_layout.setContentsMargins(30, 25, 30, 25)
        
        self.lbl_greeting = QLabel("Hello!")
        self.lbl_greeting.setStyleSheet("font-size: 40px; font-weight: bold; color: white; background: transparent; border: none;")
        greet_layout.addStretch()
        greet_layout.addWidget(self.lbl_greeting)
        greet_layout.addStretch()
        hero_layout.addWidget(greet_panel, stretch=2)
        
        cal_container = QVBoxLayout()
        cal_container.setSpacing(5)
        
        self.calendar = QCalendarWidget()
        self.calendar.setFixedSize(300, 180) 
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setStyleSheet("""
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #202020; padding: 2px; }
            QCalendarWidget QToolButton { color: white; font-size: 14px; font-weight: bold; background-color: transparent; border: none; }
            QCalendarWidget QToolButton:hover { background-color: #333333; border-radius: 4px; }
            QCalendarWidget QMenu { background-color: #2b2b2b; color: white; }
            QCalendarWidget QSpinBox { color: white; background: transparent; selection-background-color: #4CC2FF; selection-color: black; }
            QCalendarWidget QAbstractItemView:enabled { color: white; background-color: #202020; selection-background-color: #4CC2FF; selection-color: black; }
            QCalendarWidget QAbstractItemView:disabled { color: #555555; }
        """)
        cal_container.addWidget(self.calendar)
        
        btn_today = QPushButton("📅 Today")
        btn_today.setStyleSheet("background-color: #333333; font-weight: bold; padding: 5px; border-radius: 4px;")
        btn_today.clicked.connect(lambda: self.calendar.setSelectedDate(QDate.currentDate()))
        cal_container.addWidget(btn_today)
        
        hero_layout.addLayout(cal_container, stretch=1)
        layout.addWidget(hero_widget)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        proj_container = QWidget()
        proj_layout = QVBoxLayout(proj_container)
        proj_layout.setContentsMargins(0,0,0,0)
        header_lbl = QLabel("🚀 Active Projects")
        header_lbl.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 5px;")
        proj_layout.addWidget(header_lbl)
        
        self.dash_proj_scroll = QScrollArea()
        self.dash_proj_scroll.setWidgetResizable(True)
        self.dash_proj_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.dash_proj_inner = QWidget()
        self.dash_proj_inner.setStyleSheet("background: transparent;")
        self.dash_layout = QGridLayout(self.dash_proj_inner)
        self.dash_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.dash_layout.setSpacing(15)
        self.dash_proj_scroll.setWidget(self.dash_proj_inner)
        proj_layout.addWidget(self.dash_proj_scroll, stretch=3)
        
        # --- Dashboard Quick Links Header ---
        ql_header_layout = QHBoxLayout()
        ql_header_layout.setContentsMargins(0, 10, 0, 5)
        ql_label = QLabel("🔗 Quick Links")
        ql_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        btn_dash_ql_add = QPushButton("+")
        btn_dash_ql_add.setFixedSize(25, 25)
        btn_dash_ql_add.clicked.connect(self.add_dash_quick_link)
        
        btn_dash_ql_del = QPushButton("-")
        btn_dash_ql_del.setFixedSize(25, 25)
        btn_dash_ql_del.clicked.connect(self.del_dash_quick_link)
        
        ql_header_layout.addWidget(ql_label)
        ql_header_layout.addWidget(btn_dash_ql_add)
        ql_header_layout.addWidget(btn_dash_ql_del)
        ql_header_layout.addStretch()  # Moved stretch to the end to pin buttons left
        proj_layout.addLayout(ql_header_layout)
        
        self.dash_ql_scroll = QScrollArea()
        self.dash_ql_scroll.setMaximumHeight(80)
        self.dash_ql_scroll.setWidgetResizable(True)
        self.dash_ql_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.dash_ql_inner = QWidget()
        self.dash_ql_inner.setStyleSheet("background: transparent;")
        self.dash_ql_layout = QHBoxLayout(self.dash_ql_inner)
        self.dash_ql_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.dash_ql_layout.setContentsMargins(0,0,0,0)
        self.dash_ql_scroll.setWidget(self.dash_ql_inner)
        proj_layout.addWidget(self.dash_ql_scroll, stretch=1)
        
        bottom_layout.addWidget(proj_container, stretch=2)

        task_container = QFrame()
        task_container.setStyleSheet("QFrame { background-color: palette(alternate-base); border-radius: 8px; border: 1px solid #3a3b45; }")
        task_layout = QVBoxLayout(task_container)
        task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        task_header = QLabel("📝 Today's Tasks")
        task_header.setStyleSheet("font-size: 18px; font-weight: bold; border: none; margin-bottom: 10px;")
        task_layout.addWidget(task_header)
        
        self.dash_tasks_layout = QVBoxLayout()
        task_layout.addLayout(self.dash_tasks_layout)
        task_layout.addStretch()
        bottom_layout.addWidget(task_container, stretch=1)

        layout.addLayout(bottom_layout)
        self.stacked_widget.addWidget(page)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_greeting)
        self.timer.start(60000)
        self.update_time_greeting()

    def update_time_greeting(self):
        hour = QTime.currentTime().hour()
        if hour < 12: greeting = "Good Morning"
        elif hour < 17: greeting = "Good Afternoon"
        else: greeting = "Good Evening"
        self.lbl_greeting.setText(f"{greeting},\n{database.get_setting('user_name') or 'Engineer'}.")

    def update_calendar_colors(self):
        fmt_clear = QTextCharFormat()
        for d in self.highlighted_dates:
            self.calendar.setDateTextFormat(d, fmt_clear)
            self.task_calendar.setDateTextFormat(d, fmt_clear)
        self.highlighted_dates.clear()

        fmt_highlight = QTextCharFormat()
        fmt_highlight.setForeground(QColor("#FFC107"))
        fmt_highlight.setFontWeight(700)
        fmt_highlight.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        
        dates_with_tasks = database.get_dates_with_tasks()
        for d_str in dates_with_tasks:
            qdate = QDate.fromString(d_str, Qt.DateFormat.ISODate)
            self.highlighted_dates.append(qdate)
            self.calendar.setDateTextFormat(qdate, fmt_highlight)
            self.task_calendar.setDateTextFormat(qdate, fmt_highlight)

    def update_task_counts(self):
        tasks = database.get_all_tasks()
        pending = sum(1 for t in tasks if t[2] == 'pending')
        completed = sum(1 for t in tasks if t[2] == 'completed')
        self.btn_pending_card.setText(f"⏳ Pending Tasks\n{pending}")
        self.btn_completed_card.setText(f"🏆 Completed Tasks\n{completed}")

    def show_tasks_table(self, status):
        all_tasks = database.get_all_tasks()
        filtered_tasks = [t for t in all_tasks if t[2] == status]
        dialog = TaskTableDialog(f"All {status.capitalize()} Tasks", filtered_tasks, self)
        dialog.exec()

    def jump_to_project_from_dashboard(self, project_name):
        self.stacked_widget.setCurrentIndex(1)
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == project_name:
                self.project_list.setCurrentItem(item)
                self.load_project_files(item)
                break

    def build_projects_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        top_bar = QHBoxLayout()
        btn_new_project = QPushButton("➕ Create New Project")
        btn_new_project.clicked.connect(self.create_new_project)
        top_bar.addWidget(btn_new_project)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("<b>📂 Project List</b>"))
        self.project_list = QListWidget()
        self.project_list.itemClicked.connect(self.load_project_files)
        left_layout.addWidget(self.project_list)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        details_header_layout = QHBoxLayout()
        details_header_layout.addWidget(QLabel("<b>📋 Project Details</b>"))
        
        self.btn_top_edit = QPushButton("✏️")
        self.btn_top_edit.setFixedSize(30, 30)
        self.btn_top_edit.hide()
        self.btn_top_edit.clicked.connect(self.trigger_top_edit)
        
        self.btn_top_popup = QPushButton("📄")
        self.btn_top_popup.setFixedSize(30, 30)
        self.btn_top_popup.hide()
        self.btn_top_popup.clicked.connect(self.trigger_top_popup)

        self.btn_top_notes = QPushButton("🗒️")
        self.btn_top_notes.setFixedSize(30, 30)
        self.btn_top_notes.hide()
        self.btn_top_notes.clicked.connect(self.trigger_top_notes)
        
        self.btn_top_timeline = QPushButton("🕒")
        self.btn_top_timeline.setToolTip("Project Timeline")
        self.btn_top_timeline.setFixedSize(30, 30)
        self.btn_top_timeline.hide()
        self.btn_top_timeline.clicked.connect(self.trigger_top_timeline)
        
        for btn in [self.btn_top_edit, self.btn_top_popup, self.btn_top_notes, self.btn_top_timeline]:
            details_header_layout.addWidget(btn)
        details_header_layout.addStretch()
        right_layout.addLayout(details_header_layout)

        self.details_group = QFrame()
        self.details_group.setStyleSheet("QFrame { background-color: palette(alternate-base); border-radius: 5px; }")
        self.details_layout = QFormLayout(self.details_group)
        self.details_layout.addRow(QLabel("<i>Select a project to view details...</i>"))
        right_layout.addWidget(self.details_group)
        right_layout.addSpacing(10)
        
        # --- Project Quick Links UI ---
        pql_header_layout = QHBoxLayout()
        pql_header_layout.addWidget(QLabel("<b>🔗 Project Quick Links</b>"))
        
        self.btn_pql_add = QPushButton("+")
        self.btn_pql_add.setFixedSize(25, 25)
        self.btn_pql_add.clicked.connect(self.add_proj_quick_link)
        
        self.btn_pql_del = QPushButton("-")
        self.btn_pql_del.setFixedSize(25, 25)
        self.btn_pql_del.clicked.connect(self.del_proj_quick_link)
        
        pql_header_layout.addWidget(self.btn_pql_add)
        pql_header_layout.addWidget(self.btn_pql_del)
        pql_header_layout.addStretch() # Moved stretch to the end to pin buttons left
        right_layout.addLayout(pql_header_layout)

        self.pql_scroll = QScrollArea()
        self.pql_scroll.setMaximumHeight(65)
        self.pql_scroll.setWidgetResizable(True)
        self.pql_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.pql_inner = QWidget()
        self.pql_inner.setStyleSheet("background: transparent;")
        self.pql_layout = QHBoxLayout(self.pql_inner)
        self.pql_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.pql_layout.setContentsMargins(0, 0, 0, 0)
        self.pql_scroll.setWidget(self.pql_inner)
        
        right_layout.addWidget(self.pql_scroll)
        right_layout.addSpacing(10)
        # ------------------------------

        right_layout.addWidget(QLabel("<b>🗄️ Project Files</b>"))
        
        self.file_model = QFileSystemModel()
        self.file_model.setReadOnly(False) 
        self.file_model.setRootPath("")
        
        self.file_model.fileRenamed.connect(lambda path, old_name, new_name: self.log_activity("RENAMED", f"'{old_name}' to '{new_name}' in {path}"))
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setColumnWidth(0, 250)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.open_context_menu)
        self.tree_view.doubleClicked.connect(self.open_file_on_double_click)
        
        right_layout.addWidget(self.tree_view)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 850])
        layout.addWidget(splitter)
        self.stacked_widget.addWidget(page) 

    def build_tasks_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("<b>📅 Select Date</b>"))
        
        self.task_calendar = QCalendarWidget()
        self.task_calendar.setFixedSize(300, 180)
        self.task_calendar.setGridVisible(False)
        self.task_calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.task_calendar.setStyleSheet("""
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #202020; padding: 2px; }
            QCalendarWidget QToolButton { color: white; font-size: 14px; font-weight: bold; background-color: transparent; border: none; }
            QCalendarWidget QToolButton:hover { background-color: #333333; border-radius: 4px; }
            QCalendarWidget QMenu { background-color: #2b2b2b; color: white; }
            QCalendarWidget QSpinBox { color: white; background: transparent; selection-background-color: #4CC2FF; selection-color: black; }
            QCalendarWidget QAbstractItemView:enabled { color: white; background-color: #202020; selection-background-color: #4CC2FF; selection-color: black; }
            QCalendarWidget QAbstractItemView:disabled { color: #555555; }
        """)
        self.task_calendar.clicked.connect(self.load_tasks_for_date)
        left_layout.addWidget(self.task_calendar)
        
        btn_today_task = QPushButton("📅 Today")
        btn_today_task.setStyleSheet("background-color: #333333; font-weight: bold; padding: 5px; border-radius: 4px;")
        btn_today_task.clicked.connect(lambda: self.task_calendar.setSelectedDate(QDate.currentDate()))
        left_layout.addWidget(btn_today_task)
        
        left_layout.addSpacing(20)
        
        self.btn_pending_card = QPushButton("⏳ Pending Tasks\n0")
        self.btn_pending_card.setStyleSheet("QPushButton { background-color: #e3a83b; color: black; font-weight: bold; border-radius: 8px; padding: 15px; font-size: 14px; text-align: left; } QPushButton:hover { background-color: #c79230; }")
        self.btn_pending_card.clicked.connect(lambda: self.show_tasks_table('pending'))
        left_layout.addWidget(self.btn_pending_card)

        self.btn_completed_card = QPushButton("🏆 Completed Tasks\n0")
        self.btn_completed_card.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; border-radius: 8px; padding: 15px; font-size: 14px; text-align: left; } QPushButton:hover { background-color: #218838; }")
        self.btn_completed_card.clicked.connect(lambda: self.show_tasks_table('completed'))
        left_layout.addWidget(self.btn_completed_card)
        
        left_layout.addStretch()
        splitter.addWidget(left_panel)
        
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.addWidget(QLabel("<b>🎯 Tasks for Selected Date</b>"))
        
        self.task_list_widget = QListWidget()
        self.task_list_widget.itemClicked.connect(self.display_task_details)
        mid_layout.addWidget(self.task_list_widget)
        
        btn_add_task = QPushButton("➕ Add New Task")
        btn_add_task.clicked.connect(self.create_new_task)
        mid_layout.addWidget(btn_add_task)
        splitter.addWidget(mid_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("<b>🔍 Task Details</b>"))
        
        self.task_details_group = QFrame()
        self.task_details_group.setStyleSheet("QFrame { background-color: palette(alternate-base); border-radius: 5px; }")
        self.task_details_layout = QFormLayout(self.task_details_group)
        self.task_details_layout.addRow(QLabel("<i>Select a task to view details...</i>"))
        right_layout.addWidget(self.task_details_group)
        right_layout.addStretch()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 300, 400])
        layout.addWidget(splitter)
        self.stacked_widget.addWidget(page)
        
        self.load_tasks_for_date(QDate.currentDate())

    def build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>⚙️ Settings</h2>"))
        header_layout.addStretch()
        theme_btn = QPushButton("🌓 Toggle Dark/Light Mode")
        theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(theme_btn)
        layout.addLayout(header_layout)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("<b>User Name (For Greeting)</b>"))
        self.name_input = QLineEdit(database.get_setting('user_name'))
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        layout.addWidget(QLabel("<b>Main Workspace Directory</b>"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(database.get_setting('main_path'))
        self.path_input.setReadOnly(True)
        btn_browse = QPushButton("📂 Browse...")
        btn_browse.clicked.connect(self.browse_main_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        layout.addSpacing(15)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setStyleSheet("QScrollArea { border: none; }")
        settings_container = QWidget()
        lists_layout = QGridLayout(settings_container)
        
        def create_list_panel(title, db_key, list_widget, row, col):
            panel = QVBoxLayout()
            panel.addWidget(QLabel(f"<b>{title}</b>"))
            list_widget.addItems(database.get_setting(db_key))
            panel.addWidget(list_widget)
            
            btn_box = QHBoxLayout()
            b_add, b_ren, b_del = QPushButton("+"), QPushButton("✏️"), QPushButton("-")
            b_up, b_down = QPushButton("⬆️"), QPushButton("⬇️")
            
            b_add.clicked.connect(lambda: self.add_to_list(list_widget, title))
            b_ren.clicked.connect(lambda: self.rename_in_list(list_widget, title))
            b_del.clicked.connect(lambda: self.del_from_list(list_widget))
            b_up.clicked.connect(lambda: self.move_list_item(list_widget, -1))
            b_down.clicked.connect(lambda: self.move_list_item(list_widget, 1))
            
            for b in [b_add, b_ren, b_del, b_up, b_down]: btn_box.addWidget(b)
            panel.addLayout(btn_box)
            lists_layout.addLayout(panel, row, col)

        self.folder_list = QListWidget()
        self.field_list = QListWidget()
        self.dash_field_list = QListWidget()
        self.task_field_list = QListWidget()
        
        create_list_panel("Standard Subfolders", "subfolders", self.folder_list, 0, 0)
        create_list_panel("Project Form Fields", "project_fields", self.field_list, 0, 1)
        create_list_panel("Dashboard Card Fields", "dashboard_fields", self.dash_field_list, 1, 0)
        create_list_panel("Task Form Fields", "task_fields", self.task_field_list, 1, 1)

        settings_scroll.setWidget(settings_container)
        layout.addWidget(settings_scroll)
        
        self.cb_apply_existing = QCheckBox("Apply structural changes to existing projects (will overwrite/create files)")
        self.cb_apply_existing.setStyleSheet("color: #e3a83b; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.cb_apply_existing)

        btn_save = QPushButton("💾 Save Settings")
        btn_save.setMinimumHeight(40)
        btn_save.setStyleSheet("background-color: #2b5c8f; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)
        self.stacked_widget.addWidget(page)

    def move_list_item(self, list_widget, direction):
        row = list_widget.currentRow()
        if row < 0: return
        new_row = row + direction
        if new_row < 0 or new_row >= list_widget.count(): return
        item = list_widget.takeItem(row)
        list_widget.insertItem(new_row, item)
        list_widget.setCurrentRow(new_row)

    # --- Quick Links (Dashboard & Projects) ---
    def add_dash_quick_link(self):
        dialog = QuickLinkDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, url = dialog.get_data()
            if name and url:
                qls = database.get_setting('quick_links')
                qls.append(f"{name} | {url}")
                database.update_setting('quick_links', qls)
                self.refresh_dashboard()

    def del_dash_quick_link(self):
        qls = database.get_setting('quick_links')
        if not qls: return
        item, ok = QInputDialog.getItem(self, "❌ Delete Quick Link", "Select link to remove:", qls, 0, False)
        if ok and item:
            qls.remove(item)
            database.update_setting('quick_links', qls)
            self.refresh_dashboard()

    def add_proj_quick_link(self):
        if not self.current_loaded_project: return
        dialog = QuickLinkDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, url = dialog.get_data()
            if name and url:
                proj_name, path, status, details = self.current_loaded_project
                pqls = details.get("_quick_links", [])
                pqls.append(f"{name} | {url}")
                details["_quick_links"] = pqls
                database.update_project_details(proj_name, status, details)
                self.current_loaded_project = (proj_name, path, status, details)
                self.refresh_proj_quick_links(proj_name, details)

    def del_proj_quick_link(self):
        if not self.current_loaded_project: return
        proj_name, path, status, details = self.current_loaded_project
        pqls = details.get("_quick_links", [])
        if not pqls: return
        
        item, ok = QInputDialog.getItem(self, "❌ Delete Quick Link", "Select link to remove:", pqls, 0, False)
        if ok and item:
            pqls.remove(item)
            details["_quick_links"] = pqls
            database.update_project_details(proj_name, status, details)
            self.current_loaded_project = (proj_name, path, status, details)
            self.refresh_proj_quick_links(proj_name, details)

    def refresh_proj_quick_links(self, proj_name, details):
        while self.pql_layout.count():
            item = self.pql_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        pqls = details.get("_quick_links", [])
        if not pqls:
            lbl = QLabel("<i>No quick links added.</i>")
            lbl.setStyleSheet("color: #858796;")
            self.pql_layout.addWidget(lbl)
        else:
            for item in pqls:
                parts = item.split("|", 1)
                n = parts[0].strip()
                u = parts[1].strip() if len(parts)>1 else ""
                btn = QPushButton(n)
                btn.setStyleSheet("background-color: #333333; padding: 5px 15px; border-radius: 4px;")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, url=u: QDesktopServices.openUrl(QUrl(url) if url.startswith('http') else QUrl.fromLocalFile(url)))
                self.pql_layout.addWidget(btn)
        self.pql_layout.addStretch()

    # --- Actions & Logic ---
    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        qdarktheme.setup_theme(self.current_theme)

    def write_notepad_files(self, name, path, details):
        details_path = os.path.join(path, f"{name}_Details.txt")
        try:
            with open(details_path, "w", encoding="utf-8") as f:
                f.write(f"PROJECT DETAILS: {name}\n")
                f.write("="*40 + "\n\n")
                for k, v in details.items():
                    if k != "_quick_links":
                        f.write(f"{k.upper()}:\n{v}\n\n")
        except Exception as e: pass

    def open_notepad_file(self, name, path, file_type):
        file_path = os.path.join(path, f"{name}_{file_type.capitalize()}.txt")
        if os.path.exists(file_path):
            self.log_activity("OPENED FILE", file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else:
            if file_type == "notes":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"PROJECT NOTES: {name}\n")
                    f.write("="*40 + "\n\n")
                self.log_activity("CREATED FILE", file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                QMessageBox.warning(self, "Not Found", f"{file_type.title()} file not found.")

    def open_file_on_double_click(self, index):
        if not self.file_model.isDir(index):
            file_path = self.file_model.filePath(index)
            self.log_activity("OPENED FILE", file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def refresh_dashboard(self):
        for i in reversed(range(self.dash_layout.count())): 
            w = self.dash_layout.itemAt(i).widget()
            if w: w.setParent(None)
                
        self.project_list.clear()
        
        projects = database.get_all_projects()
        dash_fields = database.get_setting('dashboard_fields')
        
        groups = {'active': [], 'hold': [], 'additional info': [], 'closed': []}
        for proj in projects:
            s = proj[3].lower()
            if s in groups: groups[s].append(proj)
            else: groups['active'].append(proj)
            
        for g in groups.values():
            g.sort(key=lambda x: x[0].lower())
            
        for s_key, title in [('active', 'ACTIVE'), ('hold', 'HOLD'), ('additional info', 'ADDITIONAL INFO'), ('closed', 'CLOSED')]:
            if groups[s_key]:
                sep = QListWidgetItem(f"--- {title} ---")
                sep.setFlags(Qt.ItemFlag.NoItemFlags)
                sep.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                sep.setForeground(QColor("#4CC2FF"))
                self.project_list.addItem(sep)
                
                for name, path, details_str, status in groups[s_key]:
                    item = QListWidgetItem(name)
                    item.setData(Qt.ItemDataRole.UserRole, name)
                    self.project_list.addItem(item)
        
        row, col = 0, 0
        for name, path, details_str, status in groups['active']:
            card = ClickableFrame(name)
            card.clicked.connect(self.jump_to_project_from_dashboard)
            card.setMaximumHeight(110)
            card.setStyleSheet("QFrame { background-color: palette(alternate-base); border: 1px solid #3a3b45; border-radius: 12px; } QFrame:hover { border: 1px solid #5a5c69; }")
            
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(4)
            c_layout.setContentsMargins(15, 12, 15, 12)
            
            title = QLabel(f"<h3 style='margin:0; padding:0;'>{name}</h3>")
            title.setStyleSheet("background: transparent; border: none;")
            c_layout.addWidget(title)
            
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background: transparent; border-top: 1px solid #3a3b45; margin-bottom: 4px;")
            c_layout.addWidget(line)
            
            if details_str:
                details = json.loads(details_str)
                for df in dash_fields:
                    if df in details and details[df] and df != "_quick_links":
                        lbl = SelectableLabel(f"<b style='color: #858796;'>{df}:</b> {details[df]}")
                        lbl.setStyleSheet("background: transparent; border: none; font-size: 13px;")
                        c_layout.addWidget(lbl)
            c_layout.addStretch()
            self.dash_layout.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        while self.dash_ql_layout.count():
            item = self.dash_ql_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        qls = database.get_setting('quick_links')
        if not qls:
            lbl = QLabel("<i>No quick links added.</i>")
            lbl.setStyleSheet("color: #858796;")
            self.dash_ql_layout.addWidget(lbl)
        else:
            for item in qls:
                parts = item.split("|", 1)
                n = parts[0].strip()
                u = parts[1].strip() if len(parts)>1 else ""
                btn = QPushButton(n)
                btn.setStyleSheet("background-color: #333333; padding: 5px 15px; border-radius: 4px;")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, url=u: QDesktopServices.openUrl(QUrl(url) if url.startswith('http') else QUrl.fromLocalFile(url)))
                self.dash_ql_layout.addWidget(btn)
        self.dash_ql_layout.addStretch()

        for i in reversed(range(self.dash_tasks_layout.count())):
            layout_item = self.dash_tasks_layout.itemAt(i)
            if layout_item.widget(): layout_item.widget().setParent(None)
            elif layout_item.layout():
                while layout_item.layout().count():
                    item = layout_item.layout().takeAt(0)
                    if item.widget(): item.widget().deleteLater()
                layout_item.layout().deleteLater()

        today_str = QDate.currentDate().toString(Qt.DateFormat.ISODate)
        today_tasks = database.get_tasks_by_date(today_str)
        
        if not today_tasks:
            lbl = QLabel("<i>No tasks for today.</i>")
            lbl.setStyleSheet("color: #858796; border: none;")
            self.dash_tasks_layout.addWidget(lbl)
        else:
            for t_id, t_status, t_details_json in today_tasks:
                details = json.loads(t_details_json)
                task_name = details.get("Task Name", "Unnamed Task")
                
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0,0,0,0)
                
                chk = QCheckBox()
                chk.setChecked(t_status == 'completed')
                chk.stateChanged.connect(lambda state, tid=t_id: self.toggle_task_status(tid, state))
                
                lbl_task = DoubleClickLabel(task_name)
                font_style = "text-decoration: line-through; color: #858796;" if t_status == 'completed' else "color: white;"
                lbl_task.setStyleSheet(f"background: transparent; border: none; font-size: 14px; {font_style}")
                lbl_task.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl_task.doubleClicked.connect(lambda tid=t_id, d_str=today_str: self.jump_to_task(tid, d_str))
                
                row_layout.addWidget(chk)
                row_layout.addWidget(lbl_task)
                row_layout.addStretch()
                self.dash_tasks_layout.addWidget(row_widget)

    def create_new_project(self):
        main_path = database.get_setting('main_path')
        if not main_path or not os.path.isdir(main_path):
            QMessageBox.warning(self, "Setup Required", "Please set a valid Main Workspace Directory in the Settings tab first.")
            return

        dialog = DynamicFormDialog("Create New Project", "Project Name", database.get_setting('project_fields'), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            project_name = data.pop("Primary Name")
            if not project_name: return
                
            project_full_path = os.path.join(main_path, project_name)
            try:
                os.makedirs(project_full_path, exist_ok=True)
                for folder in database.get_setting('subfolders'):
                    os.makedirs(os.path.join(project_full_path, folder), exist_ok=True)
                
                with open(os.path.join(project_full_path, f"{project_name}_Notes.txt"), "w", encoding="utf-8") as f:
                    f.write(f"PROJECT NOTES: {project_name}\n\n")

                database.add_project(project_name, main_path, data)
                self.write_notepad_files(project_name, project_full_path, data)
                self.log_activity("CREATED PROJECT", project_full_path)
                self.refresh_dashboard()
                QMessageBox.information(self, "Success", f"Project '{project_name}' created!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folders: {str(e)}")

    def trigger_top_edit(self):
        if self.current_loaded_project: self.open_edit_dialog(*self.current_loaded_project)
    def trigger_top_popup(self):
        if self.current_loaded_project: self.open_notepad_file(self.current_loaded_project[0], self.current_loaded_project[1], "details")
    def trigger_top_notes(self):
        if self.current_loaded_project: self.open_notepad_file(self.current_loaded_project[0], self.current_loaded_project[1], "notes")
        
    def trigger_top_timeline(self):
        if self.current_loaded_project:
            project_name = self.current_loaded_project[0]
            timeline_data = database.get_project_timeline(project_name)
            dialog = TimelineDialog(project_name, timeline_data, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_data = dialog.get_data()
                database.update_project_timeline(project_name, new_data)
                QMessageBox.information(self, "Saved", "Project timeline updated successfully.")

    def load_project_files(self, item):
        if not item.flags() & Qt.ItemFlag.ItemIsSelectable:
            return 
        project_name = item.data(Qt.ItemDataRole.UserRole)
        for name, path, details_json, status in database.get_all_projects():
            if name == project_name:
                while self.details_layout.count():
                    child = self.details_layout.takeAt(0)
                    if child.widget(): child.widget().deleteLater()
                
                details = json.loads(details_json) if details_json else {}
                self.current_loaded_project = (name, path, status, details)
                self.btn_top_edit.show()
                self.btn_top_popup.show()
                self.btn_top_notes.show()
                self.btn_top_timeline.show()
                
                status_color = "green" if status == 'active' else "red" if status == 'closed' else "#FFC107"
                
                self.details_layout.addRow("<b>Project Name:</b>", SelectableLabel(name))
                self.details_layout.addRow("<b>Status:</b>", SelectableLabel(f"<span style='color:{status_color}'>{status.upper()}</span>"))
                
                for key, val in details.items():
                    if key == "_quick_links": continue
                    self.details_layout.addRow(f"<b>{key}:</b>", SelectableLabel(str(val)))

                self.refresh_proj_quick_links(name, details)
                self.tree_view.setRootIndex(self.file_model.setRootPath(path))
                break

    def open_edit_dialog(self, name, path, current_status, details):
        dialog = EditProjectDialog(name, current_status, details, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_status, new_data = dialog.get_data()
            
            if "_quick_links" in details:
                new_data["_quick_links"] = details["_quick_links"]
                
            database.update_project_details(name, new_status, new_data)
            self.write_notepad_files(name, path, new_data)
            self.refresh_dashboard()
            
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == name:
                    self.project_list.setCurrentItem(item)
                    self.load_project_files(item)
                    break

    def open_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid(): return
        
        raw_path = self.file_model.filePath(index)
        file_path = os.path.normpath(raw_path)
        is_dir = self.file_model.isDir(index)
        
        current_info = database.get_folder_info(file_path)
        if not current_info:
            current_info = database.get_folder_info(raw_path)
            
        is_iteration = False
        iter_data = {}
        try:
            if current_info:
                data = json.loads(current_info)
                if isinstance(data, dict) and "Iteration count" in data:
                    is_iteration = True
                    iter_data = data
        except:
            pass

        menu = QMenu()
        actions = {}
        
        actions["🔄 Create Iteration"] = lambda: self.create_iteration(file_path, is_dir)
        if is_iteration:
            actions["⚙️ Edit Iteration Details"] = lambda: self.edit_iteration_details(file_path, iter_data)
            
        actions["ℹ️ Folder/File Info"] = lambda: self.edit_folder_info(file_path, current_info)
        actions["📁 Open in File Explorer"] = lambda: (self.log_activity("OPENED DIRECTORY", raw_path), QDesktopServices.openUrl(QUrl.fromLocalFile(raw_path)))
        actions["✏️ Rename"] = lambda: self.tree_view.edit(index)
        actions["📋 Copy"] = lambda: self.copy_file_dir(file_path, is_dir)
        actions["✂️ Move"] = lambda: self.move_file_dir(file_path)
        actions["🗑️ Delete"] = lambda: self.delete_file_dir(file_path, index)
        
        for text in actions.keys(): menu.addAction(QAction(text, self))
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))
        if action and action.text() in actions: actions[action.text()]()

    def create_iteration(self, file_path, is_dir):
        base_dir = file_path if is_dir else os.path.dirname(file_path)
        dialog = IterationDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            folder_name = f"{data['Iteration count']}_{data['Category']}"
            new_folder_path = os.path.normpath(os.path.join(base_dir, folder_name))
            
            try:
                os.makedirs(new_folder_path, exist_ok=True)
                database.set_folder_info(new_folder_path, json.dumps(data))
                self.log_activity("CREATED ITERATION", new_folder_path)
                QMessageBox.information(self, "Success", f"Iteration folder '{folder_name}' created.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create folder: {str(e)}")

    def edit_iteration_details(self, file_path, existing_data):
        dialog = IterationDialog(existing_data=existing_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            database.set_folder_info(file_path, json.dumps(new_data))
            QMessageBox.information(self, "Updated", "Iteration details updated successfully.")

    def edit_folder_info(self, file_path, current_info):
        new_info, ok = QInputDialog.getMultiLineText(self, "Information", f"Details for:\n{os.path.basename(file_path)}", current_info)
        if ok: database.set_folder_info(file_path, new_info.strip())

    def copy_file_dir(self, file_path, is_dir):
        dest = QFileDialog.getExistingDirectory(self, "Select Destination")
        if dest:
            try: 
                if is_dir:
                    shutil.copytree(file_path, os.path.join(dest, os.path.basename(file_path)))
                else:
                    shutil.copy2(file_path, dest)
                self.log_activity("COPIED", f"{file_path} -> {dest}")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def move_file_dir(self, file_path):
        dest = QFileDialog.getExistingDirectory(self, "Select Destination")
        if dest:
            try: 
                shutil.move(file_path, dest)
                self.log_activity("MOVED", f"{file_path} -> {dest}")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def delete_file_dir(self, file_path, index):
        if QMessageBox.question(self, "🗑️ Delete", f"Permanently delete {os.path.basename(file_path)}?") == QMessageBox.StandardButton.Yes:
            self.file_model.remove(index)
            self.log_activity("DELETED", file_path)

    # --- Tasks Logic ---
    def create_new_task(self):
        selected_date = self.task_calendar.selectedDate().toString(Qt.DateFormat.ISODate)
        projects = [p[0] for p in database.get_all_projects()]
        dialog = NewTaskDialog(selected_date, projects, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            task_name = data.get("Task Name")
            task_date = data.get("Date")
            if not task_name: return
            
            database.add_task(task_date, data)
            self.load_tasks_for_date(self.task_calendar.selectedDate())
            self.refresh_dashboard()
            self.update_calendar_colors()
            self.update_task_counts()

    def load_tasks_for_date(self, qdate):
        date_str = qdate.toString(Qt.DateFormat.ISODate)
        self.task_list_widget.clear()
        
        while self.task_details_layout.count():
            child = self.task_details_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.task_details_layout.addRow(QLabel("<i>Select a task to view details...</i>"))

        tasks = database.get_tasks_by_date(date_str)
        for t_id, status, details_json in tasks:
            details = json.loads(details_json)
            name = details.get("Task Name", "Unnamed Task")
            display = name if status == 'pending' else f"{name} (Completed)"
            
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, (t_id, status, details))
            self.task_list_widget.addItem(item)

    def display_task_details(self, item):
        t_id, status, details = item.data(Qt.ItemDataRole.UserRole)
        
        while self.task_details_layout.count():
            child = self.task_details_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        status_color = "green" if status == 'completed' else "#e3a83b"
        self.task_details_layout.addRow("<b>Status:</b>", SelectableLabel(f"<span style='color:{status_color}'>{status.upper()}</span>"))
        
        for k, v in details.items():
            lbl = SelectableLabel(str(v))
            self.task_details_layout.addRow(f"<b>{k}:</b>", lbl)
            
        btn_toggle = QPushButton("✔️ Mark as Completed" if status == 'pending' else "⏳ Mark as Pending")
        btn_toggle.clicked.connect(lambda: self.toggle_task_status_from_details(t_id, 'completed' if status == 'pending' else 'pending'))
        self.task_details_layout.addRow(btn_toggle)

    def toggle_task_status_from_details(self, task_id, new_status):
        database.update_task_status(task_id, new_status)
        self.load_tasks_for_date(self.task_calendar.selectedDate())
        self.refresh_dashboard()
        self.update_task_counts()

    def toggle_task_status(self, task_id, check_state):
        new_status = 'completed' if check_state == Qt.CheckState.Checked.value else 'pending'
        database.update_task_status(task_id, new_status)
        self.refresh_dashboard()
        self.update_task_counts()
        
        today = QDate.currentDate()
        if self.task_calendar.selectedDate() == today:
            self.load_tasks_for_date(today)

    def jump_to_task(self, task_id, date_str):
        self.stacked_widget.setCurrentIndex(2)
        qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
        self.task_calendar.setSelectedDate(qdate)
        self.load_tasks_for_date(qdate)
        
        for i in range(self.task_list_widget.count()):
            item = self.task_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole)[0] == task_id:
                self.task_list_widget.setCurrentItem(item)
                self.display_task_details(item)
                break

    # --- Settings Logic ---
    def browse_main_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Main Workspace Directory")
        if path: self.path_input.setText(path)

    def add_to_list(self, list_widget, title):
        name, ok = QInputDialog.getText(self, title, "Enter item name:")
        if ok and name.strip(): list_widget.addItem(name.strip())
            
    def rename_in_list(self, list_widget, title):
        current = list_widget.currentItem()
        if current:
            new_name, ok = QInputDialog.getText(self, title, "Rename item:", text=current.text())
            if ok and new_name.strip(): current.setText(new_name.strip())
                
    def del_from_list(self, list_widget):
        if list_widget.currentItem(): list_widget.takeItem(list_widget.row(list_widget.currentItem()))
            
    def save_settings(self):
        database.update_setting('user_name', self.name_input.text())
        database.update_setting('main_path', self.path_input.text())
        
        fields = [self.field_list.item(i).text() for i in range(self.field_list.count())]
        folders = [self.folder_list.item(i).text() for i in range(self.folder_list.count())]
        
        database.update_setting('subfolders', folders)
        database.update_setting('project_fields', fields)
        database.update_setting('dashboard_fields', [self.dash_field_list.item(i).text() for i in range(self.dash_field_list.count())])
        database.update_setting('task_fields', [self.task_field_list.item(i).text() for i in range(self.task_field_list.count())])
        
        if self.cb_apply_existing.isChecked():
            for name, path, details_json, status in database.get_all_projects():
                old_details = json.loads(details_json) if details_json else {}
                new_details = {f: old_details.get(f, "") for f in fields}
                for k, v in old_details.items():
                    if k not in new_details: new_details[k] = v
                database.update_project_details(name, status, new_details)
                self.write_notepad_files(name, path, new_details)
                
                try:
                    for f in folders:
                        os.makedirs(os.path.join(path, f), exist_ok=True)
                except Exception:
                    pass
            
        self.refresh_dashboard()
        if self.current_loaded_project:
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.current_loaded_project[0]:
                    self.project_list.setCurrentItem(item)
                    self.load_project_files(item)
                    break
            
        QMessageBox.information(self, "Saved", "Settings updated successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme("dark")
    window = EngineeringWorkspace()
    window.show()
    sys.exit(app.exec())