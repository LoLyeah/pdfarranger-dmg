#!/usr/bin/env python3
"""Frozen-app entry point for the macOS bundle.

PyInstaller needs a plain top-level script as its entry point (a package
``__main__.py`` would break the relative imports).

Set ``PDFARRANGER_MACOS_DIAG=1`` to dump application state (document queue,
page model, thumbnails) and thread stacks every 5 s - used by the CI smoke
test to diagnose rendering problems on macOS.
"""

import os
import sys
from pathlib import Path


def _build_info():
    """Return the build stamp written by build_app.sh (version/commit/date)."""
    path = Path(sys.executable).resolve().parent.parent / "Resources" / "build-info.txt"
    try:
        return path.read_text(encoding="utf-8").replace("\n", " ").strip()
    except OSError:
        return "unknown (no build-info.txt)"


def _simulate_internal_drop(app):
    """Feed a drop without target and data to the drop handler.

    Reproduces the macOS failure mode of issue #1334: the drag ends without
    its target atom and without data. Used by the CI smoke test to check the
    fallback that moves the dragged (selected) pages anyway.
    """
    from gi.repository import Gdk, Gtk

    model = app.model
    if model is None or len(model) < 2:
        print("DIAG selftest: skipped, fewer than 2 pages", flush=True)
        return

    def order():
        return [row[0].description.replace("\n", " ") for row in model]

    before = order()
    app.iconview.select_path(Gtk.TreePath.new_from_indices([0]))
    app.drag_path = Gtk.TreePath.new_from_indices([len(model) - 1])
    app.drag_pos = Gtk.IconViewDropPosition.DROP_RIGHT

    class _Context:
        @staticmethod
        def get_selected_action():
            return Gdk.DragAction.MOVE

    class _SelectionData:
        """Stands in for the GtkSelectionData of a drag that lost its payload."""

        @staticmethod
        def get_data():
            return None

        @staticmethod
        def get_target():
            return None

    try:
        app.iv_dnd_received_data(app.iconview, _Context(), 0, 0, _SelectionData(), 0, 0)
    except Exception as exc:  # a crash here is what we are testing for
        print(f"DIAG selftest: ERROR {exc!r}", flush=True)
    print(f"DIAG selftest before={before}", flush=True)
    print(f"DIAG selftest after ={order()}", flush=True)

    # Second scenario: pages dropped on the empty area of the scrolled window
    # (MODEL_ROW_EXTERN target). This is the path that deleted pages on macOS.
    count_before = len(model)
    before_sw = order()
    app.iconview.select_path(Gtk.TreePath.new_from_indices([1]))
    app.drag_origin_self = True
    app.drag_path = Gtk.TreePath.new_from_indices([0])
    app.drag_pos = Gtk.IconViewDropPosition.DROP_LEFT
    try:
        app.sw_dnd_received_data(app.sw, None, 0, 0, _SelectionData(),
                                 app.MODEL_ROW_EXTERN, 0)
    except Exception as exc:
        print(f"DIAG selftest: ERROR(sw) {exc!r}", flush=True)
    finally:
        app.drag_origin_self = False
    print(f"DIAG selftest sw before={before_sw} count={count_before}", flush=True)
    print(f"DIAG selftest sw after ={order()} count={len(model)}", flush=True)


def _enable_diagnostics(app):
    import faulthandler

    from gi.repository import GLib

    faulthandler.enable()
    faulthandler.dump_traceback_later(20, repeat=True)
    state = {"round": 0}

    def dump():
        state["round"] += 1
        tag = f"DIAG[{state['round']}]"
        if state["round"] == 1:
            print(f"{tag} build: {_build_info()}", flush=True)
        try:
            pdfqueue = app.pdfqueue or []
            model = app.model
            print(f"{tag} pdfqueue={len(pdfqueue)} model={None if model is None else len(model)}",
                  flush=True)
            for doc in pdfqueue:
                print(f"{tag}   doc {doc.basename!r}: n_pages={doc.document.get_n_pages()}",
                      flush=True)
            if model is not None:
                for row in model:
                    page = row[0]
                    print(f"{tag}   page: thumbnail={page.thumbnail} "
                          f"wpx={page.width_in_pixel()} hpx={page.height_in_pixel()} "
                          f"scale={page.scale} zoom={page.zoom}", flush=True)
            thread = app.rendering_thread
            if thread is not None:
                print(f"{tag}   render thread alive={thread.is_alive()} "
                      f"model_lock={thread.model_lock.locked()}", flush=True)
            iconview = app.iconview
            if iconview is not None:
                print(f"{tag}   iconview visible={iconview.get_visible()} "
                      f"mapped={iconview.get_mapped()} size={iconview.get_allocated_width()}x"
                      f"{iconview.get_allocated_height()} model="
                      f"{iconview.get_model() is model}", flush=True)
            window = app.window
            if window is not None:
                print(f"{tag}   window size={window.get_size()} visible={window.get_visible()}",
                      flush=True)
        except Exception as exc:  # diagnostics must never break the app
            print(f"{tag} error while dumping state: {exc!r}", flush=True)
        if state["round"] == 3 and os.environ.get("PDFARRANGER_MACOS_DROP_SELFTEST"):
            _simulate_internal_drop(app)
        if state["round"] >= 8:
            faulthandler.cancel_dump_traceback_later()
        return state["round"] < 8

    GLib.timeout_add(5000, dump)


def main():
    from pdfarranger.pdfarranger import PdfArranger

    app = PdfArranger()
    if os.environ.get("PDFARRANGER_MACOS_DIAG"):
        _enable_diagnostics(app)
    sys.exit(app.run(sys.argv) or 0)


main()
