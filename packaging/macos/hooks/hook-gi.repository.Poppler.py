"""PyInstaller hook for gi.repository.Poppler.

PyInstaller ships hooks for most GIRepository modules but not for Poppler,
which pdfarranger needs to render PDF pages (gi.require_version("Poppler",
"0.18")). This hook collects the typelib and the libpoppler-glib shared
library that the typelib is bound to.
"""

from PyInstaller.utils.hooks.gi import GiModuleInfo


def hook(hook_api):
    module_info = GiModuleInfo('Poppler', '0.18', hook_api=hook_api)
    if not module_info.available:
        return

    binaries, datas, hiddenimports = module_info.collect_typelib_data()

    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports)
