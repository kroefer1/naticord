import sys
import requests
import configparser
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QTextEdit, QLineEdit, QPushButton, QTabWidget, QMessageBox, QDialog, QListWidgetItem, QCompleter
from PyQt5.QtCore import Qt, QTimer, QStringListModel

class LoginScreen(QDialog):
    def __init__(self):
        # login screen ui
        super().__init__()
        self.setWindowTitle("Login")
        self.layout = QVBoxLayout()

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter your Discord token...")
        self.layout.addWidget(self.token_input)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        self.layout.addWidget(self.login_button)

        self.setLayout(self.layout)

    # token login through config.ini
    def login(self):
        token = self.token_input.text().strip()
        if token:
            config = configparser.ConfigParser()
            config['Auth'] = {'Token': token}
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Please enter a valid Discord token.")

class CustomCompleter(QCompleter):
    def __init__(self):
        super().__init__()
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.PopupCompletion)

class Naticord(QWidget):
    def __init__(self):
        # ui code
        super().__init__()
        self.setWindowTitle("Naticord")
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.left_panel = QWidget()
        self.left_panel_layout = QVBoxLayout()
        self.left_panel.setLayout(self.left_panel_layout)

        self.friends_tab = QWidget()
        self.servers_tab = QWidget()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.friends_tab, "Friends")
        self.tabs.addTab(self.servers_tab, "Servers")

        self.friends_layout = QVBoxLayout(self.friends_tab)
        self.servers_layout = QVBoxLayout(self.servers_tab)

        self.user_info_label = QLabel("User Info")
        self.friends_label = QLabel("Friends")
        self.servers_label = QLabel("Servers")

        self.friends_list = QListWidget()
        self.servers_list = QListWidget()

        self.friends_layout.addWidget(self.friends_label)
        self.friends_layout.addWidget(self.friends_list)

        self.servers_layout.addWidget(self.servers_label)
        self.servers_layout.addWidget(self.servers_list)

        self.left_panel_layout.addWidget(self.user_info_label)
        self.left_panel_layout.addWidget(self.tabs)

        self.layout.addWidget(self.left_panel)

        self.right_panel = QWidget()
        self.right_panel_layout = QVBoxLayout()
        self.right_panel.setLayout(self.right_panel_layout)

        self.messages_label = QLabel("Messages")
        self.right_panel_layout.addWidget(self.messages_label)

        self.messages_text_edit = QTextEdit()
        self.right_panel_layout.addWidget(self.messages_text_edit)

        self.message_input = QLineEdit()
        self.right_panel_layout.addWidget(self.message_input)

        self.layout.addWidget(self.right_panel)

        self.token = self.get_token()
        if not self.token:
            self.show_login_screen()
        else:
            self.load_data()

        # dm refresher, someone please improve this through a pr
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_messages)
        self.refresh_timer.start(3000)

        # Custom completer for message input field
        self.completer = CustomCompleter()
        self.message_input.setCompleter(self.completer)

        # Initialize completer model with empty list
        self.completer.setModel(QStringListModel([]))

        # Start the timer to refresh the completer's model
        self.refresh_completer_timer = QTimer(self)
        self.refresh_completer_timer.timeout.connect(self.load_usernames_completer)
        self.refresh_completer_timer.start(3000)

    # shows token input screen
    def show_login_screen(self):
        login_screen = LoginScreen()
        if login_screen.exec_() == QDialog.Accepted:
            self.token = self.get_token()
            self.load_data()
        else:
            sys.exit()

    # gets token from a file called 'config.ini'
    def get_token(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        return config['Auth']['Token'] if 'Auth' in config and 'Token' in config['Auth'] else None
    
    # loads all friends servers info etc
    def load_data(self):
        self.load_user_info()
        self.load_friends()
        self.load_servers()

    # gets user info and welcomes the user 
    def load_user_info(self):
        headers = {"Authorization": f"{self.token}"}
        response = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            self.user_info_label.setText(f"Welcome, {user_data.get('username')}")
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch user information.")

    # loads friends and servers through the api
    def load_friends(self):
        headers = {"Authorization": f"{self.token}"}
        response = requests.get("https://discord.com/api/v9/users/@me/channels", headers=headers)
        if response.status_code == 200:
            channels_data = response.json()
            for channel in channels_data:
                friend_name = channel.get("recipients", [{}])[0].get("username", "Unknown")
                item = QListWidgetItem(friend_name)
                item.setData(Qt.UserRole, channel.get("id"))
                self.friends_list.addItem(item)
            self.friends_list.itemDoubleClicked.connect(self.load_channel_messages)
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch friends.")

    def load_servers(self):
        headers = {"Authorization": f"{self.token}"}
        response = requests.get("https://discord.com/api/v9/users/@me/guilds", headers=headers)
        if response.status_code == 200:
            servers_data = response.json()
            for server in servers_data:
                server_name = server.get("name")
                item = QListWidgetItem(server_name)
                item.setData(Qt.UserRole, server.get("id"))
                self.servers_list.addItem(item)
            self.servers_list.itemDoubleClicked.connect(self.load_server_channels)
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch servers.")

    def load_server_channels(self, item):
        # Clear messages text edit when changing channels
        self.messages_text_edit.clear()

        # Fetch and display messages for the selected server channel
        channel_id = item.data(Qt.UserRole)
        if channel_id:
            headers = {"Authorization": f"{self.token}"}
            response = requests.get(f"https://discord.com/api/v9/guilds/{channel_id}/channels", headers=headers)
            if response.status_code == 200:
                channels_data = response.json()
                # Filter to get text channels only
                text_channels = [channel for channel in channels_data if channel["type"] == 0]
                if text_channels:
                    channel = text_channels[0]  # Select the first text channel
                    channel_id = channel["id"]
                    self.load_channel_messages(QListWidgetItem(channel["name"], self.servers_list), channel_id)
                else:
                    QMessageBox.warning(self, "Error", "No text channels found in the server.")
            else:
                QMessageBox.warning(self, "Error", "Failed to fetch server channels.")

    # loads server messages in a specific channel
    def load_channel_messages(self, item, channel_id=None):
        if not channel_id:
            channel_id = item.data(Qt.UserRole)
        if channel_id:
            headers = {"Authorization": f"{self.token}"}
            response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers, params={"limit": 20})
            if response.status_code == 200:
                messages_data = response.json()
                self.display_messages(messages_data)
            else:
                QMessageBox.warning(self, "Error", "Failed to fetch messages.")
    
    # displays messages in the message box on the right
    def display_messages(self, messages):
        self.messages_text_edit.clear()
        for message in reversed(messages):
            author = message.get("author", {}).get("username", "Unknown")
            content = self.format_message_content(message.get("content", ""))
            self.messages_text_edit.append(f"{author}: {content}")

    # formats message content with user mentions highlighted
    def format_message_content(self, content):
        headers = {"Authorization": f"{self.token}"}
        while "<@!" in content:
            start_index = content.index("<@!")  # Get the index of the start of the mention
            end_index = content.index(">", start_index)  # Get the index of the end of the mention
            user_id = content[start_index + 3:end_index]  # Extract the user ID
            username = self.get_username(user_id)  # Get the username associated with the user ID
            if username:
                content = content.replace(f"<@!{user_id}>", f"<span style=\"color: blue;\">@{username}</span>")  # Replace the mention with formatted username
            else:
                content = content.replace(f"<@!{user_id}>", f"<@!{user_id}>")  # If username not found, keep the original mention
        while "<@" in content:
            start_index = content.index("<@")  # Get the index of the start of the mention
            end_index = content.index(">", start_index)  # Get the index of the end of the mention
            user_id = content[start_index + 2:end_index]  # Extract the user ID
            username = self.get_username(user_id)  # Get the username associated with the user ID
            if username:
                content = content.replace(f"<@{user_id}>", f"<span style=\"color: blue;\">@{username}</span>")  # Replace the mention with formatted username
            else:
                content = content.replace(f"<@{user_id}>", f"<@{user_id}>")  # If username not found, keep the original mention
        return content

    # gets username from user ID
    def get_username(self, user_id):
        headers = {"Authorization": f"{self.token}"}
        response = requests.get(f"https://discord.com/api/v9/users/{user_id}", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('username')
        else:
            return None

    # code to send messages, communicates with the discord api and is quite basic
    def send_message(self):
        message = self.message_input.text()
        selected_tab_index = self.tabs.currentIndex()
        
        if selected_tab_index == 0:  # Friends tab
            selected_item = self.friends_list.currentItem()
            if selected_item:
                recipient_id = selected_item.data(Qt.UserRole)
                self.send_direct_message(recipient_id, message)
        elif selected_tab_index == 1:  # Servers tab
            selected_item = self.servers_list.currentItem()
            if selected_item:
                channel_id = selected_item.data(Qt.UserRole)
                self.send_channel_message(channel_id, message)

    def send_direct_message(self, recipient_id, message):
        headers = {"Authorization": f"{self.token}", "Content-Type": "application/json"}
        payload = {"content": message}
        response = requests.post(f"https://discord.com/api/v9/channels/{recipient_id}/messages", headers=headers, json=payload)
        if response.status_code != 200:
            QMessageBox.warning(self, "Error", "Failed to send message.")

    def send_channel_message(self, channel_id, message):
        headers = {"Authorization": f"{self.token}", "Content-Type": "application/json"}
        payload = {"content": message}
        response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers, json=payload)
        if response.status_code != 200:
            QMessageBox.warning(self, "Error", "Failed to send message.")

    def refresh_messages(self):
        selected_tab_index = self.tabs.currentIndex()
        selected_item = None
        if selected_tab_index == 0:
            selected_item = self.friends_list.currentItem()
        elif selected_tab_index == 1:
            selected_item = self.servers_list.currentItem()
        if selected_item:
            self.load_channel_messages(selected_item)

    def load_usernames_completer(self):
        # Fetch usernames from friends and servers list
        usernames = []
        for index in range(self.friends_list.count()):
            item = self.friends_list.item(index)
            username = item.text()
            if username:
                usernames.append(username)
        for index in range(self.servers_list.count()):
            item = self.servers_list.item(index)
            username = item.text()
            if username:
                usernames.append(username)
        # Update the completer model with the usernames
        model = QStringListModel(usernames)
        self.completer.setModel(model)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = Naticord()
    client.show()
    sys.exit(app.exec_())
