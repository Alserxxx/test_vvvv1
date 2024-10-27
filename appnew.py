import sqlite3
import threading
import multiprocessing
import requests
import logging
import csv
import random
import time
from collections import defaultdict # Добавьте эту строку в начало файла 

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QMessageBox, QInputDialog, QFileDialog, QMainWindow, QAction, QComboBox, QSpinBox, QTabWidget, QTextEdit, QMenu, QTableView, QSplitter
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QModelIndex, QTimer
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import QAbstractItemView

from PyQt5.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QTableWidgetItem, 
    QTableWidget, QAbstractItemView, QComboBox, QInputDialog, QMessageBox, QLabel, QProgressBar, 
    QTextEdit, QVBoxLayout
)
import threading
# Настройка логирования
#logging.basicConfig(filename='app.log', level=print, format='%(asctime)s - %(levelname)s - %(message)s')


import sqlite3
import logging
class DatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.conn = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_file)
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")


    def create_audience_table(self, conn, audience_name: str):
        try:
            c = conn.cursor()
            table_name = f"audience_{audience_name}"
            c.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audience_name TEXT NOT NULL,
                    total_audience_count INTEGER NOT NULL,
                    processed_audience_count INTEGER NOT NULL,
                    audience_date TEXT NOT NULL
                )
            """)
            conn.commit()
            print(f"Table '{table_name}' created.")
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")



    def add_column(self, table_name: str, column_name: str, column_type: str) -> None:
        """
        Добавляет новую колонку в таблицу.

        Args:
            table_name (str): Имя таблицы.
            column_name (str): Имя новой колонки.
            column_type (str): Тип данных новой колонки.
        """
        try:
            c = self.conn.cursor()
            c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            self.conn.commit()
            print(f"Колонка '{column_name}' добавлена в таблицу '{table_name}'.")
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении колонки '{column_name}': {e}")


    def create_table(self, table_name: str) -> None:
        """
        Создает таблицу в базе данных.

        Args:
            table_name (str): Имя таблицы.
        """
        try:
            c = self.conn.cursor()
            c.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    password TEXT,
                    ua TEXT,
                    cookie TEXT,
                    device TEXT,
                    status_account TEXT,
                    messages_total INTEGER,
                    messages_day INTEGER,
                    messages_run INTEGER,
                    color TEXT
                )
            """)
            self.conn.commit()
            print(f"Таблица '{table_name}' создана.")
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы: {e}")

    def add_account(self, table_name: str, account: dict) -> None:
        """
        Добавляет аккаунт в таблицу.

        Args:
            table_name (str): Имя таблицы.
            account (dict): Словарь с данными аккаунта.
        """
        try:
            c = self.conn.cursor()
            c.execute(f"""
                INSERT INTO '{table_name}' (username, password, ua, cookie, device, status_account, messages_total, messages_day, messages_run, color)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (account['username'], account['password'], account.get('ua', ''), account.get('cookie', ''), account.get('device', ''), 'Не проверено', 0, 0, 0, ''))
            self.conn.commit()
            print(f"Аккаунт '{account['username']}' добавлен в таблицу '{table_name}'.")
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении аккаунта: {e}")

    def get_accounts(self, table_name: str) -> list:
        """
        Получает список всех аккаунтов из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список словарей с данными аккаунтов.
        """
        try:
            c = self.conn.cursor()
            c.execute(f"SELECT * FROM '{table_name}'")
            rows = c.fetchall()
            accounts = [dict(zip([column[0] for column in c.description], row)) for row in rows]
            print(f"Список аккаунтов из таблицы '{table_name}' получен.")
            return accounts
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка аккаунтов: {e}")
            return []

    def update_account_status(self, table_name: str, account: dict):
        try:
            c = self.conn.cursor()
            # Проверка занятости аккаунта
            if account['status_account'] == 'В процессе':
                print(f"Аккаунт '{account['username']}' уже выполняет задачу.")
                return
            
            status = 'Валидный' if random.randint(1, 2) == 1 else 'Невалидный'
            color = 'lightgreen' if status == 'Валидный' else 'lightcoral'
            
            c.execute(f"UPDATE '{table_name}' SET status_account = ?, color = ? WHERE id = ?", (status, color, account['id']))
            self.conn.commit()
            print(f"Статус аккаунта '{account['username']}' обновлен в таблице '{table_name}'.")
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении статуса аккаунта: {e}")

    def delete_table(self, table_name: str) -> None:
        """
        Удаляет таблицу из базы данных.

        Args:
            table_name (str): Имя таблицы.
        """
        try:
            c = self.conn.cursor()
            c.execute(f"DROP TABLE '{table_name}'")
            self.conn.commit()
            print(f"Таблица '{table_name}' удалена.")
        except sqlite3.Error as e:
            print(f"Ошибка при удалении таблицы: {e}")

    def check_account_status(self, account: dict) -> str:
        """
        Проверяет статус аккаунта (временная функция).

        Args:
            account (dict): Словарь с данными аккаунта.

        Returns:
            str: Статус аккаунта ("Валидный" или "Невалидный").
        """
        status = "Валидный" if random.randint(1, 2) == 1 else "Невалидный"
        return status


    def get_audience_ids(self, table_name: str) -> list:
        """
        Получает список всех ID аудитории из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список ID аудитории.
        """
        try:
            c = self.conn.cursor()
            c.execute(f"SELECT id FROM '{table_name}'")
            rows = c.fetchall()
            audience_ids = [row[0] for row in rows]
            print(f"Список ID аудитории из таблицы '{table_name}' получен.")
            return audience_ids
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка ID аудитории: {e}")
            return []


    def add_audience_id(self, audience_id):
        try:
            c = self.conn.cursor()
            c.execute("INSERT INTO parsed_audience (audience_id) VALUES (?)", (audience_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error adding audience ID: {e}")

    def get_unused_audience_ids(self):
        try:
            c = self.conn.cursor()
            c.execute("SELECT audience_id FROM parsed_audience WHERE used = 0")
            return [row[0] for row in c.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error retrieving audience IDs: {e}")
            return []

    def mark_audience_id_as_used(self, audience_id):
        try:
            c = self.conn.cursor()
            c.execute("UPDATE parsed_audience SET used = 1 WHERE audience_id = ?", (audience_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error marking audience ID as used: {e}")


        
    def create_parsed_audience_table(self) -> None:
        try:
            c = self.conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS parsed_audience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audience_name TEXT NOT NULL,
                    total_audience_count INTEGER NOT NULL,
                    processed_audience_count INTEGER NOT NULL,
                    audience_date TEXT NOT NULL
                )
            """)
            self.conn.commit()
            print("Таблица 'parsed_audience' создана.")
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы: {e}")


class AudienceParser:
    def __init__(self, db_file: str):
        self.db_file = db_file

    def save_parsed_audience(self, conn, audience_name: str, total_audience_count: int, processed_audience_count: int, audience_date: str) -> None:
        try:
            c = conn.cursor()
            table_name = f"audience_{audience_name}"
            c.execute(f"""
                INSERT INTO {table_name} (audience_name, total_audience_count, processed_audience_count, audience_date)
                VALUES (?, ?, ?, ?)
            """, (audience_name, total_audience_count, processed_audience_count, audience_date))
            conn.commit()
            print(f"Audience data '{audience_name}' saved.")
        except sqlite3.Error as e:
            print(f"Error saving audience data: {e}")

class ParsedAudienceTable(QTableWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Название аудитории", "Кол-во аудитории всего", "Кол-во пройденной аудитории", "Дата аудитории"])
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.update_table()

    def update_table(self):
        self.setRowCount(0)
        conn = self.db_manager.connect()
        if conn:
            c = conn.cursor()
            c.execute("SELECT audience_name, total_audience_count, processed_audience_count, audience_date FROM parsed_audience")
            rows = c.fetchall()
            for i, row in enumerate(rows):
                self.insertRow(i)
                for j, value in enumerate(row):
                    self.setItem(i, j, QTableWidgetItem(str(value)))
            conn.close()


class AudienceTable(QTableWidget):
    def __init__(self, db_manager: DatabaseManager, audience_name: str):
        super().__init__()
        self.db_manager = db_manager
        self.audience_name = audience_name
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Audience Name", "Total Count", "Processed Count"])
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.update_table()

    def update_table(self):
        self.setRowCount(0)
        c = self.db_manager.conn.cursor()
        table_name = f"{self.audience_name}"
        c.execute(f"SELECT audience_name, total_audience_count, processed_audience_count FROM {table_name}")
        rows = c.fetchall()
        for i, row in enumerate(rows):
            self.insertRow(i)
            for j, value in enumerate(row):
                self.setItem(i, j, QTableWidgetItem(str(value)))








class AccountManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager


    def create_task_with_custom_name(self):
        audience_name, ok = QInputDialog.getText(None, "Создание группы", "Введите имя группы:")
        if ok:
            if audience_name:
                if not audience_name.isalnum():
                    QMessageBox.warning(None, "Ошибка", "Имя группы должно состоять из букв и цифр.")
                    return
                self.db_manager.create_audience_table(audience_name)
                # Immediately update the table to reflect the new group
                parsed_audience_table = ParsedAudienceTable(self.db_manager)
                parsed_audience_table.update_table()
            else:
                QMessageBox.warning(None, "Ошибка", "Введите имя группы.")

   

    def add_account(self, table_name: str, account: dict) -> None:
        """
        Добавляет аккаунт в таблицу.

        Args:
            table_name (str): Имя таблицы.
            account (dict): Словарь с данными аккаунта.
        """
        self.db_manager.add_account(table_name, account)

    def get_accounts(self, table_name: str) -> list:
        """
        Получает список всех аккаунтов из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список словарей с данными аккаунтов.
        """
        return self.db_manager.get_accounts(table_name)


    def update_account_status(self, table_name: str, account: dict):
        try:
            c = self.db_manager.conn.cursor()
            # Проверка занятости аккаунта
            if account['status_account'] == 'В процессе':
                logging.info(f"Аккаунт '{account['username']}' уже выполняет задачу.")
                return
            
            status = 'Валидный' if random.randint(1, 2) == 1 else 'Невалидный'
            color = 'lightgreen' if status == 'Валидный' else 'lightcoral'
            
            c.execute(f"UPDATE '{table_name}' SET status_account = ?, color = ? WHERE id = ?", (status, color, account['id']))
            self.db_manager.conn.commit()
            logging.info(f"Статус аккаунта '{account['username']}' обновлен в таблице '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении статуса аккаунта: {e}")

    def update_account_messages(self, table_name: str, account_id: int, messages_run: int):
        """
        Обновляет счетчик сообщений в базе данных.

        Args:
            table_name (str): Имя таблицы.
            account_id (int): ID аккаунта.
            messages_run (int): Количество сообщений для добавления.
        """
        try:
            c = self.db_manager.conn.cursor()
            c.execute(f"""
                UPDATE '{table_name}'
                SET messages_run = messages_run + ?,
                    messages_total = messages_total + ?
                WHERE id = ?
            """, (messages_run, messages_run, account_id))
            self.db_manager.conn.commit()
            print(f"Счетчик сообщений для аккаунта '{account_id}' обновлен.")
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении счетчика сообщений: {e}")

class TaskManager:
    def __init__(self, db_file, account_manager, settings):
        self.db_file = db_file
        self.account_manager = account_manager
        self.settings = settings

    def run_task(self, accounts: list, task_type: str, table_name: str):
        db_manager = DatabaseManager(self.db_file)
        db_manager.connect()
        account_manager = AccountManager(db_manager)

        if task_type == "Проверка валидности":
            for account in accounts:
                account_manager.update_account_status(table_name, account)
        elif task_type == "Парсинг аудитории":
            self.parse_audience(db_manager, accounts)
        elif task_type == "Рассылка сообщений":
            self.send_messages(db_manager, account_manager, accounts)

    def parse_audience(self, db_manager: DatabaseManager, accounts: list):
        for _ in range(len(accounts)):
            audience_id = random.randint(10000, 100000)
            db_manager.add_audience_id(audience_id)
            time.sleep(0.01)

    def send_messages(self, db_manager: DatabaseManager, account_manager: AccountManager, accounts: list):
        for account in accounts:
            unused_audience_ids = db_manager.get_unused_audience_ids()
            if unused_audience_ids:
                audience_id = random.choice(unused_audience_ids)
                db_manager.mark_audience_id_as_used(audience_id)
                account_manager.update_account_messages(account['id'], 1)
                time.sleep(0.01)

class AccountTable(QTableWidget, QTableView):
    def __init__(self, db_manager: DatabaseManager, table_name: str):
        super().__init__()
        self.db_manager = db_manager
        self.table_name = table_name
        self.setColumnCount(10)
        self.setHorizontalHeaderLabels(["Имя пользователя", "Пароль", "UA", "Cookie", "Device", "Статус", "Сообщ. всего", "Сообщ. день", "Сообщ. запуск", " "])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.update_table()
        self.itemClicked.connect(self.handle_item_clicked)


    def update_table(self):
        self.db_manager.connect()
        self.setRowCount(0)
        accounts = self.db_manager.get_accounts(table_name)
        for i, account in enumerate(accounts):
            self.insertRow(i)
            self.setItem(i, 0, QTableWidgetItem(account['username']))
            self.setItem(i, 1, QTableWidgetItem(account['password']))
            self.setItem(i, 2, QTableWidgetItem(account['ua']))
            self.setItem(i, 3, QTableWidgetItem(account['cookie']))
            self.setItem(i, 4, QTableWidgetItem(account['device']))
            self.setItem(i, 5, QTableWidgetItem(account['status_account']))
            self.setItem(i, 6, QTableWidgetItem(str(account['messages_total'])))
            self.setItem(i, 7, QTableWidgetItem(str(account['messages_day'])))
            self.setItem(i, 8, QTableWidgetItem(str(account['messages_run'])))
            self.setItem(i, 9, QTableWidgetItem(""))

            # Установка цвета строки
            color = account['color']
            if color:
                for j in range(10):
                    self.item(i, j).setBackground(QColor(color))

    def select_rows_with_shift(self, key):
        """
        Выделение строк с зажатым Shift.
        """
        current_row = self.currentRow()
        if key == Qt.Key_Up:
            if current_row > 0:
                self.selectRow(current_row - 1)
                self.setCurrentCell(current_row - 1, 0)
        elif key == Qt.Key_Down:
            if current_row < self.rowCount() - 1:
                self.selectRow(current_row + 1)
                self.setCurrentCell(current_row + 1, 0)

    def select_rows_with_ctrl(self, key):
        """
        Выделение/снятие выделения строк с зажатым Ctrl.
        """
        current_row = self.currentRow()
        if key == Qt.Key_Up:
            if current_row > 0:
                if self.isRowSelected(current_row - 1):
                    self.removeRowSelection(current_row - 1)
                else:
                    self.selectRow(current_row - 1)
        elif key == Qt.Key_Down:
            if current_row < self.rowCount() - 1:
                if self.isRowSelected(current_row + 1):
                    self.removeRowSelection(current_row + 1)
                else:
                    self.selectRow(current_row + 1)



    def contextMenuEvent(self, event):
        """
        Отображает контекстное меню при правом клике по выделенным строкам.
        """
        menu = QMenu(self)
        delete_action = QAction("Удалить строки", self)
        delete_action.triggered.connect(self.delete_selected_rows)
        menu.addAction(delete_action)
        menu.exec_(event.globalPos())

    def delete_selected_rows(self):
        """
        Удаляет выделенные строки из таблицы и базы данных.
        """
        selected_rows = self.selectionModel().selectedRows()
        selected_row_ids = [row.row() for row in selected_rows]

        # Подтверждение удаления
        reply = QMessageBox.question(self, "Удаление строк", f"Вы уверены, что хотите удалить {len(selected_rows)} строк?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Удаление из базы данных
            for row_id in selected_row_ids:
                try:
                    # Получаем id из базы данных для соответствующей строки
                    c = self.db_manager.conn.cursor()
                    c.execute(f"SELECT id FROM '{self.table_name}' LIMIT 1 OFFSET ?", (row_id,))
                    db_row_id = c.fetchone()
                    if db_row_id:
                        c.execute(f"DELETE FROM '{self.table_name}' WHERE id = ?", (db_row_id[0],))
                        self.db_manager.conn.commit()
                        print(f"Строка с id {db_row_id[0]} удалена из таблицы '{self.table_name}'.")
                except sqlite3.Error as e:
                    print(f"Ошибка при удалении строки: {e}")

            # Удаление из таблицы
            for row_id in sorted(selected_row_ids, reverse=True):
                self.removeRow(row_id)

    def handle_item_clicked(self, item: QTableWidgetItem):
        row = self.row(item)
        print(row)

        self.selectRow(row)


class TaskWindow(QWidget):
    def __init__(self, main_window, table_name: str, task_type: str, audience_name: str):
        super().__init__()
        self.setWindowTitle(f"Задача: {task_type}")
        self.main_window = main_window
        self.table_name = table_name
        self.task_type = task_type
        self.audience_name = audience_name
        self.stop_flag = False

        # UI Elements
        self.status_label = QLabel("Статус: Ожидание")
        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_task)
        self.progress_bar = QProgressBar()

        if task_type == "Парсинг аудитории":
            self.save_audience_button = QPushButton("Сохранить аудиторию")
            self.save_audience_button.clicked.connect(self.save_audience)
            self.audience_label = QLabel("Аудитория:")
            self.audience_list = QTextEdit()
            self.audience_list.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Задача: {task_type} для таблицы '{table_name}'"))
        layout.addWidget(self.status_label)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.progress_bar)

        if task_type == "Парсинг аудитории":
            layout.addWidget(self.audience_label)
            layout.addWidget(self.audience_list)
            layout.addWidget(self.save_audience_button)

        self.setLayout(layout)

        # Start the task in a separate thread
        self.thread = threading.Thread(target=self.run_task)
        self.thread.start()

    def run_task(self):
        self.status_label.setText("Статус: Выполняется")
        self.main_window.db_manager.connect()

        accounts = self.main_window.account_manager.get_accounts(self.table_name)
        self.progress_bar.setMaximum(len(accounts))
        for i, account in enumerate(accounts):
            if self.stop_flag:
                break

            if self.task_type == "Проверка валидности":
                self.main_window.account_manager.update_account_status(self.table_name, account)
                self.main_window.tab_widget.currentWidget().update_table(self.table_name)
                self.progress_bar.setValue(i + 1)
            elif self.task_type == "Парсинг аудитории":
                self.main_window.task_manager.parse_audience(self.main_window.db_manager, [account])
                self.audience_list.setText("\n".join(str(id) for id in self.main_window.db_manager.get_unused_audience_ids()))
                self.progress_bar.setValue(i + 1)
            elif self.task_type == "Рассылка сообщений":
                self.main_window.task_manager.send_messages(self.main_window.db_manager, self.main_window.account_manager, [account])
                self.main_window.tab_widget.currentWidget().update_table(self.table_name)
                self.progress_bar.setValue(i + 1)

        if self.stop_flag:
            self.status_label.setText("Статус: Остановлено")
        else:
            self.status_label.setText("Статус: Завершено")

    def stop_task(self):
        self.stop_flag = True

    def save_audience(self):
        filename, ok = QFileDialog.getSaveFileName(self, "Сохранить аудиторию", "", "Text Files (*.txt)")
        if ok and filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.audience_list.toPlainText())
            logging.info(f"Аудитория сохранена в файл '{filename}'.")


    def save_audience_to_file(self, audience: list, filename: str):
        """
        Сохраняет аудиторию в файл.

        Args:
            audience (list): Список ID аудитории.
            filename (str): Имя файла.
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for id in audience:
                    f.write(str(id) + '\n')
            print(f"Аудитория сохранена в файл '{filename}'.")
        except Exception as e:
            print(f"Ошибка при сохранении аудитории в файл: {e}")


class SettingsWindow(QWidget):
    """
    Класс для представления окна настроек.
    """

    def __init__(self, settings: dict):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.settings = settings

        # Создание элементов интерфейса для настроек (например, поля ввода для прокси, спинтаксов и т.д.)
        self.proxy_input = QLineEdit()
        self.spintax_input = QLineEdit()
        self.settings_label = QLabel("Настройки будут сохранены при следующем запуске приложения")

        # Создание компоновки
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Прокси:"))
        layout.addWidget(self.proxy_input)
        layout.addWidget(QLabel("Спинтаксы:"))
        layout.addWidget(self.spintax_input)
        layout.addWidget(self.settings_label)

        self.setLayout(layout)

        # Сохранение настроек
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        # Загрузка текущих настроек
        self.proxy_input.setText(self.settings.get('proxy', ''))
        self.spintax_input.setText(self.settings.get('spintax', ''))

    def save_settings(self):
        """
        Сохраняет настройки.
        """
        proxy = self.proxy_input.text()
        spintax = self.spintax_input.text()

        self.settings['proxy'] = proxy
        self.settings['spintax'] = spintax

        # ... (реализация сохранения настроек, например, в файл конфигурации)

        QMessageBox.information(self, "Сохранение настроек", "Настройки сохранены.")





class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление аккаунтами")
        self.db_manager = DatabaseManager('accounts.db')
        self.db_manager.connect()
        self.account_manager = AccountManager(self.db_manager)
        self.settings = {}
        self.current_table = None
        self.available_tables = []

        self.task_manager = TaskManager('accounts.db', self.account_manager, self.settings)

        # Initialize UI components
        self.initUI()

    def initUI(self):
        self.create_table_button = QPushButton("Создать таблицу")
        self.load_accounts_button = QPushButton("Загрузить аккаунты")
        self.start_task_button = QPushButton("Запустить задачу")
        self.task_select = QComboBox()
        self.task_select.addItems(["Проверка валидности", "Парсинг аудитории", "Рассылка сообщений"])

        # Create Splitter
        self.splitter = QSplitter()

        # Create tabs for account tables
        self.tab_widget = QTabWidget()
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_table_context_menu)

        # Placeholder for audience table
        self.audience_table = QTableWidget()
        self.audience_table.setColumnCount(4)
        self.audience_table.setHorizontalHeaderLabels(["Название аудитории", "Кол-во аудитории всего", "Кол-во пройденной аудитории", "Дата аудитории"])
        self.audience_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.audience_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.audience_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Add widgets to splitter
        self.splitter.addWidget(self.tab_widget)
        self.splitter.addWidget(self.audience_table)

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.create_table_button)
        button_layout.addWidget(self.load_accounts_button)
        button_layout.addWidget(self.start_task_button)
        button_layout.addWidget(self.task_select)
        main_layout.addWidget(self.splitter)
        main_layout.addLayout(button_layout)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.create_table_button.clicked.connect(self.show_create_table_dialog)
        self.load_accounts_button.clicked.connect(self.load_accounts)
        self.start_task_button.clicked.connect(self.start_task_with_group_name)

        self.load_tables_from_database()
        self.show()

    def start_task_with_group_name(self):
        audience_name, ok = QInputDialog.getText(self, "Название группы", "Введите название группы:")
        if ok and audience_name:
            if not audience_name.isalnum():
                QMessageBox.warning(self, "Ошибка", "Название группы должно состоять из букв и цифр.")
                return
            task_type = self.task_select.currentText()
            task_window = TaskWindow(self, self.current_table, task_type, audience_name)
            task_window.show()

    def send_selected_to_task_thread(self, accounts, task_type, table_name):
        """
        Отправляет выделенные аккаунты в задачу в отдельном потоке.
        """
        thread = threading.Thread(target=self.run_task, args=(accounts, task_type, table_name))
        thread.start()

    def run_task(self, accounts, task_type, table_name):
        """
        Обработка задачи (в отдельном потоке).
        """
        self.task_manager.run_task(accounts, task_type, table_name)
    def show_create_table_dialog(self):
        table_name, ok = QInputDialog.getText(self, "Создание таблицы", "Введите имя таблицы:")
        if ok and table_name:
            if not table_name.isalnum():
                QMessageBox.warning(self, "Ошибка", "Имя таблицы должно состоять из букв и цифр.")
                return
            self.db_manager.create_table(table_name)
            self.available_tables.append(table_name)
            self.account_table = QTableWidget()
            self.tab_widget.addTab(self.account_table, table_name)
            self.current_table = table_name
        else:
            QMessageBox.warning(self, "Ошибка", "Введите имя таблицы.")


    def load_accounts(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить аккаунты", "", "All Files (*)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.account_manager.add_account(self.current_table, row)
            self.tab_widget.currentWidget().update_table()

    def send_selected_to_task(self):
        """
        Отправляет выделенные аккаунты в задачу.
        """
        selected_rows = self.tab_widget.currentWidget().selectionModel().selectedRows()
        selected_row_ids = [row.row() for row in selected_rows]

        # Подтверждение отправки
        selected_task = self.task_select.currentText()
        reply = QMessageBox.question(self, "Отправка в задачу",
                                    f"Вы уверены, что хотите отправить {len(selected_rows)} строк в задачу '{selected_task}'?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Получаем данные аккаунтов из базы данных
            accounts = self.account_manager.get_accounts(self.tab_widget.currentWidget().table_name)
            selected_accounts = [accounts[row_id] for row_id in selected_row_ids]
            self.send_selected_to_task_thread(selected_accounts, selected_task, self.tab_widget.currentWidget().table_name)



    def show_settings(self):
        """
        Отображает окно настроек.
        """
        settings_window = SettingsWindow(self.settings)
        settings_window.show()

    def fill_table_with_data(self):
        """
        Заполняет таблицу сгенерированными данными.
        """
        print("Кнопка 'Заполнить таблицу' нажата")  # Логирование

        # Обновляем self.current_table
        self.current_table = self.tab_widget.currentWidget().table_name  # Получаем имя текущей таблицы

        if self.tab_widget.currentWidget().rowCount() > 0:
            reply = QMessageBox.question(self, "Предупреждение", "Таблица уже содержит данные. Вы уверены, что хотите заполнить ее заново?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        row_count = random.randint(50, 500)
        for _ in range(row_count):
            self.account_manager.add_account(self.current_table, {
                'username': f'user_{random.randint(1, 1000)}',
                'password': f'pass_{random.randint(1, 1000)}',
                'ua': f'UA_{random.randint(1, 1000)}',
                'cookie': f'cookie_{random.randint(1, 1000)}',
                'device': f'device_{random.randint(1, 1000)}'
            })
        # Обновляем только текущую таблицу
        self.tab_widget.currentWidget().update_table(self.current_table)
        # Перерисовываем QTabWidget, чтобы изменения стали видны
        self.tab_widget.currentWidget().repaint()


    def load_tables_from_database(self):
        try:
            c = self.db_manager.conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall() if row[0] != 'sqlite_sequence']
            for table_name in tables:
                if table_name not in self.available_tables:
                    self.available_tables.append(table_name)
                    self.account_table = QTableWidget()
                    self.tab_widget.addTab(self.account_table, table_name)
        except sqlite3.Error as e:
            logging.error(f"Ошибка при загрузке таблиц из базы данных: {e}")

    def show_table_context_menu(self, point):
        """
        Отображает контекстное меню для таблицы.
        """
        menu = QMenu(self)

        # Действие для удаления таблицы
        delete_action = QAction("Удалить таблицу", self)
        delete_action.triggered.connect(self.delete_table)
        menu.addAction(delete_action)

        menu.exec_(self.tab_widget.mapToGlobal(point))

    def delete_table(self):
        """
        Удаляет таблицу из базы данных и интерфейса.
        """
        current_index = self.tab_widget.currentIndex()
        table_name = self.tab_widget.tabText(current_index)

        # Подтверждение удаления
        reply = QMessageBox.question(self, "Удаление таблицы", f"Вы уверены, что хотите удалить таблицу '{table_name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_manager.delete_table(table_name)
            self.tab_widget.removeTab(current_index)
            self.available_tables.remove(table_name)
            self.current_table = None  # Обновляем текущую таблицу, если она была удалена
            print(f"Таблица '{table_name}' удалена.")
        else:
            print(f"Удаление таблицы '{table_name}' отменено.")

    def load_settings(self):
        """
        Загружает настройки из файла (реализуйте свою логику загрузки).
        """
        try:
            with open('settings.txt', 'r') as f:
                for line in f:
                    key, value = line.strip().split("=", 1)
                    self.settings[key] = value
            print("Настройки загружены.")
        except FileNotFoundError:
            print("Файл настроек не найден. Используются стандартные настройки.")

    def save_settings(self):
        """
        Сохраняет настройки в файл (реализуйте свою логику сохранения).
        """
        try:
            with open('settings.txt', 'w') as f:
                for key, value in self.settings.items():
                    f.write(f"{key}={value}\n")
            print("Настройки сохранены.")
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")



def ensure_parsed_audience_table_exists(db_file: str):
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table' AND name='parsed_audience';
        """)
        if c.fetchone() is None:
            c.execute("""
                CREATE TABLE parsed_audience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audience_name TEXT NOT NULL,
                    total_audience_count INTEGER NOT NULL,
                    processed_audience_count INTEGER NOT NULL,
                    audience_date TEXT NOT NULL
                )
            """)
            conn.commit()
            logging.info("Table 'parsed_audience' created.")
        else:
            logging.info("Table 'parsed_audience' already exists.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ensure_parsed_audience_table_exists('accounts.db')
    app = QApplication([])
    main_window = MainWindow()
    app.exec_()
