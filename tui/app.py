# ============================================================
# tui/app.py
# SQL Optimization Agent — Terminal UI
#
# LAYOUT (OpenCode-style, four panels):
#
#   ┌──────────────┬─────────────────────────────────────────┐
#   │  SCHEMA      │  OUTPUT                                 │
#   │              │                                         │
#   │  Tables      │  Pipeline output streams here live      │
#   │  ▶ table1    │  Step messages, AI response, results    │
#   │  ▶ table2    │                                         │
#   │              │                                         │
#   │  Views       │                                         │
#   │  ▶ vw_dash   │                                         │
#   │              │                                         │
#   ├──────────────┼─────────────────────────────────────────┤
#   │  RUNS        │  PROGRESS / INPUT                       │
#   │              │                                         │
#   │  14:32 opt   │  ████████░░  Step 5/9                   │
#   │  13:45 bench │  > Enter query or command...            │
#   └──────────────┴─────────────────────────────────────────┘
#
# KEYBOARD SHORTCUTS:
#   a / Enter   — open query input dialog
#   f           — full-run on queries/ folder
#   r           — refresh schema panel
#   b           — benchmark last optimization
#   d           — generate deployment package
#   h           — show history
#   w           — run schema watcher
#   s           — take schema snapshot
#   q / Ctrl+C  — quit
#
# LIBRARY: Textual (pip install textual)
# ============================================================

import asyncio
import threading
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    RichLog,
    Static,
    Tree,
)
from textual.widgets.tree import TreeNode


# ============================================================
# MODAL: Query Input Dialog
# ============================================================

class QueryInputDialog(ModalScreen):
    """
    Modal dialog for entering a SQL query or command.
    Appears when user presses 'a' or Enter.
    """

    CSS = """
    QueryInputDialog {
        align: center middle;
    }
    #dialog {
        width: 80;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }
    #dialog Label {
        margin-bottom: 1;
        color: $text-muted;
    }
    #dialog Input {
        margin-bottom: 1;
    }
    #buttons {
        height: 3;
        align: right middle;
    }
    Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Enter SQL query to optimize:")
            yield Input(placeholder="SELECT * FROM your_table WHERE ...", id="query_input")
            with Horizontal(id="buttons"):
                yield Button("Cancel",   variant="default",  id="cancel")
                yield Button("Full-Run", variant="primary",  id="full_run")
                yield Button("Analyze",  variant="success",  id="analyze")

    def on_mount(self) -> None:
        self.query_one("#query_input", Input).focus()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#analyze")
    def do_analyze(self) -> None:
        query = self.query_one("#query_input", Input).value.strip()
        self.dismiss({"action": "analyze", "query": query} if query else None)

    @on(Button.Pressed, "#full_run")
    def do_full_run(self) -> None:
        query = self.query_one("#query_input", Input).value.strip()
        self.dismiss({"action": "full_run", "query": query} if query else None)

    @on(Input.Submitted)
    def input_submitted(self) -> None:
        self.do_full_run()


# ============================================================
# MODAL: History Screen
# ============================================================

class HistoryScreen(ModalScreen):
    """Modal showing run history table."""

    CSS = """
    HistoryScreen {
        align: center middle;
    }
    #history_box {
        width: 90%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #history_log {
        height: 1fr;
    }
    #close_btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="history_box"):
            yield Label("[bold cyan]Run History[/bold cyan]")
            yield RichLog(id="history_log", highlight=True, markup=True)
            yield Button("Close [Esc]", variant="default", id="close_btn")

    def on_mount(self) -> None:
        log = self.query_one("#history_log", RichLog)
        try:
            from tools.history import get_history, print_history
            from io import StringIO
            from rich.console import Console as RConsole

            runs = get_history(limit=20)
            if not runs:
                log.write("[dim]No history yet — run some optimizations first[/dim]")
                return

            buf     = StringIO()
            console = RConsole(file=buf, highlight=False)
            print_history(runs)
            # Write each run as a formatted line
            for r in runs:
                label   = r.get("label") or r.get("query_preview", "")[:40]
                before  = f"{r['before_ms']}ms" if r.get("before_ms") else "—"
                after   = f"{r['after_ms']}ms"  if r.get("after_ms")  else "—"
                pct     = r.get("improvement_pct")
                imp_str = f"[green]{pct}%[/green]" if pct and pct > 0 else f"[red]{pct}%[/red]" if pct else "—"
                log.write(
                    f"[dim]{r['timestamp'][:16]}[/dim]  "
                    f"[cyan]#{r['id']}[/cyan]  "
                    f"{label[:35]}  "
                    f"[red]{before}[/red] → [green]{after}[/green]  {imp_str}"
                )
        except Exception as e:
            log.write(f"[red]Could not load history: {e}[/red]")

    @on(Button.Pressed, "#close_btn")
    def close(self) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()


# ============================================================
# MAIN APP
# ============================================================

class SQLAgentApp(App):
    """
    SQL Optimization Agent TUI.
    Four-panel OpenCode-style layout.
    """

    TITLE   = "SQL Optimization Agent"
    SUB_TITLE = "Offline · Local · Powered by Ollama"

    CSS = """
    /* ── Layout ───────────────────────────── */
    Screen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr 1fr;
    }

    #top_row {
        layout: horizontal;
        height: 1fr;
    }

    #bottom_row {
        layout: horizontal;
        height: 14;
        border-top: solid $primary-darken-2;
    }

    /* ── Schema Panel (top-left) ──────────── */
    #schema_panel {
        width: 28;
        border-right: solid $primary-darken-2;
        padding: 0 1;
    }

    #schema_panel Label {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }

    #schema_tree {
        height: 1fr;
        scrollbar-size: 1 1;
    }

    /* ── Output Panel (top-right) ─────────── */
    #output_panel {
        width: 1fr;
        padding: 0 1;
    }

    #output_label {
        color: $primary;
        text-style: bold;
    }

    #output_log {
        height: 1fr;
        scrollbar-size: 1 1;
        background: $surface-darken-1;
        padding: 0 1;
        border: solid $primary-darken-3;
    }

    /* ── Runs Panel (bottom-left) ─────────── */
    #runs_panel {
        width: 28;
        border-right: solid $primary-darken-2;
        padding: 0 1;
    }

    #runs_panel Label {
        color: $primary;
        text-style: bold;
    }

    #runs_list {
        height: 1fr;
        scrollbar-size: 1 1;
    }

    /* ── Progress/Input Panel (bottom-right) ─*/
    #progress_panel {
        width: 1fr;
        padding: 0 1;
    }

    #progress_label {
        color: $primary;
        text-style: bold;
    }

    #step_label {
        color: $text;
        margin-top: 1;
    }

    #elapsed_label {
        color: $text-muted;
        margin-bottom: 1;
    }

    #query_bar {
        width: 100%;
        margin-top: 1;
        border: solid $primary-darken-2;
    }

    /* ── Status bar ───────────────────────── */
    #status_bar {
        height: 1;
        background: $primary-darken-3;
        color: $text-muted;
        padding: 0 1;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("a",       "open_query",    "Analyze",   show=True),
        Binding("f",       "full_run_folder","Full-Run",  show=True),
        Binding("r",       "refresh_schema", "Refresh",   show=True),
        Binding("d",       "deploy",         "Deploy",    show=True),
        Binding("h",       "show_history",   "History",   show=True),
        Binding("w",       "run_watch",      "Watch",     show=True),
        Binding("s",       "snapshot",       "Snapshot",  show=True),
        Binding("ctrl+c",  "quit",           "Quit",      show=True),
        Binding("q",       "quit",           "Quit",      show=False),
    ]

    # Reactive state
    current_step    = reactive(0)
    total_steps     = reactive(9)
    step_label_text = reactive("Idle")
    elapsed_secs    = reactive(0.0)
    is_running      = reactive(False)
    status_text     = reactive("Ready — press [a] to analyze a query")

    def compose(self) -> ComposeResult:
        yield Header()

        # ── Top row ───────────────────────────────────────
        with Horizontal(id="top_row"):

            # Schema panel
            with Vertical(id="schema_panel"):
                yield Label("◈ SCHEMA")
                yield Tree("Database", id="schema_tree")

            # Output panel
            with Vertical(id="output_panel"):
                yield Label("◈ OUTPUT", id="output_label")
                yield RichLog(
                    id="output_log",
                    highlight=True,
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                )

        # ── Bottom row ────────────────────────────────────
        with Horizontal(id="bottom_row"):

            # Recent runs panel
            with Vertical(id="runs_panel"):
                yield Label("◈ RECENT RUNS")
                yield ListView(id="runs_list")

            # Progress + input panel
            with Vertical(id="progress_panel"):
                yield Label("◈ PROGRESS", id="progress_label")
                yield ProgressBar(
                    total=9,
                    show_eta=False,
                    id="progress_bar",
                )
                yield Label("Idle", id="step_label")
                yield Label("", id="elapsed_label")
                yield Input(
                    placeholder="Press [a] to enter a query...",
                    id="query_bar",
                )

        yield Footer()

    # ── Startup ───────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize panels on startup."""
        self._task_start_time = None
        self._timer      = None
        self._load_schema()
        self._load_recent_runs()
        self._write_welcome()

    def _write_welcome(self) -> None:
        log = self.query_one("#output_log", RichLog)
        log.write("[bold cyan]SQL Optimization Agent v2[/bold cyan]")
        log.write("[dim]Offline · Local · Powered by Ollama[/dim]")
        log.write("")
        log.write("  [cyan]a[/cyan]  — analyze / full-run a query")
        log.write("  [cyan]f[/cyan]  — batch full-run on queries/ folder")
        log.write("  [cyan]r[/cyan]  — refresh schema tree")
        log.write("  [cyan]d[/cyan]  — generate deployment package")
        log.write("  [cyan]h[/cyan]  — view run history")
        log.write("  [cyan]w[/cyan]  — run schema watcher")
        log.write("  [cyan]s[/cyan]  — take schema snapshot")
        log.write("  [cyan]q[/cyan]  — quit")
        log.write("")

    # ── Schema Tree ───────────────────────────────────────

    def _load_schema(self) -> None:
        """Populate the schema tree from SQL Server."""
        tree = self.query_one("#schema_tree", Tree)
        tree.clear()

        try:
            from tools.schema import list_all_tables, list_all_views
            tables = list_all_tables()
            views  = list_all_views()

            tables_node = tree.root.add(
                f"[bold]Tables ({len(tables)})[/bold]",
                expand=True,
            )
            for t in tables:
                tables_node.add_leaf(f"[green]▶[/green] {t}", data={"type": "table", "name": t})

            views_node = tree.root.add(
                f"[bold]Views ({len(views)})[/bold]",
                expand=True,
            )
            for v in views:
                views_node.add_leaf(f"[cyan]▶[/cyan] {v}", data={"type": "view", "name": v})

            tree.root.expand()
            self._set_status(
                f"Connected — {len(tables)} tables · {len(views)} views"
            )

        except Exception as e:
            tree.root.add_leaf(f"[red]✗ Cannot connect: {e}[/red]")
            self._set_status(f"DB Error: {e}")

    # ── Recent Runs ───────────────────────────────────────

    def _load_recent_runs(self) -> None:
        """Populate recent runs list from history.db."""
        lv = self.query_one("#runs_list", ListView)
        lv.clear()

        try:
            from tools.history import get_history
            runs = get_history(limit=8)

            if not runs:
                lv.append(ListItem(Label("[dim]No runs yet[/dim]")))
                return

            for r in runs:
                label = r.get("label") or r.get("query_preview", "")[:22]
                time  = r["timestamp"][11:16]
                pct   = r.get("improvement_pct")
                color = "green" if pct and pct > 0 else "red" if pct else "dim"
                pct_str = f"[{color}]{pct}%[/{color}]" if pct is not None else ""
                lv.append(ListItem(
                    Label(f"[dim]{time}[/dim] {label[:18]} {pct_str}"),
                    name=str(r["id"]),
                ))
        except Exception:
            lv.append(ListItem(Label("[dim]History unavailable[/dim]")))

    # ── Output helpers ────────────────────────────────────

    def _write(self, text: str) -> None:
        """Write a line to the output log."""
        try:
            log = self.query_one("#output_log", RichLog)
            log.write(text)
        except Exception:
            pass

    def _set_status(self, text: str) -> None:
        self.status_text = text

    def _set_step(self, step: int, total: int, label: str) -> None:
        self.current_step    = step
        self.total_steps     = total
        self.step_label_text = label
        try:
            bar = self.query_one("#progress_bar", ProgressBar)
            bar.update(total=total, progress=step)   # correct Textual API
            self.query_one("#step_label", Label).update(
                f"Step {step}/{total} — {label}"
            )
        except Exception:
            pass

    def _set_elapsed(self, secs: float) -> None:
        try:
            self.query_one("#elapsed_label", Label).update(
                f"[dim]Elapsed: {secs:.1f}s[/dim]"
            )
        except Exception:
            pass

    def _reset_progress(self) -> None:
        try:
            bar = self.query_one("#progress_bar", ProgressBar)
            bar.update(total=9, progress=0)          # correct Textual API
            self.query_one("#step_label",   Label).update("Idle")
            self.query_one("#elapsed_label",Label).update("")
        except Exception:
            pass

    # ── Watch reactive changes ────────────────────────────

    def watch_status_text(self, value: str) -> None:
        pass  # status shown via _set_status, not a widget

    # ── Tree interaction ──────────────────────────────────

    @on(Tree.NodeSelected, "#schema_tree")
    def tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """When user clicks a table/view in the schema tree, show its details."""
        node = event.node
        data = node.data
        if not data:
            return

        obj_type = data.get("type")
        obj_name = data.get("name", "")

        if obj_type == "table":
            self._show_table_details(obj_name)
        elif obj_type == "view":
            self._show_view_details(obj_name)

    def _show_table_details(self, table: str) -> None:
        self._write(f"\n[bold cyan]━━━ TABLE: {table} ━━━[/bold cyan]")
        try:
            from tools.schema import get_schema
            s = get_schema(table)
            self._write(f"[dim]~{s.get('estimated_row_count','?'):,} rows[/dim]")
            self._write("[bold]Columns:[/bold]")
            for col in s["columns"]:
                pk   = " [yellow][PK][/yellow]" if col["primary_key"] == "YES" else ""
                null = " [dim]NULL[/dim]"        if col["nullable"]    == "YES" else ""
                self._write(f"  {col['name']}  [dim]{col['type']}[/dim]{pk}{null}")
            if s["indexes"]:
                self._write("[bold]Indexes:[/bold]")
                for idx in s["indexes"]:
                    self._write(f"  [cyan]•[/cyan] {idx['name']} ({idx['key_columns']})")
            else:
                self._write("  [yellow]No indexes[/yellow]")
        except Exception as e:
            self._write(f"[red]Error loading schema: {e}[/red]")

    def _show_view_details(self, view: str) -> None:
        self._write(f"\n[bold cyan]━━━ VIEW: {view} ━━━[/bold cyan]")
        try:
            from tools.schema import get_view_definition
            vd = get_view_definition(view)
            if "error" in vd:
                self._write(f"[red]{vd['error']}[/red]")
                return
            self._write(f"[dim]References: {', '.join(vd['referenced_tables'])}[/dim]")
            self._write("[bold]Definition:[/bold]")
            for line in vd["definition"].splitlines()[:30]:
                self._write(f"  [dim]{line}[/dim]")
            if len(vd["definition"].splitlines()) > 30:
                self._write("  [dim]... (truncated — full definition in SSMS)[/dim]")
        except Exception as e:
            self._write(f"[red]Error loading view: {e}[/red]")

    # ── Input bar ─────────────────────────────────────────

    @on(Input.Submitted, "#query_bar")
    def input_bar_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.query_one("#query_bar", Input).value = ""
            self._run_full_run(query)

    # ── Key Bindings ──────────────────────────────────────

    def action_open_query(self) -> None:
        """Open the query input dialog."""
        if self.is_running:
            self._write("[yellow]⚠ A task is already running — please wait[/yellow]")
            return
        self.push_screen(QueryInputDialog(), self._handle_query_dialog)

    def _handle_query_dialog(self, result) -> None:
        if not result:
            return
        action = result.get("action")
        query  = result.get("query", "")
        if not query:
            return
        if action == "full_run":
            self._run_full_run(query)
        elif action == "analyze":
            self._run_analyze(query)

    def action_full_run_folder(self) -> None:
        """Run batch full-run on queries/ folder."""
        if self.is_running:
            self._write("[yellow]⚠ Already running — please wait[/yellow]")
            return
        queries_folder = Path("queries")
        if not queries_folder.exists():
            self._write("[yellow]⚠ No 'queries/' folder found[/yellow]")
            self._write("[dim]  Create it and add .sql files, then press [f] again[/dim]")
            return
        self._run_batch(str(queries_folder))

    def action_refresh_schema(self) -> None:
        """Refresh the schema tree."""
        self._write("\n[cyan]→ Refreshing schema...[/cyan]")
        self._load_schema()
        self._write("[green]✓ Schema refreshed[/green]")

    def action_deploy(self) -> None:
        """Generate deployment package."""
        if self.is_running:
            self._write("[yellow]⚠ Already running — please wait[/yellow]")
            return
        self._run_in_thread(self._do_deploy, "Deploy")

    def action_show_history(self) -> None:
        """Show history modal."""
        self.push_screen(HistoryScreen())

    def action_run_watch(self) -> None:
        """Run schema watcher."""
        if self.is_running:
            self._write("[yellow]⚠ Already running — please wait[/yellow]")
            return
        self._run_in_thread(self._do_watch, "Schema Watch")

    def action_snapshot(self) -> None:
        """Take schema snapshot."""
        self._run_in_thread(self._do_snapshot, "Snapshot")

    # ── Background task runners ───────────────────────────

    def _run_full_run(self, query: str) -> None:
        self._run_in_thread(lambda: self._do_full_run(query), "Full-Run")

    def _run_analyze(self, query: str) -> None:
        self._run_in_thread(lambda: self._do_analyze(query), "Analyze")

    def _run_batch(self, folder: str) -> None:
        self._run_in_thread(lambda: self._do_batch(folder), "Batch")

    def _run_in_thread(self, fn, label: str) -> None:
        """Run a blocking function in a background thread."""
        if self.is_running:
            return

        self.is_running  = True
        self._task_start_time = time.time()
        self._write(f"\n[bold cyan]━━━ {label.upper()} ━━━[/bold cyan]")
        self._set_status(f"Running: {label}...")

        def run():
            try:
                fn()
            except Exception as e:
                self.call_from_thread(self._write, f"[red]✗ Error: {e}[/red]")
            finally:
                self.call_from_thread(self._on_task_complete)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        # Kick off elapsed timer via set_timer (async-safe, runs on main thread)
        self.set_timer(0.1, self._tick_elapsed)

    async def _tick_elapsed(self) -> None:
        """Update elapsed time every second while running.
        Called from main Textual thread via set_timer — must be async.
        Uses _set_elapsed directly (no call_from_thread needed here).
        """
        if not self.is_running:
            return
        elapsed = time.time() - (self._task_start_time or time.time())
        self._set_elapsed(elapsed)          # direct call — we ARE on main thread
        self.set_timer(1.0, self._tick_elapsed)

    def _on_task_complete(self) -> None:
        """Called when a background task finishes."""
        self.is_running = False
        self._reset_progress()
        self._load_recent_runs()
        self._set_status("Ready — press [a] to analyze a query")

    # ── Task implementations ──────────────────────────────

    def _do_full_run(self, query: str) -> None:
        """Execute full-run pipeline, writing output to the log."""
        from tools.pipeline import run_single

        # Monkey-patch console output to TUI log
        self._patch_console()
        try:
            result = run_single(query, skip_deploy=False)
            if result.get("success"):
                pct = result.get("benchmark", {}).get("improvement_pct") if result.get("benchmark") else None
                if pct:
                    self.call_from_thread(
                        self._write,
                        f"\n[bold green]✓ Complete — {pct}% improvement[/bold green]"
                    )
                else:
                    self.call_from_thread(self._write, "\n[bold green]✓ Complete[/bold green]")
        finally:
            self._restore_console()

    def _do_analyze(self, query: str) -> None:
        """Execute just the optimization (no benchmark/deploy)."""
        self._patch_console()
        try:
            from tools.schema import list_all_tables, list_all_views, get_schema, get_view_definition
            from tools.optimizer import optimize_query

            all_tables  = list_all_tables()
            all_views   = list_all_views()
            query_upper = query.upper()
            found       = [o for o in all_tables + all_views if o.upper() in query_upper]
            if not found:
                found = all_tables

            schema_list = []
            for obj in found:
                if obj in all_tables:
                    schema_list.append(get_schema(obj))
                else:
                    vd = get_view_definition(obj)
                    for t in vd.get("referenced_tables", []):
                        if t in all_tables:
                            schema_list.append(get_schema(t))

            optimize_query(query, schema_list)
        finally:
            self._restore_console()

    def _do_batch(self, folder: str) -> None:
        """Execute batch full-run on a folder."""
        self._patch_console()
        try:
            from tools.pipeline import run_batch
            run_batch(folder, skip_deploy=False)
        finally:
            self._restore_console()

    def _do_deploy(self) -> None:
        """Generate deployment package."""
        self._patch_console()
        try:
            from tools.reporter import generate_deployment_package
            generate_deployment_package()
        finally:
            self._restore_console()

    def _do_watch(self) -> None:
        """Run schema watcher."""
        self._patch_console()
        try:
            from tools.watcher import run_watch
            run_watch()
        finally:
            self._restore_console()

    def _do_snapshot(self) -> None:
        """Take schema snapshot."""
        self._patch_console()
        try:
            from tools.watcher import take_snapshot, save_snapshot
            snap  = take_snapshot()
            paths = save_snapshot(snap)
            self.call_from_thread(
                self._write,
                f"[green]✓ Snapshot saved[/green] [dim]{Path(paths['dated']).name}[/dim]"
            )
        finally:
            self._restore_console()

    # ── Console redirect ──────────────────────────────────
    # Redirects Rich console output from tools/* into the TUI log

    def _patch_console(self) -> None:
        """Redirect all console.print calls to the TUI output log."""
        import tools.optimizer as opt_mod
        import tools.schema    as sch_mod
        import tools.executor  as exe_mod
        import tools.benchmarker as bench_mod
        import tools.pipeline  as pipe_mod

        self._orig_consoles = {}

        def make_tui_console(module):
            from rich.console import Console
            old = module.console

            class TUIConsole:
                def print(self, *args, **kwargs):
                    # Convert Rich markup to string and write to TUI log
                    try:
                        buf = StringIO()
                        c   = Console(file=buf, highlight=False)
                        c.print(*args, **kwargs)
                        text = buf.getvalue().rstrip()
                        if text:
                            self_app.call_from_thread(self_app._write, text)
                            # ── Progress bar hook ──────────────────────
                            # Detect "Step N/M — label" lines from optimizer
                            # and drive the progress bar from them
                            import re as _re
                            m = _re.search("Step (\\d+)/(\\d+)", text)
                            if m:
                                step  = int(m.group(1))
                                total = int(m.group(2))
                                lbl   = f"step {m.group(1)} of {m.group(2)}"
                                self_app.call_from_thread(
                                    self_app._set_step, step, total, lbl
                                )
                    except Exception:
                        pass
                def __getattr__(self, name):
                    return getattr(old, name)

            self._orig_consoles[module] = old
            module.console = TUIConsole()

        self_app = self
        for mod in [opt_mod, sch_mod, exe_mod, bench_mod, pipe_mod]:
            try:
                make_tui_console(mod)
            except Exception:
                pass

    def _restore_console(self) -> None:
        """Restore original console objects after task."""
        for mod, orig in getattr(self, "_orig_consoles", {}).items():
            try:
                mod.console = orig
            except Exception:
                pass
        self._orig_consoles = {}


# ============================================================
# ENTRY POINT
# ============================================================

def run_tui():
    """Start the TUI application."""
    app = SQLAgentApp()
    app.run()


if __name__ == "__main__":
    run_tui()
