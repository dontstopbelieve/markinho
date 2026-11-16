; Instalador do Markinho para Windows (Inno Setup 6).
; Gere com: python packaging/build.py --edition padrao inno
; As três edições usam o mesmo AppId: instalar uma edição por cima de outra a substitui.

#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\build\dist\Markinho"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\release"
#endif
#ifndef Edition
  #define Edition "PADRÃO"
#endif
#ifndef OutputName
  #define OutputName "Markinho-" + AppVersion + "-setup"
#endif
#ifndef IconFile
  #define IconFile "..\icons\markinho.ico"
#endif

[Setup]
AppId={{6F1C2B9E-3D4A-4E8B-9C7D-2A5F0E1B3C4D}
AppName=Markinho
AppComments=Conversor Markdown
AppVersion={#AppVersion}
AppVerName=Markinho {#Edition} {#AppVersion}
AppPublisher=dontstopbelieve
AppPublisherURL=https://github.com/dontstopbelieve/markinho
AppSupportURL=https://github.com/dontstopbelieve/markinho/issues
DefaultDirName={autopf}\Markinho
DefaultGroupName=Markinho
DisableProgramGroupPage=yes
; o usuário escolhe: instalar só para si (sem senha de administrador) ou para todos
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\Markinho.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes
LicenseFile=termos.rtf

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
brazilianportuguese.FinishedLabel=O Markinho foi instalado.%n%nDica: para fixá-lo na barra de tarefas, abra o Markinho, clique com o botão direito no ícone dele na barra de tarefas e escolha “Fixar na barra de tarefas”.%n%nPara converter sem abrir o programa: botão direito no arquivo > Markinho (no Windows 11, em “Mostrar mais opções”).
english.FinishedLabel=Markinho has been installed.%n%nTip: to pin it to the taskbar, open Markinho, right-click its taskbar icon and choose “Pin to taskbar”.%n%nTo convert without opening the program: right-click a file > Markinho > Converter para Markdown aqui (on Windows 11, under “Show more options”).

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"
Name: "contextmenu"; Description: "Adicionar o menu “Markinho” ao botão direito (converter para Markdown, converter Markdown para Word/PDF/HTML, abrir no Markinho)"; GroupDescription: "Integração:"
Name: "addtopath"; Description: "Permitir usar o comando “markinho-cli” no terminal (adiciona ao PATH)"; GroupDescription: "Integração:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Markinho"; Filename: "{app}\Markinho.exe"
Name: "{group}\Markinho (terminal)"; Filename: "{cmd}"; Parameters: "/k ""{app}\markinho-cli.exe"" --help"; WorkingDir: "{userdocs}"
Name: "{group}\Desinstalar Markinho"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Markinho"; Filename: "{app}\Markinho.exe"; Tasks: desktopicon

[Registry]
; Botão direito: submenu “Markinho”. Documentos: “Converter para Markdown…” (escolhe onde salvar),
; “Converter para Markdown aqui” (sem perguntar) e “Abrir no Markinho”. Arquivos .md: “Converter Markdown
; para…” (Word, PDF, HTML…). No Windows 11 aparece em “Mostrar mais opções” (o menu novo exige pacote assinado).
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.doc\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xls\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ods\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ppt\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.odp\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown…"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\1perguntar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\1perguntar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-para-md ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: ""; ValueData: "Converter para Markdown aqui"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\2aqui"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\2aqui\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --converter-aqui ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\3abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\Markinho\shell\3abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho\shell\1exportar"; ValueType: string; ValueName: ""; ValueData: "Converter Markdown para… (Word, PDF, HTML…)"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho\shell\1exportar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho\shell\1exportar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --exportar ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho\shell\2abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho\shell\2abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\Markinho\shell\2abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Markinho"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho"; ValueType: string; ValueName: "SubCommands"; ValueData: ""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Markinho.exe"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho\shell\1exportar"; ValueType: string; ValueName: ""; ValueData: "Converter Markdown para… (Word, PDF, HTML…)"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho\shell\1exportar"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho\shell\1exportar\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" --exportar ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho\shell\2abrir"; ValueType: string; ValueName: ""; ValueData: "Abrir no Markinho"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho\shell\2abrir"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.markdown\shell\Markinho\shell\2abrir\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Markinho.exe"" ""%1"""; Tasks: contextmenu

[InstallDelete]
; Atualizar ou trocar de edição: o instalador substitui a versão atual no mesmo lugar (mesmo AppId).
; Antes de copiar, apaga a pasta interna do programa anterior, para não sobrar biblioteca de outra edição
; (ex.: IA da COMPLETA ao voltar para a LEVE). As configurações do usuário ficam na pasta do perfil
; (não aqui) e são mantidas.
Type: filesandordirs; Name: "{app}\_internal"
; modelos de IA embutidos (COMPLETA); os baixados pelo usuário ficam na pasta do perfil e não são apagados
Type: filesandordirs; Name: "{app}\models"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\models"

[Run]
Filename: "{app}\Markinho.exe"; Description: "Abrir o Markinho agora"; Flags: nowait postinstall skipifsilent

[Code]
const EnvKeyUser = 'Environment';

function NeedsAddPath(Dir: string): Boolean;
var Paths: string;
begin
  if not RegQueryStringValue(HKCU, EnvKeyUser, 'Path', Paths) then Paths := '';
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Paths) + ';') = 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Paths: string;
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') and NeedsAddPath(ExpandConstant('{app}')) then
  begin
    if not RegQueryStringValue(HKCU, EnvKeyUser, 'Path', Paths) then Paths := '';
    if (Paths <> '') and (Copy(Paths, Length(Paths), 1) <> ';') then Paths := Paths + ';';
    RegWriteExpandStringValue(HKCU, EnvKeyUser, 'Path', Paths + ExpandConstant('{app}'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Paths, Dir: string; P: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Dir := ExpandConstant('{app}');
    if RegQueryStringValue(HKCU, EnvKeyUser, 'Path', Paths) then
    begin
      P := Pos(';' + Uppercase(Dir), Uppercase(Paths));
      if P > 0 then
      begin
        Delete(Paths, P, Length(Dir) + 1);
        RegWriteExpandStringValue(HKCU, EnvKeyUser, 'Path', Paths);
      end;
    end;
  end;
end;
