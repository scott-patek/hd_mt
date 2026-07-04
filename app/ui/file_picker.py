"""Custom file picker dialog that works around macOS sandboxing issues."""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QDir, QMimeData
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileSystemModel,
    QTreeView,
    QLineEdit,
    QLabel,
)


class SimpleFilePicker(QDialog):
    """Simple file picker dialog that avoids macOS native dialog issues."""

    def __init__(self, parent=None, title="Open File", start_dir: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 600, 500)
        self.selected_file: Optional[str] = None

        # Start directory
        self.current_dir = Path(start_dir or Path.home() / "Downloads")
        if not self.current_dir.exists():
            self.current_dir = Path.home()

        layout = QVBoxLayout(self)

        # Path display
        path_layout = QHBoxLayout()
        path_label = QLabel("Current path:")
        self.path_input = QLineEdit()
        self.path_input.setText(str(self.current_dir))
        self.path_input.setReadOnly(True)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        layout.addLayout(path_layout)

        # File browser
        self.model = QFileSystemModel()
        self.model.setRootPath(str(self.current_dir))

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(self.current_dir)))
        self.tree.setColumnWidth(0, 300)
        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        # File input field
        file_layout = QHBoxLayout()
        file_label = QLabel("File name:")
        self.file_input = QLineEdit()
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_input)
        layout.addLayout(file_layout)

        # Buttons
        button_layout = QHBoxLayout()
        open_btn = QPushButton("Open")
        cancel_btn = QPushButton("Cancel")
        open_btn.clicked.connect(self._on_open)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(open_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def _on_item_double_clicked(self, index):
        path = self.model.filePath(index)
        file_path = Path(path)

        if file_path.is_dir():
            self.current_dir = file_path
            self.model.setRootPath(str(file_path))
            self.tree.setRootIndex(self.model.index(str(file_path)))
            self.path_input.setText(str(file_path))
        else:
            self.file_input.setText(file_path.name)
            self.selected_file = str(file_path)
            self.accept()

    def _on_open(self):
        filename = self.file_input.text().strip()
        if not filename:
            return

        file_path = self.current_dir / filename
        if file_path.exists() and file_path.is_file():
            self.selected_file = str(file_path)
            self.accept()

    def get_file(self) -> Optional[str]:
        """Return the selected file path or None if cancelled."""
        return self.selected_file


def get_open_file_name(
    parent=None,
    title: str = "Open File",
    start_dir: Optional[str] = None,
    filter_str: str = "All Files (*)",
) -> tuple[Optional[str], str]:
    """
    Show a custom file picker dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        start_dir: Starting directory
        filter_str: File filter (currently ignored; shows all files)
    
    Returns:
        Tuple of (selected_file_path, filter) or (None, "") if cancelled
    """
    dialog = SimpleFilePicker(parent, title=title, start_dir=start_dir)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_file(), filter_str
    return None, ""
