---
trigger: always_on
---

# PRINCIPAL RULE
- DONT USE TERMINAL/SHELL, except for test compilation of app

# CRITICAL RULE FOR FILE READING:
1. NEVER use terminal/shell (e.g., `cat`, `less`, `head`, `tail`, `grep`) to read or search file contents.
2. ALWAYS use your native internal tools (like `read_file`, `view_file`, or whatever native IDE tool is available) to inspect files.
3. Only use the terminal for executing compiling, or running actual programs.