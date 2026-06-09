Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd /c cd /d """ & folder & """ && set ""PYTHONUTF8=1"" && set ""PYTHONIOENCODING=utf-8"" && set ""PYTHONLEGACYWINDOWSSTDIO=0"" && (py -3w -X utf8 scripts\lab_gui.py || pythonw -X utf8 scripts\lab_gui.py)"
shell.Run cmd, 0, False
