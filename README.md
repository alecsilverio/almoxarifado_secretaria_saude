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
text
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
O arquivo almoxarifado.db é criado localmente e não deve ser enviado ao repositório, pois está listado no .gitignore.

Requisitos
Antes de iniciar, tenha instalado:

Python 3.10 ou superior

Git (opcional, para controle de versão)

Como executar localmente
1. Clone o repositório
bash
git clone <URL_DO_REPOSITORIO>
cd almoxarifado_secretaria_saude
2. Crie o ambiente virtual
No Windows PowerShell:

powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
Caso o PowerShell bloqueie a ativação, execute apenas para a sessão atual:

powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
3. Instale as dependências
powershell
pip install -r requirements.txt
4. Inicie o banco de dados
O banco é iniciado automaticamente ao executar app.py. Se necessário, também é possível usar:

powershell
python criar_banco.py
Para verificar se as tabelas foram criadas:

powershell
python verificar_banco.py
As principais tabelas são:

unidades

equipamentos

insumos

movimentacoes

5. Execute a aplicação
powershell
python app.py
Abra no navegador:

text
http://127.0.0.1:5000
Para parar o servidor, use Ctrl + C no terminal.

Acesso administrativo
No estado atual do projeto, o acesso é protegido por login administrativo configurado no arquivo app.py.

text
Usuário: admin
Senha: mude_esta_senha_123
Antes de disponibilizar o sistema para outras pessoas, altere a senha e mova as credenciais para variáveis de ambiente. Senhas não devem ficar gravadas diretamente no código em uma aplicação de produção.

Modelo de dados
text
Unidade 1 ─── 0..* Equipamento
Unidade 1 ─── 0..* Insumo
Insumo  1 ─── 0..* Movimentacao
Uma unidade pode possuir diversos equipamentos.

Um equipamento fica associado a uma unidade de saúde.

Um insumo pode estar no almoxarifado central ou associado a uma unidade.

Uma movimentação registra entrada, saída ou transferência de insumos entre o almoxarifado e as unidades.

Funcionalidades atuais
Login administrativo

Cadastro e listagem de unidades

Cadastro e listagem de equipamentos

Cadastro e listagem de insumos

Vínculo de equipamentos com unidades de saúde

Controle de patrimônio, marca, modelo e número de série

Controle de quantidade, lote e validade de insumos

Identidade visual com cores institucionais

Banco de dados SQLite

Próximas melhorias
Editar e excluir unidades, equipamentos e insumos

Pesquisa e filtros por unidade, patrimônio, modelo, marca e situação

Dashboard com totais de equipamentos, insumos e unidades

Alerta de insumos vencidos ou próximos do vencimento

Definição de alertas em 30, 60 e 90 dias

Registro completo de movimentações de entrada, saída e transferência

Controle de usuários e perfis de acesso

Exportação de relatórios para Excel e PDF

Importação dos dados existentes em planilhas Excel

Backup do banco de dados

Publicação em servidor para acesso interno autorizado

Segurança e uso de dados
Este sistema pode conter informações patrimoniais e operacionais da Secretaria Municipal de Saúde. Por isso:

Não publique dados reais de patrimônio, equipamentos, fornecedores ou estoque em repositórios públicos.

Mantenha o repositório como privado enquanto houver dados institucionais.

Não envie o banco local almoxarifado.db ao GitHub.

Use credenciais fortes antes de qualquer uso por mais de uma pessoa.

Realize backups periódicos do banco de dados após a implantação.

Autor
Projeto desenvolvido para apoiar o controle de almoxarifado, equipamentos clínicos e insumos da Secretaria Municipal de Saúde.