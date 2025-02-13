from dotenv import load_dotenv
from openai import OpenAI
import ollama
from bs4 import BeautifulSoup
import requests
import os
import sys
from PySide6.QtWidgets import QMainWindow, QWidget, QApplication, QLabel, QPushButton, QVBoxLayout, QLineEdit, QTextEdit, QRadioButton, QHBoxLayout

class APIClient:
    """Setup API Key and modules for to the chat completion calls"""
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.validate_api_key()

        # Create instance of OpenAI() class
        self.client = OpenAI()

    def validate_api_key(self):
        """Verify the OpenAI API key is present and is valid"""
        if not self.api_key:
            raise ValueError("API key not found")
        elif not self.api_key.startswith("sk-proj"):
            raise ValueError("API key found, but it does not start with sk-proj")
        
        print("API key validated successfully")

    def chat_completion(self, model, messages):
        """Call OpenAI API for chat completion"""
        response = self.client.chat.completions.create(
            model = model,
            messages = messages
        )
        return response.choices[0].message.content

class WebsiteScraper:
    """Fetch and parse website content"""
    def __init__(self, url):
        self.url = url
        self.title, self.text = self._scrape_website()

    def _scrape_website(self):
        """Get text from the relevant website using beautifulsoup"""
        response = requests.get(self.url)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch the website. \
                                  Status code: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else "No title found"
        
        # Remove irrelavant content from website body
        for irrelevant in soup.body(['script', 'style', 'img', 'input']):
            irrelevant.decompose()
        
        text = soup.body.get_text(separator="\n", strip=True) if soup.body \
                else "No content found"
        return title, text

class Gui(QMainWindow):
    """Setup the Desktop App"""
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Text Summariser")
        self.setGeometry(200, 200, 400, 600)

        # Create central widget
        central_widget = QWidget(self)  # Create a central widget
        self.setCentralWidget(central_widget)

        # Instantiate all the widgets
        layout = QVBoxLayout(central_widget)
        radio_button_layout = QHBoxLayout()
        label = QLabel("Enter Website", self)
        self.website_edit = QLineEdit(self)
        self.model_ollama_rbtn = QRadioButton("llama3.2", self)
        self.model_ollama_rbtn.setChecked(True)
        self.model_openai_rbtn = QRadioButton("gpt-4o-mini", self)
        self.summarize_button = QPushButton("Summarize", self)
        self.summary_text = QTextEdit(self)
        self.summarize_button.clicked.connect(self.summarize_api)

        # Add to layout
        layout.addWidget(label)
        layout.addWidget(self.website_edit)
        radio_button_layout.addWidget(self.model_ollama_rbtn)
        radio_button_layout.addWidget(self.model_openai_rbtn)
        layout.addLayout(radio_button_layout)
        layout.addWidget(self.summarize_button)
        layout.addWidget(self.summary_text)
        # self.setLayout(layout)

    def summarize_api(self):
        """Call the LLM APIs to summarize based on model selected"""
        if not self.website_edit.text().strip():
            self.summary_text.setText("Please enter a valid URL.")
            return
        try:
            summarizer = TextSummarizer(url=self.website_edit.text())
            if self.model_ollama_rbtn.isChecked():   
                model_name = self.model_ollama_rbtn.text()
            elif self.model_openai_rbtn.isChecked():
                model_name = self.model_openai_rbtn.text()
            summary = summarizer.summarize(model_name)
            self.summary_text.setText(summary)
        except ConnectionError as ce:
            self.summary_text.setText(f"Network Error: {ce}")
        except Exception as e:
            self.summary_text.setText(f"An error occurred during summarize: {e}")


# 3. call chat completion, mention model, link with website text
class TextSummarizer:
    """Combine website scraper to create prompt and call api"""
    def __init__(self, url):
        self.scraper = WebsiteScraper(url)
        self.api_client = APIClient()
        
    def create_prompt(self):
        # 1. define system and user prompt
        # 2. create prompt using sytem and user prompt
        system_prompt = (
            "You are an expert AI assistant. "
            "Given text from a website, provide the user with a short summary of the website. "
            "Ignore unnecessary or navigational text. Respond in markdown."
        )
        user_prompt = (
            f"Here is some content from this website titled {self.scraper.title}"
            "The content is as follows.\n"
            f"{self.scraper.text}"
            "Provide a summary of the key points in markdown. "
            "If you see any news or announcements, include a summary about that too."
            
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def summarize(self, model_name):
        """Select and call the model chat completion to generate response"""
        prompt = self.create_prompt()
        if model_name == 'gpt-4o-mini':
            response = self.api_client.chat_completion(model=model_name, messages=prompt)
        elif model_name == "llama3.2":
            response = ollama.chat(model=model_name, messages=prompt)
            response = response['message']['content']

        return response


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)

        summary_window = Gui()
        summary_window.show()

        app.exec()
        
    except Exception as e:
        print(f"An error occurred. {e}")

