# Sistema de Controle de Almoxarifado

Aplicação web para organizar equipamentos clínicos e insumos da Secretaria Municipal de Saúde em uma base única, substituindo controles espalhados em planilhas.

## Funcionalidades

- Cadastro e consulta de unidades de saúde.
- Cadastro de equipamentos vinculados a cada unidade.
- Registro de patrimônio, nome, marca, modelo e número de série.
- Acompanhamento da situação dos equipamentos: em uso, manutenção, quebrado, sucata ou reserva.
- Cadastro de insumos do almoxarifado central ou distribuídos nas unidades.
- Controle de quantidade, localização, datas de entrega, fabricação e vencimento.
- Acesso protegido por login administrativo.

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python 3 | Linguagem principal |
| Flask | Aplicação web e rotas |
| SQLite | Banco de dados local |
| HTML, CSS e JavaScript | Interface do sistema |
| Jinja | Templates das páginas |

## Como executar

### 1. Pré-requisitos

- Python 3.10 ou superior instalado.
- Git, caso o projeto seja obtido por um repositório.

### 2. Instale as dependências

No terminal, dentro da pasta do projeto:

```bash
python -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No Linux ou macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Crie o banco de dados

O banco é criado automaticamente ao iniciar a aplicação. Se preferir criá-lo separadamente, execute:

```bash
python criar_banco.py
```

### 4. Inicie a aplicação

```bash
python app.py
```

Depois, acesse [`http://127.0.0.1:5000`](http://127.0.0.1:5000) no navegador.

## Acesso e configuração

Por padrão, o login local é:

| Campo | Valor padrão |
| --- | --- |
| Usuário | `admin` |
| Senha | `admin` |

Altere essas credenciais antes de usar o sistema em produção. Elas podem ser configuradas por variáveis de ambiente:

```powershell
$env:ADMIN_USER = "seu_usuario"
$env:ADMIN_PASS = "sua_senha"
$env:SECRET_KEY = "uma_chave_secreta"
python app.py
```

## Comandos auxiliares

Para verificar as tabelas existentes no banco local:

```bash
python verificar_banco.py
```

O arquivo `almoxarifado.db` é criado na raiz do projeto e não deve ser versionado.

## Estrutura do projeto

```text
almoxarifado_secretaria_saude/
├── app.py                    # Aplicação Flask e rotas
├── schema_almoxarifado.sql   # Estrutura das tabelas SQLite
├── requirements.txt          # Dependências Python
├── criar_banco.py            # Cria o banco local
├── verificar_banco.py        # Lista as tabelas do banco
├── templates/                # Páginas HTML com Jinja
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── unidades.html
│   ├── equipamentos.html
│   └── insumos.html
├── static/                   # Arquivos estáticos
│   └── style.css
└── .gitignore
```

## Execução em produção

Para executar com Gunicorn em um ambiente compatível:

```bash
gunicorn app:app
```

Defina `ADMIN_USER`, `ADMIN_PASS` e `SECRET_KEY` no ambiente de produção e desative o modo de desenvolvimento do Flask.