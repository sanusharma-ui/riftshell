import unittest

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.terminal_output import TerminalOutput


class TerminalOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["output-tests", "-platform", "offscreen"])

    def setUp(self):
        self.output = TerminalOutput()

    def tearDown(self):
        self.output.clear()
        self.output.deleteLater()

    def test_large_output_yields_and_preserves_literal_text_and_order(self):
        text = "<b>literal</b>  aligned\tcolumn\n" * 1000
        heartbeat = []
        QTimer.singleShot(0, lambda: heartbeat.append(True))
        self.output.append_output(text, "#cccccc")
        self.output.append_output("next command", "#ffffff", "$")
        self.assertLess(len(self.output.toPlainText()), len(text))
        self.app.processEvents()
        self.assertEqual(heartbeat, [True])
        while self.output._pending:
            self.output._drain_output()
        self.assertEqual(self.output.toPlainText(), text + "\n$ next command")
        self.assertFalse(self.output._output_timer.isActive())

    def test_clear_discards_queued_output(self):
        self.output.append_output("old output\n" * 1000, "#cccccc")
        self.output.clear()
        self.output.append_output("fresh output", "#cccccc")
        self.output._drain_output()
        self.assertEqual(self.output.toPlainText(), "fresh output")

    def test_scrollback_is_bounded_by_real_lines(self):
        self.output.document().setMaximumBlockCount(20)
        self.output.append_output("\n".join(str(i) for i in range(100)), "#cccccc")
        self.assertEqual(self.output.document().blockCount(), 20)
        self.assertTrue(self.output.toPlainText().startswith("80\n"))
