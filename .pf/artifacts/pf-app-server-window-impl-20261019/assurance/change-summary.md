# Изменения и проверенные границы

Заголовок проверяется как автоматическое поведение TTY: настоящий logo renderer, Core version переданного объекта, текущий PID, назначение foreground Runtime и предупреждение о закрытии. NonTTY/None/ошибки isatty не вызывают GUI; ASCII-поток действительно отклоняет непредставимые символы. Сохраняются прежние `--console` и все четыре runtime/server + serve/run alias; detached/status/stop не принимают новый window-флаг.

Windows fake APIs ограничены внешней границей: production ownership logic требует единственного текущего PID, видимого ConsoleWindowClass, повторного владения и наблюдения IsIconic. Shared/foreign/oversized lists, ConPTY/Windows Terminal, remote/multiplexer, исчезнувшее окно, native errors и отсутствие подтверждения отклоняются.

Linux вызывает настоящие property/process/ownership/state parsers над фикстурами. Проверяются direct/exclusive xterm, UID, session/process groups, TTY, parent identity/start time, sole child, local X11, WINDOWID, window PID/class, обе части подтверждённого состояния. Wayland/XWayland, SSH, remote DISPLAY/headless, multiplexers, shared/changed owner, missing tools, inaccessible proc, scan/time limits, subprocess failures/timeout и неподтверждённая минимизация дают отказ. Внешние xprop/xdotool вызовы подменены; проверены shell=False и timeout=1s. Fresh-process import test запрещает import-time native binding, subprocess и /proc scan.

Ошибочный адаптер не останавливает цепочку command_serve: вызывается serve, сохраняется его exit code; private exception canary не выводится. Существующие проверки настоящего loopback HTTP и guarded shutdown исполняются без изменения assertions.

Autostart проверяет прямой tools/processforge.py, foreground serve --minimized, точный указанный Python при наличии соседнего pythonw.exe, Windows CommandLineToArgvW с пробелами/Unicode и XML settings. Старое действие без флага, иной interpreter и bridge-only distribution не принимаются; перезапись требует --replace, preview выполняет только fake /Query. Не выполняются реальные schtasks/Codex subprocess.

Прямой worker console run: 27/27. Operator и autostart через fixture-allocation-only harness: exit 0. Начальные canonical worker runs были остановлены TemporaryDirectory ACL до assertions. Singleton smoke через тот же harness не прошёл live-owner gate; отдельная диагностика установила tasklist ERROR: Access denied при живом готовом child. Продукт/права/существующие singleton assertions не менялись.

Итоговая независимая проверка primary: сообщение msg_3b5323a1f0b54db3a49ffcdf22ad8c7e и прочитанный `primary/focused-checks-final.md` подтверждают exit 0 у точных canonical команд operator (финальные 27 методов), autostart и неизменённого singleton smoke. В родительском окружении worker liveness failure не повторился; TEMP/TMP указывали в собственный task scratch, подмены тестового кода и изменения assertions отсутствовали. Это подтверждение primary отделено от собственных worker результатов.

Native Windows visible-classic minimization и Linux GUI acceptance не заявляются; положительные desktop-сценарии здесь смоделированы. Сам факт успешного mock или Windows argv decoding не доказывает минимизацию настоящего окна.
