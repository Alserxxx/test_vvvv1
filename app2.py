import sqlite3
import threading
import multiprocessing
import requests
import logging
import csv
import random
import time
from collections import defaultdict

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QMessageBox, QInputDialog, QFileDialog, QMainWindow, QAction, QComboBox, QSpinBox, QTabWidget, QTextEdit, QMenu, QProgressBar, QGridLayout, QGroupBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QModelIndex, QTimer, QSize
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import QAbstractItemView

# Настройка логирования
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Application(QMainWindow):
    """
    Класс для управления приложением.
    """

    def __init__(self):
        """
        Инициализация приложения.
        """
        super().__init__()
        self.setWindowTitle("Управление аккаунтами")
        self.db_conn = None  # Подключение к базе данных
        self.db_file = 'accounts.db'
        self.connect_to_db()
        self.settings = defaultdict(lambda: None)  # Словарь для хранения настроек
        self.current_table = None  # Имя текущей таблицы
        self.available_tables = []  # Список доступных таблиц
        self.tasks_history = []  # История выполненных задач

        # Создание UI элементов
        self.create_table_button = QPushButton("Создать таблицу")
        self.load_accounts_button = QPushButton("Загрузить аккаунты")
        self.start_task_button = QPushButton("Запустить задачу")
        self.task_select = QComboBox()
        self.task_select.addItems(["Проверка валидности", "Парсинг аудитории", "Рассылка сообщений"])
        self.fill_table_button = QPushButton("Заполнить таблицу")
        self.fill_table_button.clicked.connect(self.fill_table_with_data)
        self.tab_widget = QTabWidget()
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_table_context_menu)

        # Таблица для отображения истории задач
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(3)
        self.tasks_table.setHorizontalHeaderLabels(["Задача", "Дата", "Статус"])
        self.update_tasks_table()

        # Таблица для отображения статистики по аккаунтам
        self.accounts_stats_table = QTableWidget()
        self.accounts_stats_table.setColumnCount(3)
        self.accounts_stats_table.setHorizontalHeaderLabels(["Аккаунт", "Всего сообщений", "Последняя отправка"])
        self.update_accounts_stats_table()

        # Создание центрального виджета
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.create_table_button)
        button_layout.addWidget(self.load_accounts_button)
        button_layout.addWidget(self.task_select)
        button_layout.addWidget(self.start_task_button)
        button_layout.addWidget(self.fill_table_button)
        main_layout.addWidget(self.tab_widget)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.tasks_table)
        main_layout.addWidget(self.accounts_stats_table)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Создание и показ главного окна
        self.show()

        # Подключение действий к кнопкам и меню
        self.create_table_button.clicked.connect(self.show_create_table_dialog)
        self.load_accounts_button.clicked.connect(self.load_accounts)
        self.start_task_button.clicked.connect(self.send_selected_to_task)
        self.fill_table_button.clicked.connect(self.fill_table_with_data)

        # Загрузка таблиц и настроек при запуске
        self.load_tables_from_database()
        self.load_settings()

    def connect_to_db(self) -> None:
        """
        Создает подключение к базе данных SQLite.
        """
        try:
            self.db_conn = sqlite3.connect(self.db_file)
            logging.info(f"Соединение с базой данных '{self.db_file}' установлено.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при подключении к базе данных: {e}")

    def create_table(self, table_name: str) -> None:
        """
        Создает таблицу в базе данных.

        Args:
            table_name (str): Имя таблицы.
        """
        try:
            c = self.db_conn.cursor()
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
            self.db_conn.commit()
            logging.info(f"Таблица '{table_name}' создана.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")

    def create_audience_table(self, table_name: str) -> None:
        """
        Создает таблицу для аудитории в базе данных.

        Args:
            table_name (str): Имя таблицы.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audience_id INTEGER UNIQUE,
                    used INTEGER DEFAULT 0
                )
            """)
            self.db_conn.commit()
            logging.info(f"Таблица '{table_name}' для аудитории создана.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы для аудитории: {e}")

    def add_account(self, table_name: str, account: dict) -> None:
        """
        Добавляет аккаунт в таблицу.

        Args:
            table_name (str): Имя таблицы.
            account (dict): Словарь с данными аккаунта.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                INSERT INTO '{table_name}' (username, password, ua, cookie, device, status_account, messages_total, messages_day, messages_run, color)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (account['username'], account['password'], account.get('ua', ''), account.get('cookie', ''), account.get('device', ''), 'Не проверено', 0, 0, 0, ''))
            self.db_conn.commit()
            logging.info(f"Аккаунт '{account['username']}' добавлен в таблицу '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении аккаунта: {e}")

    def get_accounts(self, table_name: str) -> list:
        """
        Получает список всех аккаунтов из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список словарей с данными аккаунтов.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"SELECT * FROM '{table_name}'")
            rows = c.fetchall()
            accounts = [dict(zip([column[0] for column in c.description], row)) for row in rows]
            logging.info(f"Список аккаунтов из таблицы '{table_name}' получен.")
            return accounts
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении списка аккаунтов: {e}")
            return []

    def update_account_status(self, table_name: str, account: dict):
        """
        Обновляет статус аккаунта в базе данных.

        Args:
            table_name (str): Имя таблицы.
            account (dict): Словарь с данными аккаунта.
        """
        try:
            c = self.db_conn.cursor()
            status = self.check_account_status(account)
            color = 'green' if status == "Валидный" else 'red'
            c.execute(f"""
                UPDATE '{table_name}'
                SET status_account = ?, color = ?
                WHERE id = ?
            """, (status, color, account['id']))
            self.db_conn.commit()
            logging.info(f"Статус аккаунта '{account['username']}' обновлен в таблице '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении статуса аккаунта: {e}")

    def delete_table(self, table_name: str) -> None:
        """
        Удаляет таблицу из базы данных.

        Args:
            table_name (str): Имя таблицы.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"DROP TABLE '{table_name}'")
            self.db_conn.commit()
            logging.info(f"Таблица '{table_name}' удалена.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении таблицы: {e}")

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

    def add_audience_id(self, table_name: str, audience_id: int) -> None:
        """
        Добавляет ID аудитории в таблицу.

        Args:
            table_name (str): Имя таблицы.
            audience_id (int): ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                INSERT OR IGNORE INTO '{table_name}' (audience_id)
                VALUES (?)
            """, (audience_id,))
            self.db_conn.commit()
            logging.info(f"ID аудитории '{audience_id}' добавлен в таблицу '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении ID аудитории: {e}")

    def get_audience_ids(self, table_name: str) -> list:
        """
        Получает список всех ID аудитории из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"SELECT audience_id FROM '{table_name}'")
            rows = c.fetchall()
            audience_ids = [row[0] for row in rows]
            logging.info(f"Список ID аудитории из таблицы '{table_name}' получен.")
            return audience_ids
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении списка ID аудитории: {e}")
            return []

    def mark_audience_id_as_used(self, table_name: str, audience_id: int) -> None:
        """
        Помечает ID аудитории как использованный.

        Args:
            table_name (str): Имя таблицы.
            audience_id (int): ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                UPDATE '{table_name}'
                SET used = 1
                WHERE audience_id = ?
            """, (audience_id,))
            self.db_conn.commit()
            logging.info(f"ID аудитории '{audience_id}' помечен как использованный в таблице '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при пометке ID аудитории как использованный: {e}")

    def get_unused_audience_ids(self, table_name: str) -> list:
        """
        Получает список всех неиспользованных ID аудитории из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список неиспользованных ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"SELECT audience_id FROM '{table_name}' WHERE used = 0")
            rows = c.fetchall()
            audience_ids = [row[0] for row in rows]
            logging.info(f"Список неиспользованных ID аудитории из таблицы '{table_name}' получен.")
            return audience_ids
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении списка неиспользованных ID аудитории: {e}")
            return []

    def update_account_messages(self, table_name: str, account_id: int, messages_run: int):
        """
        Обновляет счетчик сообщений в базе данных.

        Args:
            table_name (str): Имя таблицы.
            account_id (int): ID аккаунта.
            messages_run (int): Количество сообщений для добавления.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                UPDATE '{table_name}'
                SET messages_run = messages_run + ?,
                    messages_total = messages_total + ?
                WHERE id = ?
            """, (messages_run, messages_run, account_id))
            self.db_conn.commit()
            logging.info(f"Счетчик сообщений для аккаунта '{account_id}' обновлен.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении счетчика сообщений: {e}")

    def show_create_table_dialog(self):
        """
        Отображает диалоговое окно для создания новой таблицы.
        """
        table_name, ok = QInputDialog.getText(self, "Создание таблицы", "Введите имя таблицы:")
        if ok:
            if table_name:
                if not table_name.isalnum():
                    QMessageBox.warning(self, "Ошибка", "Имя таблицы должно состоять из букв и цифр.")
                    return
                self.create_table(table_name)
                self.create_audience_table(f"{table_name}_audience")
                self.available_tables.append(table_name)  # Добавляем таблицу в список
                self.current_table = table_name  # Обновляем текущую таблицу
                self.account_table = AccountTable(self, table_name)  # Создаем новую таблицу
                self.tab_widget.addTab(self.account_table, table_name)  # Добавляем вкладку с новой таблицей
                self.tab_widget.setCurrentWidget(self.account_table)  # Переключаемся на новую вкладку
                logging.info(f"Таблица '{table_name}' создана.")
            else:
                QMessageBox.warning(self, "Ошибка", "Введите имя таблицы.")
        else:
            logging.info("Создание таблицы отменено.")

    def load_accounts(self):
        """
        Загружает аккаунты из файла.
        """
        file_path, ok = QFileDialog.getOpenFileName(self, "Загрузить аккаунты", "", "All Files (*)")
        if ok:
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            self.add_account(self.current_table, row)
                            # Обновляем таблицу в UI
                            self.tab_widget.currentWidget().update_table(self.current_table)
                except Exception as e:
                    logging.error(f"Ошибка при загрузке аккаунтов: {e}")
                    QMessageBox.warning(self, "Ошибка", f"Ошибка при загрузке аккаунтов: {e}")
            else:
                logging.info("Загрузка аккаунтов отменена.")
        else:
            logging.info("Загрузка аккаунтов отменена.")

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
            accounts = self.get_accounts(self.current_table)
            selected_accounts = [accounts[row_id] for row_id in selected_row_ids]
            self.run_task(selected_accounts, selected_task, self.current_table)

    def run_task(self, accounts, task_type, table_name):
        """
        Обработка задачи (в отдельном потоке).
        """
        task_start_time = time.time()
        task_status = "Успешно"
        try:
            if task_type == "Проверка валидности":
                for account in accounts:
                    self.update_account_status(table_name, account)
            elif task_type == "Парсинг аудитории":
                self.parse_audience(table_name, accounts)
            elif task_type == "Рассылка сообщений":
                self.send_messages(table_name, accounts)
        except Exception as e:
            task_status = f"Ошибка: {e}"
            logging.error(f"Ошибка при выполнении задачи '{task_type}': {e}")

        task_end_time = time.time()
        task_duration = round(task_end_time - task_start_time, 2)

        self.tasks_history.append({
            "task": task_type,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": task_status,
            "duration": task_duration
        })
        self.update_tasks_table()

    def parse_audience(self, table_name: str, accounts: list):
        """
        Фейковый парсинг аудитории.
        """
        for _ in range(len(accounts)):
            audience_id = random.randint(10000, 100000)
            self.add_audience_id(f"{table_name}_audience", audience_id)
            time.sleep(0.01)  # Эмуляция задержки

    def send_messages(self, table_name: str, accounts: list):
        """
        Фейковая рассылка сообщений.
        """
        for account in accounts:
            unused_audience_ids = self.get_unused_audience_ids(f"{table_name}_audience")
            if unused_audience_ids:
                audience_id = random.choice(unused_audience_ids)
                self.mark_audience_id_as_used(f"{table_name}_audience", audience_id)
                self.update_account_messages(table_name, account['id'], 1)
                time.sleep(0.01)  # Эмуляция задержки

    def update_account_status(self, table_name: str, account: dict):
        """
        Обновляет статус аккаунта в базе данных.

        Args:
            table_name (str): Имя таблицы.
            account (dict): Словарь с данными аккаунта.
        """
        try:
            c = self.db_conn.cursor()
            status = self.check_account_status(account)
            color = 'green' if status == "Валидный" else 'red'
            c.execute(f"""
                UPDATE '{table_name}'
                SET status_account = ?, color = ?
                WHERE id = ?
            """, (status, color, account['id']))
            self.db_conn.commit()
            logging.info(f"Статус аккаунта '{account['username']}' обновлен в таблице '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении статуса аккаунта: {e}")

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

    def update_account_messages(self, table_name: str, account_id: int, messages_run: int):
        """
        Обновляет счетчик сообщений в базе данных.

        Args:
            table_name (str): Имя таблицы.
            account_id (int): ID аккаунта.
            messages_run (int): Количество сообщений для добавления.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                UPDATE '{table_name}'
                SET messages_run = messages_run + ?,
                    messages_total = messages_total + ?
                WHERE id = ?
            """, (messages_run, messages_run, account_id))
            self.db_conn.commit()
            logging.info(f"Счетчик сообщений для аккаунта '{account_id}' обновлен.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении счетчика сообщений: {e}")

    def get_accounts(self, table_name: str) -> list:
        """
        Получает список всех аккаунтов из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список словарей с данными аккаунтов.
        """
        return self.db_manager.get_accounts(table_name)

    def update_tasks_table(self):
        """
        Обновляет таблицу истории задач.
        """
        self.tasks_table.setRowCount(len(self.tasks_history))
        for i, task_data in enumerate(self.tasks_history):
            self.tasks_table.setItem(i, 0, QTableWidgetItem(task_data["task"]))
            self.tasks_table.setItem(i, 1, QTableWidgetItem(task_data["date"]))
            self.tasks_table.setItem(i, 2, QTableWidgetItem(task_data["status"]))

    def update_accounts_stats_table(self):
        """
        Обновляет таблицу статистики по аккаунтам.
        """
        accounts = self.get_accounts(self.current_table)
        self.accounts_stats_table.setRowCount(len(accounts))
        for i, account in enumerate(accounts):
            self.accounts_stats_table.setItem(i, 0, QTableWidgetItem(account["username"]))
            self.accounts_stats_table.setItem(i, 1, QTableWidgetItem(str(account["messages_total"])))
            self.accounts_stats_table.setItem(i, 2, QTableWidgetItem(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(account["last_update"]))))

    def add_account(self, table_name: str, account: dict) -> None:
        """
        Добавляет аккаунт в таблицу.

        Args:
            table_name (str): Имя таблицы.
            account (dict): Словарь с данными аккаунта.
        """
        self.db_manager.add_account(table_name, account)

    def add_audience_id(self, table_name: str, audience_id: int) -> None:
        """
        Добавляет ID аудитории в таблицу.

        Args:
            table_name (str): Имя таблицы.
            audience_id (int): ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                INSERT OR IGNORE INTO '{table_name}' (audience_id)
                VALUES (?)
            """, (audience_id,))
            self.db_conn.commit()
            logging.info(f"ID аудитории '{audience_id}' добавлен в таблицу '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении ID аудитории: {e}")

    def get_audience_ids(self, table_name: str) -> list:
        """
        Получает список всех ID аудитории из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"SELECT audience_id FROM '{table_name}'")
            rows = c.fetchall()
            audience_ids = [row[0] for row in rows]
            logging.info(f"Список ID аудитории из таблицы '{table_name}' получен.")
            return audience_ids
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении списка ID аудитории: {e}")
            return []

    def mark_audience_id_as_used(self, table_name: str, audience_id: int) -> None:
        """
        Помечает ID аудитории как использованный.

        Args:
            table_name (str): Имя таблицы.
            audience_id (int): ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"""
                UPDATE '{table_name}'
                SET used = 1
                WHERE audience_id = ?
            """, (audience_id,))
            self.db_conn.commit()
            logging.info(f"ID аудитории '{audience_id}' помечен как использованный в таблице '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при пометке ID аудитории как использованный: {e}")

    def get_unused_audience_ids(self, table_name: str) -> list:
        """
        Получает список всех неиспользованных ID аудитории из таблицы.

        Args:
            table_name (str): Имя таблицы.

        Returns:
            list: Список неиспользованных ID аудитории.
        """
        try:
            c = self.db_conn.cursor()
            c.execute(f"SELECT audience_id FROM '{table_name}' WHERE used = 0")
            rows = c.fetchall()
            audience_ids = [row[0] for row in rows]
            logging.info(f"Список неиспользованных ID аудитории из таблицы '{table_name}' получен.")
            return audience_ids
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении списка неиспользованных ID аудитории: {e}")
            return []

    def load_settings(self):
        """
        Загружает настройки из файла (реализуйте свою логику загрузки).
        """
        try:
            with open('settings.txt', 'r') as f:
                for line in f:
                    key, value = line.strip().split("=", 1)
                    self.settings[key] = value
            logging.info("Настройки загружены.")
        except FileNotFoundError:
            logging.info("Файл настроек не найден. Используются стандартные настройки.")

    def save_settings(self):
        """
        Сохраняет настройки в файл (реализуйте свою логику сохранения).
        """
        try:
            with open('settings.txt', 'w') as f:
                for key, value in self.settings.items():
                    f.write(f"{key}={value}\n")
            logging.info("Настройки сохранены.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении настроек: {e}")

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
            self.add_account(self.current_table, {
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
        """
        Загружает таблицы из базы данных.
        """
        print("Загрузка таблиц из базы данных")  # Логирование
        try:
            c = self.db_conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall() if row[0] != 'sqlite_sequence']

            # Добавляем вкладки для каждой таблицы
            for table_name in tables:
                if table_name not in self.available_tables:
                    self.available_tables.append(table_name)
                    self.account_table = AccountTable(self, table_name)
                    self.tab_widget.addTab(self.account_table, table_name)
                    # Заполняем таблицу данными из БД
                    self.account_table.update_table(table_name)
        except Exception as e:
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
            self.delete_table(table_name)
            self.tab_widget.removeTab(current_index)
            self.available_tables.remove(table_name)
            self.current_table = None  # Обновляем текущую таблицу, если она была удалена
            logging.info(f"Таблица '{table_name}' удалена.")
        else:
            logging.info(f"Удаление таблицы '{table_name}' отменено.")

if __name__ == "__main__":
    app = QApplication([])
    main_app = Application()  # Создаем экземпляр приложения
    app.exec_()