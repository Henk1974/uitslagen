Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

batchPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "uitslagen.bat")
exitCode = shell.Run("""" & batchPath & """ /background", 7, True)

If exitCode <> 0 Then
    MsgBox "Uitslagen is niet goed gestart (foutcode " & exitCode & ")." & vbCrLf & _
        "Start uitslagen.bat rechtstreeks om de foutmelding te bekijken.", _
        vbExclamation, "Uitslagen"
End If
