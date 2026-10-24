Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

batchPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "uitslagen-web.bat")
exitCode = shell.Run("""" & batchPath & """", 7, True)

If exitCode <> 0 Then
    MsgBox "De lokale webversie is niet goed gestart (foutcode " & exitCode & ")." & vbCrLf & _
        "Start uitslagen-web.bat rechtstreeks om de foutmelding te bekijken.", _
        vbExclamation, "Uitslagen"
End If
