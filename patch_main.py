"""Patch main.py to wire AMBIENT + MEMORY + memory_recall intent."""

with open('aura/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Add imports after existing agent imports
old_imports = (
    'from aura.agent.router import ROUTER, Intent\n'
    'from aura.agent.kernel import KERNEL\n'
    'from aura.agent.planner import PLANNER\n'
    'from aura.agent.client import CLIENT\n'
)
new_imports = (
    'from aura.agent.router import ROUTER, Intent\n'
    'from aura.agent.kernel import KERNEL\n'
    'from aura.agent.planner import PLANNER\n'
    'from aura.agent.client import CLIENT\n'
    'from aura.agent.memory import MEMORY\n'
    'from aura.agent.ambient import AMBIENT\n'
)
if old_imports in src:
    src = src.replace(old_imports, new_imports)
    print('IMPORTS patched OK')
else:
    print('IMPORTS not found')

# 2. Add memory_recall handler inside TaskWorker.run() — after math_eval block
old_math_block = (
            '            # 2. Instant Math (< 0.01ms)\n'
            '            elif it == "math_eval":\n'
)
new_math_block = (
            '            # 1b. Memory Recall\n'
            '            elif it == "memory_recall":\n'
            '                self.ai_state.emit("thinking")\n'
            '                recent = MEMORY.recent_commands(8)\n'
            '                if recent:\n'
            '                    lines = [f"- {r[\'q\']}" for r in recent[-6:]]\n'
            '                    summary = "\\n".join(lines)\n'
            '                else:\n'
            '                    summary = "No prior commands in this session."\n'
            '                # Also ask the AI to answer from memory\n'
            '                data = KERNEL.process(self.intent.target)\n'
            '                # Prepend the raw memory log\n'
            '                data["answer"] = f"**Session memory:**\\n{summary}\\n\\n---\\n{data[\'answer\']}"\n'
            '                self.ai_answer.emit(data)\n'
            '                self.ai_state.emit("idle")\n'
            '                res_msg = "Memory recalled [OK]"\n'
            '\n'
            '            # 2. Instant Math (< 0.01ms)\n'
            '            elif it == "math_eval":\n'
)
if old_math_block in src:
    src = src.replace(old_math_block, new_math_block)
    print('MEMORY_RECALL handler patched OK')
else:
    print('math_eval block NOT FOUND')

# 3. Inject ambient wiring into AuraApp.__init__ — after self.lens is created
# Find where overlay and lens are instantiated
old_lens_line = '        self.lens = CursorLens()\n'
new_lens_line = (
    '        self.lens = CursorLens()\n'
    '\n'
    '        # Wire ambient intelligence\n'
    '        AMBIENT.context_changed.connect(KERNEL.update_world_model)\n'
    '        AMBIENT.suggestion.connect(self._on_ambient_suggestion)\n'
    '        AMBIENT.start()\n'
)
if old_lens_line in src:
    src = src.replace(old_lens_line, new_lens_line, 1)
    print('AMBIENT wire patched OK')
else:
    print('lens= line NOT FOUND')

# 4. Add _on_ambient_suggestion method before cleanup()
old_cleanup = '    def cleanup(self):\n'
new_handler = (
    '    def _on_ambient_suggestion(self, message: str, action: str):\n'
    '        """Proactive ambient bubble — surfaces insight without being asked."""\n'
    '        try:\n'
    '            self.lens.show_suggestion(message)\n'
    '        except Exception:\n'
    '            pass\n'
    '\n'
    '    def cleanup(self):\n'
)
if old_cleanup in src:
    src = src.replace(old_cleanup, new_handler, 1)
    print('_on_ambient_suggestion method patched OK')
else:
    print('cleanup() NOT FOUND')

# 5. Stop ambient on cleanup
old_stealth_stop = '        STEALTH.stop_hotkey_sentinel()\n'
new_stealth_stop = (
    '        STEALTH.stop_hotkey_sentinel()\n'
    '        AMBIENT.stop()\n'
)
if old_stealth_stop in src:
    src = src.replace(old_stealth_stop, new_stealth_stop, 1)
    print('AMBIENT.stop() patched OK')
else:
    print('STEALTH stop line NOT FOUND')

with open('aura/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('DONE')
