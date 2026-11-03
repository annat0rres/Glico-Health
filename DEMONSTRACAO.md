# Demonstração visual

TUTORIAL DE COMO RODAR OS TESTES DE SISTEMA

O script abre uma janela do Chromium e simula o fluxo completo de entrada:
preenche o login de demonstração, seleciona o papel de paciente, completa o
questionário e chega à página inicial. 

OBS: Usa um banco SQLite temporário; nenhum
dado real ou banco MySQL é utilizado.

Na raiz do projeto, instale os requisitos da demonstração e o navegador:

```cmd
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Depois, inicie a demonstração:

FORMA DE VISUALIZAÇÃO VISUAL DOS TESTES

```cmd
.\.venv\Scripts\python.exe scripts\demo_visual.py
```

A janela fica aberta para você conferir a tela. Pressione Enter no terminal
para fechar a demonstração e remover o banco temporário.

Para validar o mesmo fluxo sem abrir uma janela:

```cmd
.\.venv\Scripts\python.exe scripts\demo_visual.py --modo-teste
```

## Testes de sistema

FORMA DE VISUALIZAÇÃO SEM SIMULAÇÃO VISUAL

Para executar os testes das páginas, formulários, sessão, questionários,
glicemia, calendário, perfil e leituras de temperatura:

```cmd
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes usam um banco SQLite isolado. Serviços externos ou operações que
dependem de vínculos e dados fora do cenário são simulados; MySQL, hardware
físico e integrações externas não são validados por essa suíte.
