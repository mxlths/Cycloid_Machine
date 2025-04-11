import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Set application-wide stylesheet for light theme
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 