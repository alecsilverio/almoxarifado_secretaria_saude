Sistema de Controle de Almoxarifado
Sistema web para controle de equipamentos clínicos e insumos da Secretaria Municipal de Saúde. O projeto centraliza as informações que antes estavam distribuídas em planilhas, permitindo organizar equipamentos por unidade de saúde e controlar o almoxarifado central.

Objetivo
O sistema foi desenvolvido para apoiar as atividades de inventário e gestão de materiais/equipamentos, permitindo:

Cadastrar unidades de saúde

Cadastrar equipamentos clínicos vinculados a cada unidade

Registrar patrimônio, nome, marca, modelo e número de série dos equipamentos

Acompanhar a situação dos equipamentos, como em uso, manutenção, quebrado, sucata ou reserva

Cadastrar insumos do almoxarifado central ou distribuídos em unidades

Controlar quantidade, lote, localização, datas de entrega e fabricação, e vencimento

Visualizar as informações em uma base única, evitando uma planilha separada para cada unidade

Restringir o acesso ao sistema por meio de login administrativo

Tecnologias utilizadas
Python 3

Flask

SQLite

HTML5

CSS3

JavaScript

Git e GitHub

Estrutura do projeto
almoxarifado_secretaria_saude/
├── app.py                     # Aplicação Flask e rotas do sistema
├── schema_almoxarifado.sql    # Estrutura das tabelas SQLite
├── requirements.txt           # Dependências Python
├── criar_banco.py             # Script opcional para criar o banco local
├── verificar_banco.py         # Script opcional para verificar tabelas
├── templates/                 # Páginas HTML com Jinja
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── unidades.html
│   ├── equipamentos.html
│   └── insumos.html
├── static/                    # Arquivos estáticos
│   ├── style.css
│   ├── logo.png
│   └── favicon.png
└── .gitignore