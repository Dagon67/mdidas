# Subir o backend no Google Cloud Run

Siga estes passos para colocar a API de colorimetria no ar e usar no app online.

---

## Pré-requisitos

1. **Conta Google** (a mesma do Firebase).
2. **Google Cloud SDK (gcloud)** instalado:
   - Baixe: https://cloud.google.com/sdk/docs/install
   - Instale e, no final, rode `gcloud init` para fazer login e escolher o projeto.

---

## Passo 1: Abrir o terminal na pasta do backend

```powershell
cd c:\Users\Administrador\Documents\mdidas\backend
```

---

## Passo 2: Login e projeto

```powershell
gcloud auth login
```

Abra o link no navegador, entre com a conta Google e autorize.

Defina o projeto (use o mesmo do Firebase):

```powershell
gcloud config set project modi-5369d
```

Se o projeto `modi-5369d` não existir no Google Cloud, crie em https://console.cloud.google.com/ (o projeto Firebase e o do Google Cloud costumam ser o mesmo).

---

## Passo 3: Ativar a API do Cloud Run

```powershell
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## Passo 4: Fazer o deploy

Na pasta `backend`, rode:

```powershell
gcloud run deploy colorimetria --source . --region us-central1 --allow-unauthenticated --platform managed
```

- **colorimetria** = nome do serviço (pode trocar).
- **--source .** = usa o Dockerfile da pasta atual e faz o build no Google.
- **--region us-central1** = região (pode usar southamerica-east1 para São Paulo).
- **--allow-unauthenticated** = deixa o endpoint público para o app chamar.

Quando pedir **"Do you want to continue (Y/n)?"**, digite **Y** e Enter.

O build pode levar **5–15 minutos** (instala OpenCV, MediaPipe, etc.). No final aparece algo como:

```
Service [colorimetria] revision [...] has been deployed and is serving 100 percent of traffic.
Service URL: https://colorimetria-xxxxx-uc.a.run.app
```

---

## Passo 5: Copiar a URL do serviço

A **Service URL** é a URL do backend, por exemplo:

```
https://colorimetria-xxxxx-uc.a.run.app
```

Copie essa URL (sem a barra no final).

---

## Passo 6: Configurar no app

1. Abra o arquivo **cores.html** (na raiz do projeto, fora da pasta backend).
2. Procure a linha:
   ```javascript
   var API_CORES_URL = "";
   ```
3. Troque para (use a sua URL):
   ```javascript
   var API_CORES_URL = "https://colorimetria-xxxxx-uc.a.run.app";
   ```
4. Salve e faça o deploy do site de novo:
   ```powershell
   cd c:\Users\Administrador\Documents\mdidas
   firebase deploy
   ```

---

## Pronto

Abra o app em **https://modi-5369d.web.app**, entre em **Minhas cores ideais**, envie as fotos e clique em **Analisar minhas cores**. A análise deve funcionar usando o backend no Cloud Run.

---

## Se der erro

- **"Permission denied" / 403**: confira se ativou `run.googleapis.com` e `cloudbuild.googleapis.com` e se está logado com `gcloud auth login`.
- **Build falha**: veja a mensagem no terminal; às vezes é falta de ativar billing no projeto (Cloud Run exige conta de faturamento, mas há cota gratuita).
- **CORS**: a API já envia `Access-Control-Allow-Origin: *`; se o navegador reclamar, confira se a URL em `API_CORES_URL` está certa e sem barra no final.
