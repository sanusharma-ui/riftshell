STYLE = """
QMainWindow {
    background-color: #1a1b26;
}

QWidget {
    background-color: #1a1b26;
    color: #a9b1d6;
    font-family: Consolas;
}

QLabel {
    color: #9aa5ce;
    font-size: 10pt;
    font-family: Consolas;
}

QTextEdit {
    background-color: #16161e;
    color: #c0caf5;
    border: 1px solid #292e42;
    border-radius: 14px;
    padding: 12px;
    font-size: 12pt;
    selection-background-color: #33467c;
    selection-color: #c0caf5;
}

QLineEdit {
    background-color: #16161e;
    color: #c0caf5;
    border: 1px solid #292e42;
    border-radius: 14px;
    padding: 11px;
    font-size: 12pt;
    selection-background-color: #33467c;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #7aa2f7;
}

QListWidget {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 14px;
    padding: 6px;
    font-size: 10pt;
}

QListWidget::item {
    padding: 7px 8px;
    border-radius: 10px;
}

QListWidget::item:selected {
    background-color: #2f354d;
    color: #7dcfff;
}

QPushButton {
    background-color: #24283b;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 12px;
    padding: 10px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2f354d;
    border: 1px solid #7aa2f7;
    color: #c0caf5;
}

QPushButton:pressed {
    background-color: #1f2335;
}

QStatusBar {
    background-color: #1a1b26;
    color: #7dcfff;
}
"""

BOOT_BANNER = r"""
<pre style="
color:#00ff9c;
font-family:Consolas;
font-size:11pt;
line-height:115%;
">

██████╗ ██╗███████╗████████╗     ███████╗██╗  ██╗███████╗██╗     ██╗
██╔══██╗██║██╔════╝╚══██╔══╝     ██╔════╝██║  ██║██╔════╝██║     ██║
██████╔╝██║█████╗     ██║        ███████╗███████║█████╗  ██║     ██║
██╔══██╗██║██╔══╝     ██║        ╚════██║██╔══██║██╔══╝  ██║     ██║
██║  ██║██║██║        ██║        ███████║██║  ██║███████╗███████╗███████╗
╚═╝  ╚═╝╚═╝╚═╝        ╚═╝        ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝


                           ◢ RIFTSHELL v3.0 ◣

══════════════════════════════════════════════════════════════════════════════════

   ENGINE      :: CYBER CORE
   RUNTIME     :: PYTHON
   AI          :: ENABLED
   TERMINAL    :: CUSTOM COMMAND ENGINE
   COMMANDS    :: 100+
   STATUS      :: ONLINE

══════════════════════════════════════════════════════════════════════════════════

            >>> TYPE "help" TO START YOUR SESSION <<<

</pre>
"""