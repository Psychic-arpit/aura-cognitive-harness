"""Patch lens.py with new-thread + suggestion support."""
import sys

with open('aura/ui/lens.py', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Replace action bar
old_bar = (
    '        self.btn_copy = QPushButton("Copy Answer", self.resp_action_row)\n'
    '        self.btn_copy.setObjectName("LensActionBtn")\n'
    '        self.btn_copy.clicked.connect(self._copy_answer_to_clipboard)\n'
    '\n'
    '        self.btn_type = QPushButton("Insert at Cursor", self.resp_action_row)\n'
    '        self.btn_type.setObjectName("LensActionBtnPrimary")\n'
    '        self.btn_type.clicked.connect(self._type_answer_at_cursor)\n'
    '\n'
    '        self.btn_dismiss_resp = QPushButton("Close", self.resp_action_row)\n'
    '        self.btn_dismiss_resp.setObjectName("LensActionBtn")\n'
    '        self.btn_dismiss_resp.clicked.connect(self.dismiss_lens)\n'
    '\n'
    '        self.telemetry_pill = QLabel("60 FPS Compositor \u2022 Gemini 3.5 Flash", self.resp_action_row)\n'
    '        self.telemetry_pill.setObjectName("LensTelemetryPill")\n'
    '\n'
    '        self.resp_action_layout.addWidget(self.btn_copy)\n'
    '        self.resp_action_layout.addWidget(self.btn_type)\n'
    '        self.resp_action_layout.addWidget(self.btn_dismiss_resp)\n'
    '        self.resp_action_layout.addStretch()\n'
    '        self.resp_action_layout.addWidget(self.telemetry_pill)\n'
)
new_bar = (
    '        self.btn_copy = QPushButton("Copy", self.resp_action_row)\n'
    '        self.btn_copy.setObjectName("LensActionBtn")\n'
    '        self.btn_copy.clicked.connect(self._copy_answer_to_clipboard)\n'
    '\n'
    '        self.btn_type = QPushButton("Insert at Cursor", self.resp_action_row)\n'
    '        self.btn_type.setObjectName("LensActionBtnPrimary")\n'
    '        self.btn_type.clicked.connect(self._type_answer_at_cursor)\n'
    '\n'
    '        self.btn_new_thread = QPushButton("New Thread", self.resp_action_row)\n'
    '        self.btn_new_thread.setObjectName("LensActionBtn")\n'
    '        self.btn_new_thread.clicked.connect(self._on_new_thread)\n'
    '\n'
    '        self.btn_dismiss_resp = QPushButton("\u2715", self.resp_action_row)\n'
    '        self.btn_dismiss_resp.setObjectName("LensActionBtn")\n'
    '        self.btn_dismiss_resp.clicked.connect(self.dismiss_lens)\n'
    '\n'
    '        self.telemetry_pill = QLabel("AURA \u2022 Gemini 2.0 Flash", self.resp_action_row)\n'
    '        self.telemetry_pill.setObjectName("LensTelemetryPill")\n'
    '\n'
    '        self.resp_action_layout.addWidget(self.btn_copy)\n'
    '        self.resp_action_layout.addWidget(self.btn_type)\n'
    '        self.resp_action_layout.addWidget(self.btn_new_thread)\n'
    '        self.resp_action_layout.addStretch()\n'
    '        self.resp_action_layout.addWidget(self.telemetry_pill)\n'
    '        self.resp_action_layout.addWidget(self.btn_dismiss_resp)\n'
)
if old_bar in src:
    src = src.replace(old_bar, new_bar)
    print('ACTION_BAR replaced OK')
else:
    print('ACTION_BAR NOT FOUND')
    # debug
    idx = src.find('btn_copy')
    print(repr(src[idx-8:idx+200]))

# 2. Inject new methods before dismiss_lens
new_methods = '''
    def _on_new_thread(self):
        """Clears AURA conversation history for a fresh thread."""
        from aura.agent.kernel import KERNEL
        KERNEL.clear_history()
        self.resp_box.hide()
        self.resp_text.clear()
        self.latest_answer_raw = ""
        self.resize(460, 85)
        self.input.clear()
        self.input.setFocus()

    def show_suggestion(self, message: str):
        """Shows a proactive ambient suggestion bubble in the lens."""
        from PyQt6.QtWidgets import QApplication
        html = "<span style='color: #A78BFA; font-size: 11px; font-style: italic;'>" + message + "</span>"
        self.resp_box.show()
        self.resp_text.setHtml(html)
        self.resize(480, 150)
        if not self.isVisible():
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() - 500, screen.height() - 200)
            self.show()

'''

marker = '    def dismiss_lens(self):'
if marker in src:
    src = src.replace(marker, new_methods + marker, 1)
    print('METHODS injected OK')
else:
    print('dismiss_lens MARKER NOT FOUND')

with open('aura/ui/lens.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('DONE')
