import json, sys, os, winreg
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMenu, QDialog, QComboBox, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QDesktopServices
from default import DEFAULT_DATA

DATA_FILE = 'data.json'
STYLE_FILE = 'style.qss'
UI_FILE = 'interface.ui'
APP_NAME = 'MyMediaTracker'

def resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.abspath(filename)

def user_data_path():
    if sys.platform == 'win32':
        base = os.getenv('APPDATA') or os.path.expanduser('~')
    else:
        base = os.path.join(os.path.expanduser('~'), '.config')
    data_dir = os.path.join(base, APP_NAME)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DATA_FILE)

class EditItemDialog(QtWidgets.QDialog):
    def __init__(self, title, label, default_text='', ok_text='Сохранить', cancel_text='Отмена', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(label)
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setPlainText(default_text)
        self.text_edit.setMinimumHeight(40)
        buttons = QtWidgets.QHBoxLayout()
        self.btn_ok = QtWidgets.QPushButton(ok_text)
        self.btn_cancel = QtWidgets.QPushButton(cancel_text)
        buttons.addWidget(self.btn_ok)
        buttons.addWidget(self.btn_cancel)
        layout.addWidget(self.label)
        layout.addWidget(self.text_edit)
        layout.addLayout(buttons)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_text(self):
        return self.text_edit.toPlainText()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path(UI_FILE), self)

        self.category_buttons = {
            'Фильмы': self.pushButton, 
            'Сериалы': self.pushButton_2, 
            'Игры': self.pushButton_3, 
            'Аниме': self.pushButton_4, 
            'Книги': self.pushButton_5, 
            'Манга': self.pushButton_6, 
            'Прочее': self.pushButton_15}

        for lw in [self.listWidget, self.listWidget_2, self.listWidget_3]:
            lw.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            lw.setDragEnabled(True)
            lw.setAcceptDrops(True)
            lw.setDropIndicatorShown(True)
            lw.setDefaultDropAction(Qt.MoveAction)
            lw.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
            lw.setContextMenuPolicy(Qt.CustomContextMenu)
            lw.customContextMenuRequested.connect(self.open_context_menu)

        self.pushButton.setCheckable(True)
        self.pushButton_2.setCheckable(True)
        self.pushButton_3.setCheckable(True)
        self.pushButton_4.setCheckable(True)
        self.pushButton_5.setCheckable(True)
        self.pushButton_6.setCheckable(True)
        self.pushButton_15.setCheckable(True)
        self.category_group = QtWidgets.QButtonGroup()
        self.category_group.setExclusive(True)

        for btn in self.category_buttons.values():
            btn.setCheckable(True)
            self.category_group.addButton(btn)

        self.data_path = user_data_path()
        self.data = self.load_data()
        self.apply_window_size_from_settings()
        self.current_category = self.data['settings']['defaultCategory']
        self.update_category_buttons_visibility()
        self.ensure_valid_current_category()
        self.load_category(self.current_category)

        #Категории
        self.pushButton.clicked.connect(lambda: self.change_category('Фильмы'))
        self.pushButton_2.clicked.connect(lambda: self.change_category('Сериалы'))
        self.pushButton_3.clicked.connect(lambda: self.change_category('Игры'))
        self.pushButton_4.clicked.connect(lambda: self.change_category('Аниме'))
        self.pushButton_5.clicked.connect(lambda: self.change_category('Книги'))
        self.pushButton_6.clicked.connect(lambda: self.change_category('Манга'))
        self.pushButton_15.clicked.connect(lambda: self.change_category('Прочее'))
        #Плюсики для добавления элементов в списки
        self.pushButton_10.clicked.connect(lambda: self.add_item_to_list(self.listWidget, 'В планах'))
        self.pushButton_11.clicked.connect(lambda: self.add_item_to_list(self.listWidget_2, 'В процессе'))
        self.pushButton_12.clicked.connect(lambda: self.add_item_to_list(self.listWidget_3, 'Готово'))

        #Поиск
        self.lineEdit_2.textChanged.connect(lambda text: self.filter_list(self.listWidget, text))
        self.lineEdit_3.textChanged.connect(lambda text: self.filter_list(self.listWidget_2, text))
        self.lineEdit_4.textChanged.connect(lambda text: self.filter_list(self.listWidget_3, text))

        #Кнопки снизу
        self.pushButton_14.clicked.connect(self.export_json)
        self.pushButton_13.clicked.connect(self.import_json)
        self.pushButton_8.clicked.connect(self.import_from_txt)
        self.pushButton_9.clicked.connect(self.open_settings)
        self.lineEdit.setText(self.data.get('Profile', ''))
        self.lineEdit.textChanged.connect(self.on_profile_changed)
        self.pushButton_7.clicked.connect(self.save_data)

    def load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Проверяем версию профиля
            if data.get("ver") != DEFAULT_DATA["ver"]:
                self.update_version_profile(data, DEFAULT_DATA["ver"])
                with open(self.data_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            return data
        new_data = DEFAULT_DATA.copy()
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        return new_data

    def save_data(self):
        self.update_current_category_data()
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        QtWidgets.QMessageBox.information(self, 'Успех', 'Данные сохранены!')

    def add_item_to_list(self, list_widget, section_name):
        dialog = EditItemDialog(
            title='Добавление элемента',
            label='Введите название:',
            default_text='',
            ok_text='Добавить',
            cancel_text='Отмена',
            parent=self
        )
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            text = dialog.get_text().strip()
            if text:
                list_widget.addItem(text)

    def edit_item_dialog(self, current_text):
        dialog = EditItemDialog(
            title='Редактирование элемента',
            label='Измените название:',
            default_text=current_text,
            ok_text='Сохранить',
            cancel_text='Отмена',
            parent=self
        )
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            return dialog.get_text()
        return None

    def apply_window_size_from_settings(self):
        default_res = self.data.get('settings', {}).get('defaultResolution', '1024 x 800')
        if default_res:
            try:
                width, height = map(int, default_res.split(' x '))
                self.resize(width, height)
            except Exception as e:
                print(f'Ошибка при применении размера окна: {e}')

    def open_settings(self):
        dlg = SettingsDialog(self.data, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new_settings = dlg.get_settings()
            self.data['settings']['colors'] = new_settings['colors']
            self.data['settings']['visibleCategories'] = new_settings['visibleCategories']
            self.data['settings']['autostart'] = new_settings['autostart']
            self.data['settings']['defaultCategory'] = new_settings['defaultCategory']
            self.data['settings']['defaultResolution'] = new_settings['defaultResolution']
            self.data['settings']['fontsize'] = new_settings['fontsize']
            self.save_data()

            def set_autostart(enable=True):
                app_name = APP_NAME
                exe_path = sys.executable
                script_path = os.path.abspath(sys.argv[0])
                cmd = f'"{exe_path}" "{script_path}"'
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Run', 0, winreg.KEY_ALL_ACCESS)
                try:
                    if enable:
                        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                    else:
                        winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
                finally:
                    key.Close()

            set_autostart(new_settings['autostart'])
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle('Перезапуск')
            msg.setText('Для применения настроек требуется перезапустить программу. Пожалуйста, перезапустите программу вручную!')
            msg.setIcon(QtWidgets.QMessageBox.Question)
            btn_yes = msg.addButton('Да', QtWidgets.QMessageBox.YesRole)
            btn_no = msg.addButton('Нет', QtWidgets.QMessageBox.NoRole)
            msg.exec_()
            if msg.clickedButton() == btn_yes:
                QtWidgets.qApp.quit()

        self.ensure_valid_current_category()
        self.load_category(self.current_category)
        self.update_category_buttons_visibility()

    def ensure_valid_current_category(self):
        visible = self.data['settings']['visibleCategories']
        if self.current_category not in visible:
            self.current_category = visible[0]

    def update_category_buttons_visibility(self):
        visible = set(self.data['settings']['visibleCategories'])
        for cat, btn in self.category_buttons.items():
            btn.setVisible(cat in visible)

    def on_profile_changed(self, text):
        self.data['Profile'] = text

    def filter_list(self, list_widget, text):
        text = text.strip().lower()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def update_current_category_data(self):
        content = self.data['content']
        cat = self.current_category
        content[cat]['В планах'] = [self.listWidget.item(i).text() for i in range(self.listWidget.count())]
        content[cat]['В процессе'] = [self.listWidget_2.item(i).text() for i in range(self.listWidget_2.count())]
        content[cat]['Готово'] = [self.listWidget_3.item(i).text() for i in range(self.listWidget_3.count())]
        self.update_favorite_colors()

    def load_category(self, category):
        self.listWidget.clear()
        self.listWidget_2.clear()
        self.listWidget_3.clear()
        content = self.data['content']
        if category in content:
            for item in content[category]['В планах']:
                self.listWidget.addItem(item)
            for item in content[category]['В процессе']:
                self.listWidget_2.addItem(item)
            for item in content[category]['Готово']:
                self.listWidget_3.addItem(item)
        self.update_favorite_colors()

    def change_category(self, category):
        self.update_current_category_data()
        self.current_category = category
        self.load_category(category)
        for btn in self.category_buttons.values():
            if btn.text() == category:
                btn.setChecked(True)
                break

    def export_json(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Экспорт профиля в JSON', '', 'JSON Files (*.json);;All Files (*)')
        if not file_path:
            return
        self.update_current_category_data()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            QtWidgets.QMessageBox.information(self, 'Экспорт', 'Профиль успешно экспортирован!')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', f'Не удалось экспортировать профиль:\n{e}')

    def update_version_profile(self, data, ver):
        if "favcolor" not in data["settings"]["colors"]:
            data["settings"]["colors"]["favcolor"] = "#FF9000"

        if "fontsize" not in data["settings"]:
            data["settings"]["fontsize"] = "12"

        if "Прочее" not in data["content"]:
            data["content"]["Прочее"] = {
                "В планах": [],
                "В процессе": [],
                "Готово": []
            }
        data["ver"] = ver

    def import_json(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Импорт профиля из JSON', '', 'JSON Files (*.json);;All Files (*)')
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', f'Не удалось прочитать файл:\n{e}')
            return

        def check_structure(template, data):
            if isinstance(template, dict):
                if not isinstance(data, dict):
                    return False
                for key in template:
                    if key not in data:
                        return False
                    if isinstance(template[key], dict) and (not check_structure(template[key], data[key])):
                        return False
            return True

        if not check_structure(DEFAULT_DATA, imported_data):
            QtWidgets.QMessageBox.warning(self, 'Ошибка', 'Структура файла не совпадает с профилем MyMediaTracker.')
            return

        # Проверка версии профиля
        imported_ver = imported_data.get('ver')
        current_ver = DEFAULT_DATA['ver']
        if imported_ver != current_ver:
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle('Адаптация профиля')
            msg.setText(
                f"Версия профиля ({imported_ver}) не совпадает с версией программы ({current_ver}).\n"
                "Хотите адаптировать профиль к новой версии?"
            )
            msg.setIcon(QtWidgets.QMessageBox.Question)
            btn_yes = msg.addButton('Да', QtWidgets.QMessageBox.YesRole)
            btn_no = msg.addButton('Нет', QtWidgets.QMessageBox.NoRole)
            msg.exec_()
            if msg.clickedButton() == btn_yes:
                self.update_version_profile(self, imported_data, current_ver)
            elif msg.clickedButton() == btn_no:
                QtWidgets.QMessageBox.information(self, 'Импорт', 'Импорт отменён.')
                return

        reply = QtWidgets.QMessageBox.question(self, 'Импорт профиля', 'Импортировать этот профиль? Текущие данные будут заменены.', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes:
            return

        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(imported_data, f, ensure_ascii=False, indent=4)

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle('Перезапуск')
        msg.setText('Профиль успешно импортирован!\nДля применения изменений требуется перезапустить программу. Перезапустить сейчас?')
        msg.setIcon(QtWidgets.QMessageBox.Question)
        btn_yes = msg.addButton('Да', QtWidgets.QMessageBox.YesRole)
        btn_no = msg.addButton('Нет', QtWidgets.QMessageBox.NoRole)
        msg.exec_()
        if msg.clickedButton() == btn_yes:
            QtWidgets.qApp.quit()
            self.restart_application()
        else:
            QtWidgets.QMessageBox.information(self, 'Импорт', 'Изменения вступят в силу после перезапуска программы.')

    def update_favorite_colors(self):
        fav_color = self.data['settings']['colors'].get('favcolor', '#FF9000')
        normal_color = self.data['settings']['colors']['textborder']
        for lw in [self.listWidget, self.listWidget_2, self.listWidget_3]:
            for i in range(lw.count()):
                item = lw.item(i)
                if item.text().startswith('★ '):
                    item.setForeground(QColor(fav_color))
                else:
                    item.setForeground(QColor(normal_color))

    def open_context_menu(self, position):
        list_widget = self.sender()
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return

        menu = QMenu()
        edit_action = menu.addAction('Редактировать')
        delete_action = menu.addAction(f'Удалить ({len(selected_items)})')
        copy_action = menu.addAction(f'Копировать ({len(selected_items)})')
        move_menu = menu.addMenu('Переместить в')
        menu.addSeparator()
        is_favorite = any(item.text().startswith('★ ') for item in selected_items)
        if is_favorite:
            favorite_action = menu.addAction('Убрать из избранного')
        else:
            favorite_action = menu.addAction('Добавить в избранное')
        sort_action = menu.addAction('Сортировать по алфавиту')
        categories = self.data['settings']['visibleCategories']
        lists = ['В планах', 'В процессе', 'Готово']

        for cat in categories:
            if cat == self.current_category:
                continue
            cat_menu = move_menu.addMenu(cat)
            for lst_name in lists:
                cat_menu.addAction(lst_name)

        action = menu.exec_(list_widget.viewport().mapToGlobal(position))

        if action == delete_action:
            for item in selected_items:
                row = list_widget.row(item)
                list_widget.takeItem(row)

        elif action == copy_action:
            text_to_copy = '\n'.join([item.text() for item in selected_items])
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(text_to_copy)

        elif action == edit_action:
            item = selected_items[0]
            old_text = item.text()
            new_text = self.edit_item_dialog(old_text)
            if new_text and new_text.strip() and (new_text != old_text):
                item.setText(new_text.strip())
                self.update_current_category_data()

        if action == favorite_action:
            for item in selected_items:
                text = item.text()
                if is_favorite and text.startswith('★ '):
                    # Убрать звёздочку
                    item.setText(text[2:])
                elif not is_favorite and not text.startswith('★ '):
                    # Добавить звёздочку
                    item.setText('★ ' + text)
            self.update_current_category_data()
            return

        if action == sort_action:
            items = [list_widget.item(i).text() for i in range(list_widget.count())]
            favs = sorted([x for x in items if x.startswith('★ ')], key=lambda x: x.lower())
            non_favs = sorted([x for x in items if not x.startswith('★ ')], key=lambda x: x.lower())
            list_widget.clear()
            for text in favs + non_favs:
                list_widget.addItem(text)
            self.update_current_category_data()
            return

        elif action:
            parent_menu = action.parentWidget()
            if parent_menu and parent_menu.title() in categories and (action.text() in lists):
                target_category = parent_menu.title()
                target_list = action.text()
                for item in selected_items:
                    self.move_item_to_category(item.text(), target_category, target_list)
                    row = list_widget.row(item)
                    list_widget.takeItem(row)

    def move_item_to_category(self, item_text, target_category, target_list):
        self.update_current_category_data()
        self.data['content'].setdefault(target_category, {'В планах': [], 'В процессе': [], 'Готово': []})
        if item_text not in self.data['content'][target_category][target_list]:
            self.data['content'][target_category][target_list].append(item_text)
        if target_category == self.current_category:
            self.load_category(target_category)

    def import_from_txt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Выберите TXT файл', '', 'TXT Files (*.txt)')
        if not file_path:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('Импорт в список')
        main_layout = QVBoxLayout()
        list_combo = QComboBox()
        list_combo.addItems(['В планах', 'В процессе', 'Готово'])
        main_layout.addWidget(list_combo)
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton('OK')
        cancel_button = QPushButton('Отмена')
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        main_layout.addLayout(buttons_layout)
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        dialog.setLayout(main_layout)
        result = dialog.exec_()

        if result == QDialog.Rejected:
            return

        selected_list = list_combo.currentText()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', f'Не удалось прочитать файл: {e}')
            return

        if selected_list == 'В планах':
            list_widget = self.listWidget
        elif selected_list == 'В процессе':
            list_widget = self.listWidget_2
        elif selected_list == 'Готово':
            list_widget = self.listWidget_3
        else:
            QtWidgets.QMessageBox.warning(self, 'Ошибка', 'Не выбран список для импорта')
            return

        self.update_current_category_data()
        added_count = 0
        for line in lines:
            line = line.strip()
            if line:
                list_widget.addItem(line)
                if line not in self.data['content'][self.current_category][selected_list]:
                    self.data['content'][self.current_category][selected_list].append(line)
                added_count += 1
        self.load_category(self.current_category)
        QtWidgets.QMessageBox.information(self, 'Импорт', f"Импортировано {added_count} элементов в список '{selected_list}'")

class SettingsDialog(QtWidgets.QDialog):
    COLOR_LABELS = {'bg': 'Основной фон', 'bg2': 'Вторичный фон', 'textborder': 'Текст и рамки', 'activeobj': 'Активное', 'favcolor': 'Избранное'}

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Настройки')
        self.setModal(True)
        self.resize(420, 480)

        main_layout = QtWidgets.QVBoxLayout(self)
        flags = self.windowFlags()
        main_layout.addSpacing(20)
        color_title = QtWidgets.QLabel('Цвета интерфейса:')
        main_layout.addWidget(color_title)
        self.color_edits = {}
        colors = settings['settings']['colors']
        color_grid = QtWidgets.QGridLayout()
        color_grid.setHorizontalSpacing(8)
        color_grid.setVerticalSpacing(4)

        for row, (key, value) in enumerate(colors.items()):
            label = QtWidgets.QLabel(self.COLOR_LABELS.get(key, key))
            label.setMinimumWidth(80)
            edit = QtWidgets.QLineEdit(value)
            edit.setMaximumWidth(120)
            btn = QtWidgets.QPushButton('•')
            btn.setFixedWidth(40)
            color_grid.addWidget(label, row, 0)
            color_grid.addWidget(edit, row, 1)
            color_grid.addWidget(btn, row, 2)
            self.color_edits[key] = edit
            btn.clicked.connect(lambda _, e=edit: self.pick_color(e))

        main_layout.addLayout(color_grid)
        main_layout.addSpacing(20)

        cat_title = QtWidgets.QLabel('Видимые категории:')
        main_layout.addWidget(cat_title)
        self.category_buttons = {}
        all_categories = ['Фильмы', 'Сериалы', 'Игры', 'Аниме', 'Манга', 'Книги', 'Прочее']
        visible = set(settings['settings'].get('visibleCategories', all_categories))
        cat_widget = QtWidgets.QWidget()
        cat_layout = QtWidgets.QHBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(8)

        for cat in all_categories:
            btn = QtWidgets.QPushButton(cat)
            btn.setCheckable(True)
            btn.setChecked(cat in visible)
            btn.setMinimumWidth(90)
            btn.clicked.connect(self.on_category_button_toggled)
            cat_layout.addWidget(btn)
            self.category_buttons[cat] = btn

        main_layout.addWidget(cat_widget)
        self.on_category_button_toggled()
        main_layout.addSpacing(20)

        defcat_label = QtWidgets.QLabel('Категория по умолчанию при запуске:')
        main_layout.addWidget(defcat_label)
        self.default_cat_combo = QtWidgets.QComboBox()
        self.default_cat_combo.addItems([cat for cat in all_categories if self.category_buttons[cat].isChecked()])
        default_cat = settings['settings'].get('defaultCategory', all_categories[0])

        if default_cat in all_categories:
            self.default_cat_combo.setCurrentText(default_cat)

        main_layout.addWidget(self.default_cat_combo)

        for btn in self.category_buttons.values():
            btn.toggled.connect(self.update_default_cat_combo)

        main_layout.addSpacing(20)

        resolution_label = QtWidgets.QLabel('Разрешение окна программы при запуске:')
        main_layout.addWidget(resolution_label)
        self.resolution_combo = QtWidgets.QComboBox()
        resolutions = ['800 x 600', '1024 x 768', '1280 x 720', '1366 x 768', '1440 x 900', '1600 x 900', '1920 x 1080']
        self.resolution_combo.addItems(resolutions)
        current_res = settings['settings'].get('defaultResolution', '1024 x 768')
        index = self.resolution_combo.findText(current_res)

        if index != -1:
            self.resolution_combo.setCurrentIndex(index)
        else:
            self.resolution_combo.setCurrentIndex(1)

        main_layout.addWidget(self.resolution_combo)
        main_layout.addSpacing(20)

        other_title = QtWidgets.QLabel('Другие настройки:')
        main_layout.addWidget(other_title)
        self.autostart_btn = QtWidgets.QPushButton('Автозапуск')
        self.autostart_btn.setCheckable(True)
        self.autostart_btn.setChecked(settings['settings'].get('autostart', False))
        main_layout.addWidget(self.autostart_btn)
        main_layout.addSpacing(20)

        font_label = QtWidgets.QLabel('Размер шрифта:')
        main_layout.addWidget(font_label)
        self.font_combo = QtWidgets.QComboBox()
        self.font_combo.addItems(['Маленький', 'Средний', 'Большой'])
        font_size_map = {'Маленький': '12', 'Средний': '13', 'Большой': '14'}
        current_font_size = settings['settings'].get('fontsize', '12')
        for name, size in font_size_map.items():
            if size == current_font_size:
                self.font_combo.setCurrentText(name)
                break
        main_layout.addWidget(self.font_combo)
        main_layout.addSpacing(20)

        main_layout.addSpacing(40)
        footer_layout = QtWidgets.QHBoxLayout()
        version_label = QtWidgets.QLabel(f"Версия: {DEFAULT_DATA['ver']}")
        footer_layout.addWidget(version_label)
        self.link_btn = QtWidgets.QPushButton('Сайт автора')
        self.link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://app8ook.github.io')))
        footer_layout.addWidget(self.link_btn)
        footer_layout.addStretch()
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        btn_box.button(QtWidgets.QDialogButtonBox.Ok).setText('Применить')
        btn_box.button(QtWidgets.QDialogButtonBox.Cancel).setText('Отмена')

        footer_layout.addWidget(btn_box)
        main_layout.addLayout(footer_layout)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def on_category_button_toggled(self):
        checked = [btn for btn in self.category_buttons.values() if btn.isChecked()]
        if len(checked) == 1:
            checked[0].setEnabled(False)
        else:
            for btn in self.category_buttons.values():
                btn.setEnabled(True)

    def pick_color(self, edit):
        color = QtWidgets.QColorDialog.getColor(QColor(edit.text()), self)
        if color.isValid():
            edit.setText(color.name())

    def update_default_cat_combo(self):
        current = self.default_cat_combo.currentText()
        self.default_cat_combo.clear()
        visible = [cat for cat, chk in self.category_buttons.items() if chk.isChecked()]
        self.default_cat_combo.addItems(visible)
        if current in visible:
            self.default_cat_combo.setCurrentText(current)
        elif visible:
            self.default_cat_combo.setCurrentIndex(0)

    def get_settings(self):
        colors = {k: e.text() for k, e in self.color_edits.items()}
        visible = [cat for cat, btn in self.category_buttons.items() if btn.isChecked()]
        autostart = self.autostart_btn.isChecked()
        default_cat = self.default_cat_combo.currentText()
        default_resolution = self.resolution_combo.currentText()
        font_size_map = {'Маленький': '12', 'Средний': '13', 'Большой': '14'}
        fontsize = font_size_map[self.font_combo.currentText()]
        return {'colors': colors, 'visibleCategories': visible, 'autostart': autostart, 'defaultCategory': default_cat, 'defaultResolution': default_resolution, 'fontsize': fontsize}

def load_qss():
    data_path = user_data_path()
    colors = DEFAULT_DATA['settings']['colors']
    fontsize = DEFAULT_DATA['settings'].get('fontsize', '12')
    favcolor = colors.get('favcolor', '#FF9000')

    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            colors = data['settings']['colors']
            fontsize = data['settings'].get('fontsize', '12')
            favcolor = colors.get('favcolor', '#FF9000')

    with open(resource_path(STYLE_FILE), encoding='utf-8') as f:
        qss = f.read()

    qss_vars = dict(colors)
    qss_vars['fontsize'] = fontsize 
    qss_vars['favcolor'] = favcolor

    for key, value in qss_vars.items():
        qss = qss.replace(f'{{{key}}}', value)
    return qss

appconf = QtWidgets.QApplication(sys.argv)
appconf.setAttribute(Qt.AA_DisableWindowContextHelpButton)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(load_qss())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
