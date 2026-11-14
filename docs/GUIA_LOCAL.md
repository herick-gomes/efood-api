# Começar no Windows

Abra o PowerShell na pasta onde quer guardar seus projetos:

```powershell
git clone https://github.com/herick-gomes/efood-api.git
cd efood-api
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

O script usa Python 3.12 ou superior, cria uma venv, instala as dependências, aplica as migrações e inicia a API em http://127.0.0.1:8000/api/docs/. Ele usa SQLite para facilitar a primeira visita. Para testes de concorrência e o ambiente principal, use o Docker Compose com PostgreSQL.

## Criar dados fictícios

Em outro terminal, **na pasta efood-api, ao lado de manage.py**:

```powershell
$env:DJANGO_DEBUG = "1"
$env:EFOOD_DEMO_PASSWORD = Read-Host "Escolha uma senha local para as contas demo"
.\.venv\Scripts\python manage.py seed_demo
Remove-Item Env:EFOOD_DEMO_PASSWORD
```

As contas são `demo_customer` e `demo_merchant`, com a senha escolhida. Não há dados de restaurantes ou clientes reais. O comando recusa sobrescrever essas contas.

## Explorar a API

1. Em `/api/docs/`, execute `auth/token` com uma das contas.
2. Copie o token `access` e use o botão Authorize.
3. Como cliente, navegue pelo catálogo e crie um pedido com dados de entrega fictícios.
4. Gere uma chave UUID por intenção de compra. No PowerShell: `[guid]::NewGuid().ToString()`.
5. Repita o mesmo pedido com a mesma chave: deve voltar o mesmo pedido.
6. Entre como restaurante para aceitar e avançar seu status.

## Conectar o front-end

Clone o Efood em outra pasta e use a branch `feat/own-api-integration`. Siga `docs/OWN_API.md` nela. Configure `REACT_APP_EFOOD_API_URL=http://127.0.0.1:8000/api/v1`, rode `npm ci` e `npm start`.

Não use dados de cartão: o checkout dessa branch é explicitamente simulado. Não faça merge para publicar antes de hospedar a API e revisar o fluxo no navegador.

## Configuração

O Python lê variáveis do ambiente; não carrega `.env` automaticamente. Docker Compose carrega `.env`. A porta local padrão é 8000; pare o Rota se ele estiver usando a mesma porta, ou escolha outra e ajuste o endereço no front-end.

O script PowerShell foi escrito para Windows; a validação executada nesta entrega usa Python/Linux. Veja `docs/VALIDATION.md` para os resultados e limites reais.
