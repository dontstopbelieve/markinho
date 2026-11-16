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
