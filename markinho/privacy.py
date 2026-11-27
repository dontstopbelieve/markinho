# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Texto de privacidade (Ajuda > Privacidade e relatório de erro).

O arquivo PRIVACIDADE.md na raiz do projeto é uma cópia deste texto (um teste confere que são iguais).
"""

TEXT = """# Privacidade e relatório de erro

## Seus documentos não saem do computador

O Markinho converte tudo **no seu computador**. Ele não envia documentos, textos, imagens nem
nomes de arquivos para a internet, não tem telemetria (não “conta” o que você faz) e não procura
atualizações sozinho. Ele só usa a internet quando **você pede**, por exemplo para baixar modelos
de IA de um motor opcional — e mesmo aí nenhum documento é enviado.

- A descrição de imagens usa o **Ollama instalado no seu computador** (endereço local); nenhum
  serviço on-line é chamado.
- O servidor para assistentes de IA (MCP) só abre as pastas que você autorizou e só grava se você
  permitir.
- As suas configurações (motor, opções, últimas pastas usadas) ficam salvas apenas no seu
  computador, nas configurações do usuário do sistema.
- O Markinho conta, só no seu computador, quantos documentos você já converteu, para mostrar
  **uma única vez** um agradecimento aos 100 e aos 1.000 documentos (com a opção “Não mostrar de
  novo”). Esse número nunca é enviado a ninguém.

## Anonimizar

A opção **Anonimizar dados pessoais** troca CPF, CNPJ, e-mails, telefones, nomes da sua lista e
outros dados por marcadores, e tira autor, datas e dados escondidos das imagens. Ela roda no seu
computador e não guarda a correspondência entre “[PESSOA 1]” e o nome verdadeiro.

Na **sua lista**, maiúsculas, minúsculas e acentos não fazem diferença (“joão”, “JOÃO” e “Joao” são
iguais), mas **cada variação precisa ser escrita**: “João da Silva” não esconde “João”, “Sr. Silva”
nem “J. Silva”. Coloque todas as formas, uma por linha.

**Aviso de responsabilidade:** a anonimização automática nunca é 100%. O Markinho não se
responsabiliza por dados que deixarem de ser encontrados ou que forem trocados por engano; **cabe ao
usuário revisar o arquivo anonimizado antes de qualquer uso ou compartilhamento.** Trocar nomes por
marcadores é uma *pseudonimização* — para a LGPD, o texto ainda pode ser dado pessoal se der para
descobrir de quem se trata pelo contexto.

## O relatório de erro

Quando uma conversão falha, o Markinho guarda o erro **na memória, só enquanto o programa está
aberto**. Nada é gravado em disco nem enviado automaticamente. Em **Ajuda > Gerar relatório de
erro…** você vê o relatório inteiro, pode esconder os nomes dos arquivos e decide se salva, copia
ou manda para o suporte.

**O que o relatório contém**

- Versão e edição do Markinho; versão do Python e do Qt.
- Sistema operacional, quantidade de processadores, memória, idioma do sistema, tamanho e escala
  da tela.
- Motores de conversão disponíveis (instalados ou não).
- Suas configurações do Markinho, **sem pastas e caminhos**.
- Para cada erro desde que o programa foi aberto: horário, nome do arquivo (pode ser trocado por
  “arquivo1.pdf”), tipo e tamanho, a mensagem de erro, detalhes técnicos (onde o programa falhou)
  e a configuração usada naquela conversão (motor, opções, imagens, perfil).
- As últimas mensagens internas do programa, com caminhos e o nome do usuário do computador
  omitidos.

**O que o relatório nunca contém**

- O conteúdo dos seus documentos (texto, tabelas, imagens).
- Pastas e caminhos completos dos arquivos.
- O nome do seu usuário no computador.

## Preciso concordar com alguma coisa?

Não há coleta automática: o relatório só existe na tela até você decidir o que fazer com ele.
Se você escolher mandá-lo ao suporte, ele será usado **apenas para entender e corrigir o
problema**, e você pode pedir que seja apagado. Confira o texto antes de enviar: se algum nome de
arquivo for confidencial, marque “Esconder os nomes dos arquivos”.

*Este texto descreve como o programa funciona; não é uma orientação jurídica.*
"""

TEXT_EN = """# Privacy and error report

## Your documents stay on your computer

Markinho converts everything **on your computer**. It does not send documents, text, images or
file names to the internet, has no telemetry (it does not “count” what you do) and does not check
for updates on its own. It only uses the internet when **you ask**, for example to download the AI
models of an optional engine — and even then no document is sent.

- Image description uses the **Ollama installed on your computer** (a local address); no online
  service is called.
- The server for AI assistants (MCP) only opens the folders you authorized and only writes if you
  allow it.
- Your settings (engine, options, last folders used) are saved only on your computer, in the
  system user settings.
- Markinho counts, only on your computer, how many documents you have converted, to show a thank
  you **only once** at 100 and at 1,000 documents (with a “Don't show again” option). This number
  is never sent to anyone.

## Anonymize

The **Anonymize personal data** option replaces CPF, CNPJ, e-mails, phone numbers, names from your
list and other data with markers, and removes author, dates and hidden data from images. It runs on
your computer and does not keep the link between “[PESSOA 1]” and the real name. The detection
rules are made for Brazilian documents (CPF, CNPJ, PIS, voter ID, CNJ case numbers, Brazilian phone
numbers); e-mails, credit cards and your own list work for any language.

In **your list**, upper case, lower case and accents make no difference (“joão”, “JOÃO” and “Joao”
are the same), but **each variation must be written**: “João da Silva” does not hide “João”,
“Sr. Silva” or “J. Silva”. Write all the forms, one per line.

**Disclaimer:** automatic anonymization is never 100%. Markinho is not responsible for data that is
not found or that is replaced by mistake; **it is up to the user to review the anonymized file
before any use or sharing.** Replacing names with markers is *pseudonymization* — under data
protection laws (such as Brazil's LGPD or the GDPR), the text may still be personal data if the
context shows who it is about.

## The error report

When a conversion fails, Markinho keeps the error **in memory, only while the program is open**.
Nothing is written to disk or sent automatically. In **Help > Generate error report…** you see the
whole report, can hide the file names and decide whether to save it, copy it or send it to
support.

**What the report contains**

- Markinho version and edition; Python and Qt versions.
- Operating system, number of processors, memory, system language, screen size and scale.
- Available conversion engines (installed or not).
- Your Markinho settings, **without folders and paths**.
- For each error since the program was opened: time, file name (it can be replaced with
  “arquivo1.pdf”), type and size, the error message, technical details (where the program failed)
  and the settings used in that conversion (engine, options, images, profile).
- The program's latest internal messages, with paths and the computer user name left out.

**What the report never contains**

- The content of your documents (text, tables, images).
- Full folders and file paths.
- Your user name on the computer.

## Do I need to agree to anything?

There is no automatic collection: the report only exists on the screen until you decide what to do
with it. If you choose to send it to support, it will be used **only to understand and fix the
problem**, and you can ask for it to be deleted. Check the text before sending: if a file name is
confidential, tick “Hide file names”.

*This text describes how the program works; it is not legal advice.*
"""


def text() -> str:
    """O texto no idioma da interface (português ou inglês)."""
    from .i18n import language

    return TEXT if language() == "pt" else TEXT_EN
