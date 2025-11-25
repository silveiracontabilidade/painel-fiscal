# Painel Fiscal - Backend

Ambiente Django inicializado para servir como backend da nova aplicação, preparado para autenticação por JWT e integração futura com um frontend em React.

## Estrutura
- `backend-venv/`: ambiente virtual contendo todas as dependências (Django, DRF, SimpleJWT, mysqlclient, firebirdsql).
- `painel_backend/`: projeto Django com app `accounts` responsável pelas telas de login/bem-vindo e endpoints de autenticação.

## Primeiros passos
```bash
cd /home/deniscamargo/projetos/painel-fiscal
source backend-venv/bin/activate
python painel_backend/manage.py migrate
python painel_backend/manage.py createsuperuser
python painel_backend/manage.py runserver 0.0.0.0:8000
```

As configurações sensíveis estão em `.env` (carregado automaticamente com `python-dotenv`). Ajuste `OPENAI_API_KEY`, credenciais do MySQL/Firebird, hosts etc. antes de subir o servidor. As migrations usarão diretamente o banco MySQL configurado via variáveis.

## Funcionalidades prontas
- Tela de login (`/login/`) e tela de boas-vindas (`/welcome/`) usando autenticação padrão do Django.
- Logout por POST em `/logout/`.
- Endpoints JWT:
  - `POST /api/token/` para obter `access` e `refresh`.
  - `POST /api/token/refresh/` para renovar o `access`.
- Endpoint protegido (`GET /api/status/`) para validar tokens e integração futura com o frontend React.
- Tabela `reinf_NFS` (app `nfse`) populada com a NF de exemplo e preparada para novos registros.
- Processo de importação de NFSe em PDF (`manage.py import_nfse`) com OCR + OpenAI.

## Integrações e próximos passos
- **MySQL**: `mysqlclient` já instalado e configurado.
- **Firebird**: driver `firebirdsql` instalado. Informações de conexão de exemplo estão no bloco `FIREBIRD_CONNECTION` das settings, pronto para ser ajustado com os dados reais.
- **Frontend React**: o backend está pronto para receber chamadas via API. Defina as origens permitidas em `CORS_ALLOWED_ORIGINS` quando o endereço do frontend estiver disponível.

Com o servidor em execução, visite `http://localhost:8000/login/` para validar as telas e utilizar o fluxo de autenticação antes da implementação do frontend.

## Arquivo `.env`
- Localizado na raiz do projeto (`/home/deniscamargo/projetos/painel-fiscal/.env`).
- Carregado automaticamente por `python-dotenv` quando o Django inicia.
- Contém `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, credenciais do MySQL/Firebird, `OPENAI_API_KEY` e `CORS_ALLOWED_ORIGINS`.
- `OPENAI_MODEL` permite definir o modelo padrão da OpenAI (padrão `gpt-4o-mini`). Caso o modelo informado não esteja disponível, o sistema tenta automaticamente outros modelos suportados (`gpt-4o-mini`, `gpt-4o-mini-fast`, `gpt-3.5-turbo`, etc.).
- Ajuste esse arquivo (ou use variáveis de ambiente do sistema) para trocar chaves e senhas sem editar `settings.py`.

## Importação de NFSe em PDF
O app `nfse` oferece um pipeline que:
1. Lê PDFs com `pdfplumber` e só executa OCR (página a página) quando a página não possuir texto.
2. Usa `pytesseract` apenas nas páginas necessárias, reduzindo bastante o tempo total de processamento.
3. Aplica uma limpeza no texto (remove espaços/repetições) e filtra apenas trechos relevantes da NFSe (blocos com “Dados Gerais”, “Emitente”, “Tomador”, “Tributação”, “Informações Complementares”, etc.), reduzindo o número de tokens enviados à OpenAI.
4. Identifica se o documento segue o layout típico de NFSe (procura termos como “Nota Fiscal de Serviços Eletrônica”, “Prestador do Serviço”, “Tomador do Serviço”, “ISSQN”, “DPS” etc., conforme os manuais de prefeituras municipais).
5. Envia o conteúdo textual para a API (modelo padrão `gpt-4o-mini`, configurável via `--model` ou `OPENAI_MODEL`). Se o modelo configurado não estiver disponível, o importador realiza fallback automático para outros modelos liberados na conta.
6. Persiste e/ou atualiza os dados na tabela `reinf_NFS`.

### Dependências extras
- Sistema precisa ter **Tesseract OCR** e **poppler** instalados para que `pytesseract` e `pdf2image` funcionem.

### Instalando o OCR e o poppler
- **Debian/Ubuntu**: `sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils`
- **Fedora/RHEL**: `sudo dnf install -y tesseract poppler-utils`
- **macOS (Homebrew)**: `brew install tesseract poppler`
- **Windows (Chocolatey)**: `choco install tesseract poppler`

Depois de instalar, confirme que `tesseract` está disponível no `PATH` com `which tesseract` (Linux/macOS) ou `where tesseract` (Windows). Sem o binário, os testes de importação de NFSe irão falhar.
- Configure sua chave da OpenAI em `OPENAI_API_KEY` ou passe via `--api-key`.

### Uso rápido
```bash
source backend-venv/bin/activate
python painel_backend/manage.py import_nfse /caminho/para/pasta_de_pdfs --api-key "sk-xxxx"
# ou apontando para o Ollama local (API compatível com OpenAI):
python painel_backend/manage.py import_nfse /caminho/para/pasta_de_pdfs \
    --base-url http://127.0.0.1:11434/v1 \
    --api-key ollama \
    --model mistral:7b-instruct
# ou, para testar o modo sem OpenAI (regex apenas):
python painel_backend/manage.py import_nfse_regex /caminho/para/pasta_de_pdfs
```

Passe um arquivo individual ou uma pasta; quando for pasta, todos os `*.pdf` (busca recursiva) serão processados em sequência. O comando utiliza `nfse/services.py::NFSeImporter`, que também pode ser chamado diretamente em outras rotinas Python para processar lotes. Cada execução cria/atualiza registros chaveados pela `access_key` e a NF de exemplo fornecida já consta na tabela após `python manage.py migrate`.

### Classificação e organização das notas
- O comando analisa o texto de cada PDF antes de chamar a OpenAI. Só segue para importação quando identifica os elementos característicos das NFS-e brasileiras (texto contendo “Nota Fiscal de Serviços Eletrônica”, “Prestador/ Tomador do Serviço”, menções a ISSQN, códigos de tributação, etc.).
- PDFs que não atingirem o limiar mínimo de correspondências são ignorados no processo de importação e, ao final, são movidos automaticamente para a pasta `NF Outros`.
- As notas classificadas como serviço são importadas e em seguida movidas para a pasta `NF Servicos`. Ambas as pastas são criadas (se ainda não existirem) dentro da pasta analisada ou, caso você aponte para um arquivo único, dentro do mesmo diretório do arquivo.

### Modo experimental baseado em regex
- O comando `import_nfse_regex` utiliza o mesmo pipeline de leitura/OCR e classificação de NFSe, porém extrai os campos diretamente do texto com expressões regulares.
- Esse modo é útil para validar o fluxo sem depender da API da OpenAI. Entretanto, por se basear em padrões fixos, pode não reconhecer todas as variações de layout existentes no Brasil; ajuste os regex em `nfse/regex_importer.py` conforme as cidades/formatos que for apoiar.
- Caso a chave de acesso não esteja claramente indicada no texto, o importador tenta encontrá-la em qualquer sequência de ≥30 dígitos no corpo ou no nome do arquivo (por exemplo, nomes no formato `NFe_3106...pdf`). Sem chave válida, o registro é ignorado.

### Rodando com LLM local (Ollama)
- Instale o Ollama (`~/ollama/bin/ollama` já está disponível) e suba o servidor local com `ollama serve`.
- Puxe um modelo de instrução, como `ollama pull mistral:7b-instruct` ou `ollama pull llama3:latest`.
- Execute o comando de importação apontando para o endpoint local:
  ```bash
  python painel_backend/manage.py import_nfse pasta \
    --base-url http://127.0.0.1:11434/v1 \
    --api-key ollama \
    --model mistral:7b-instruct
  ```
- `NFSeImporter` tentará o modelo definido; se não funcionar, experimenta os candidatos configurados (`gpt-4o-mini`, `gpt-3.5-turbo`, `llama3.2`, etc.). Isso permite comparar rapidamente o desempenho entre OpenAI e um modelo local enxuto.
