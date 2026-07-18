from ui.themes import DEFAULT_THEME_KEY, build_stylesheet, get_theme

STYLE = build_stylesheet(get_theme(DEFAULT_THEME_KEY))

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