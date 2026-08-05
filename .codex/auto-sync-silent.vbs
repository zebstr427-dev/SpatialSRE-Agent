Option Explicit

Dim shell, fileSystem, scriptDirectory, syncScript, powershellPath
Dim command, exitCode

Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

scriptDirectory = fileSystem.GetParentFolderName(WScript.ScriptFullName)
syncScript = fileSystem.BuildPath(scriptDirectory, "auto-sync.ps1")
powershellPath = shell.ExpandEnvironmentStrings( _
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" _
)

command = Chr(34) & powershellPath & Chr(34) & _
    " -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " & _
    Chr(34) & syncScript & Chr(34)

exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode
