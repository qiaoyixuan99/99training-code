' Git Auto-Sync Watcher Launcher
' 用 VBScript 启动，避免中文路径编码问题
' 放到 shell:startup 文件夹即可开机自启

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
repoDir = FSO.GetParentFolderName(scriptDir)
pythonScript = scriptDir & "\auto_commit_watcher.py"

' 后台运行 pythonw（无窗口）
WshShell.Run "pythonw """ & pythonScript & """ --interval 120", 0, False

Set WshShell = Nothing
Set FSO = Nothing
